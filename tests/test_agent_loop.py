"""Tests for the two-phase agent loop (planning + execution)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from explorer.agent import AgentConfig, AgentTurn, ToolCallRecord, run_agent_turn


def _make_text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _make_tool_use_block(tool_id: str, name: str, input_dict: dict):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_dict)


def _make_response(content_blocks):
    return SimpleNamespace(content=content_blocks, stop_reason="end_turn")


class TestTwoPhaseLoop:
    def test_planning_phase_called_without_tools(self, mock_connections):
        """The first API call should have no tools to force a text plan."""
        plan = _make_response([_make_text_block("**Thesis:** Direct lookup.")])
        final = _make_response([_make_text_block("Target share is 0.25.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        tools = [{"name": "query_sql", "description": "test", "input_schema": {}}]
        messages = [{"role": "user", "content": "What's Waddle's target share?"}]

        run_agent_turn(
            client=client,
            system_prompt="test prompt",
            messages=messages,
            connections=mock_connections,
            tools=tools,
        )

        calls = client.messages.create.call_args_list
        assert len(calls) == 2

        # Planning call: no tools kwarg (model forced to reason in text)
        planning_call_kwargs = calls[0].kwargs
        assert "tools" not in planning_call_kwargs

        # Execution call: tools present
        exec_call_kwargs = calls[1].kwargs
        assert len(exec_call_kwargs["tools"]) > 0

    def test_plan_injected_into_messages(self, mock_connections):
        """Plan and proceed message should appear in history."""
        plan = _make_response([_make_text_block("**Thesis:** Hill vs Adams.")])
        final = _make_response([_make_text_block("Hill wins.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        messages = [{"role": "user", "content": "Compare Hill and Adams"}]

        run_agent_turn(
            client=client,
            system_prompt="test",
            messages=messages,
            connections=mock_connections,
            tools=[],
        )

        # user → assistant (plan) → user (proceed) → assistant (final)
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert "Proceed" in messages[2]["content"]
        assert messages[3]["role"] == "assistant"

    def test_tool_use_loop_works_after_plan(self, mock_connections):
        """Plan → tool call → final response should work end to end."""
        plan = _make_response([_make_text_block("**Thesis:** Need target share data.")])
        tool_call = _make_response([_make_tool_use_block(
            "t1", "query_sql", {"sql": "SELECT 1", "description": "test"}
        )])
        final = _make_response([_make_text_block("Hill leads in target share.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, tool_call, final]

        tools = [{"name": "query_sql", "description": "test", "input_schema": {}}]
        messages = [{"role": "user", "content": "Who leads in target share?"}]

        with patch("explorer.agent.dispatch_tool", return_value='{"rows": [], "row_count": 0}'):
            result = run_agent_turn(
                client=client,
                system_prompt="test",
                messages=messages,
                connections=mock_connections,
                tools=tools,
            )

        assert client.messages.create.call_count == 3
        assert result.raw_response.content[0].text == "Hill leads in target share."

    def test_planning_prompt_includes_addendum(self, mock_connections):
        """Planning call should use augmented system prompt; execution should not."""
        plan = _make_response([_make_text_block("Plan.")])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        messages = [{"role": "user", "content": "test"}]

        run_agent_turn(
            client=client,
            system_prompt="base prompt",
            messages=messages,
            connections=mock_connections,
            tools=[],
        )

        planning_system = client.messages.create.call_args_list[0].kwargs["system"]
        exec_system = client.messages.create.call_args_list[1].kwargs["system"]

        assert "PLANNING phase" in planning_system
        assert "PLANNING phase" not in exec_system


class TestAgentTurnResult:
    def test_plan_text_populated(self, mock_connections):
        """AgentTurn should contain the plan text."""
        plan = _make_response([_make_text_block("**Thesis:** Test thesis.")])
        final = _make_response([_make_text_block("Final answer.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        turn = run_agent_turn(
            client=client,
            system_prompt="test",
            messages=[{"role": "user", "content": "test"}],
            connections=mock_connections,
            tools=[],
        )

        assert turn.plan_text == "**Thesis:** Test thesis."
        assert turn.response_text == "Final answer."
        assert turn.tool_calls == []
        assert turn.raw_response is not None

    def test_tool_calls_recorded(self, mock_connections):
        """AgentTurn should record all tool calls with results."""
        plan = _make_response([_make_text_block("Plan.")])
        tool_call = _make_response([_make_tool_use_block(
            "t1", "query_sql", {"sql": "SELECT 1", "description": "test"}
        )])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, tool_call, final]

        with patch("explorer.agent.dispatch_tool", return_value='{"rows": [], "row_count": 0}'):
            turn = run_agent_turn(
                client=client,
                system_prompt="test",
                messages=[{"role": "user", "content": "test"}],
                connections=mock_connections,
                tools=[{"name": "query_sql", "description": "t", "input_schema": {}}],
            )

        assert len(turn.tool_calls) == 1
        assert turn.tool_calls[0].id == "t1"
        assert turn.tool_calls[0].name == "query_sql"
        assert turn.tool_calls[0].result == '{"rows": [], "row_count": 0}'
        assert turn.tool_calls[0].duration_ms >= 0


class TestCallbacks:
    def test_on_plan_called(self, mock_connections):
        """on_plan callback should fire with plan text."""
        plan = _make_response([_make_text_block("My plan.")])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        callback = MagicMock()

        run_agent_turn(
            client=client,
            system_prompt="test",
            messages=[{"role": "user", "content": "test"}],
            connections=mock_connections,
            tools=[],
            on_plan=callback,
        )

        callback.assert_called_once_with("My plan.")

    def test_tool_callbacks_called(self, mock_connections):
        """on_tool_start and on_tool_end should fire for each tool call."""
        plan = _make_response([_make_text_block("Plan.")])
        tool_call = _make_response([_make_tool_use_block(
            "t1", "query_sql", {"sql": "SELECT 1", "description": "test"}
        )])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, tool_call, final]

        start_cb = MagicMock()
        end_cb = MagicMock()

        with patch("explorer.agent.dispatch_tool", return_value='{"rows": [], "row_count": 0}'):
            run_agent_turn(
                client=client,
                system_prompt="test",
                messages=[{"role": "user", "content": "test"}],
                connections=mock_connections,
                tools=[{"name": "query_sql", "description": "t", "input_schema": {}}],
                on_tool_start=start_cb,
                on_tool_end=end_cb,
            )

        start_cb.assert_called_once()
        assert start_cb.call_args[0][0] == "t1"
        assert start_cb.call_args[0][1] == "query_sql"

        end_cb.assert_called_once()
        assert end_cb.call_args[0][0] == "t1"
        assert end_cb.call_args[0][1] == "query_sql"
        assert end_cb.call_args[0][2] == '{"rows": [], "row_count": 0}'

    def test_config_overrides_model(self, mock_connections):
        """AgentConfig should control model and token limits."""
        plan = _make_response([_make_text_block("Plan.")])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        config = AgentConfig(model="claude-haiku-4-5-20251001", max_tokens=2048, planning_max_tokens=512)

        run_agent_turn(
            client=client,
            system_prompt="test",
            messages=[{"role": "user", "content": "test"}],
            connections=mock_connections,
            tools=[],
            config=config,
        )

        planning_call = client.messages.create.call_args_list[0].kwargs
        assert planning_call["model"] == "claude-haiku-4-5-20251001"
        assert planning_call["max_tokens"] == 512

        exec_call = client.messages.create.call_args_list[1].kwargs
        assert exec_call["model"] == "claude-haiku-4-5-20251001"
        assert exec_call["max_tokens"] == 2048
