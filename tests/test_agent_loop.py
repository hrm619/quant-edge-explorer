"""Tests for the two-phase agent loop (planning + execution)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from explorer.main import _run_agent_loop


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

        _run_agent_loop(
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

        _run_agent_loop(
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

        with patch("explorer.main.dispatch_tool", return_value='{"rows": [], "row_count": 0}'):
            result = _run_agent_loop(
                client=client,
                system_prompt="test",
                messages=messages,
                connections=mock_connections,
                tools=tools,
            )

        assert client.messages.create.call_count == 3
        assert result.content[0].text == "Hill leads in target share."

    def test_planning_prompt_includes_addendum(self, mock_connections):
        """Planning call should use augmented system prompt; execution should not."""
        plan = _make_response([_make_text_block("Plan.")])
        final = _make_response([_make_text_block("Done.")])

        client = MagicMock()
        client.messages.create.side_effect = [plan, final]

        messages = [{"role": "user", "content": "test"}]

        _run_agent_loop(
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
