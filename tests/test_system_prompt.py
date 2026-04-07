"""Tests for system prompt builder."""

from explorer.system_prompt import build_system_prompt, load_priors


class TestBuildSystemPrompt:
    def test_contains_schema_sections(self):
        prompt = build_system_prompt()
        assert "player_season_baseline" in prompt
        assert "players" in prompt
        assert "coaching_staff" in prompt
        assert "wr_reception_perception" in prompt

    def test_contains_key_columns(self):
        prompt = build_system_prompt()
        assert "target_share" in prompt
        assert "yards_per_route_run" in prompt
        assert "data_trust_weight" in prompt
        assert "adp_divergence" in prompt
        assert "sharp_consensus_rank" in prompt

    def test_contains_priors(self):
        prompt = build_system_prompt()
        assert "Market Structure" in prompt
        assert "Player Evaluation" in prompt
        assert "Signal Hierarchy" in prompt
        assert "Red Flags" in prompt
        assert "regression candidate" in prompt

    def test_contains_kb_awareness(self):
        prompt = build_system_prompt()
        assert "ChromaDB" in prompt
        assert "barrett" in prompt
        assert "trust_tier" in prompt
        assert "fantasy_football" in prompt

    def test_contains_chart_conventions(self):
        prompt = build_system_prompt()
        assert "Chart Conventions" in prompt
        assert "spotlight" in prompt
        assert "reference_lines" in prompt or "reference lines" in prompt.lower()
        assert "insight" in prompt.lower()

    def test_contains_thresholds(self):
        prompt = build_system_prompt()
        assert "0.7" in prompt
        assert "12" in prompt

    def test_custom_priors(self):
        custom = {
            "market_structure": ["Custom market prior"],
            "player_evaluation": ["Custom eval prior"],
            "signal_hierarchy": ["Custom signal prior"],
            "red_flags": ["Custom red flag"],
            "thresholds": {"trust_weight_reliable": 0.5},
        }
        prompt = build_system_prompt(priors=custom)
        assert "Custom market prior" in prompt
        assert "Custom red flag" in prompt
        assert "0.5" in prompt


class TestAnalysisFramework:
    def test_contains_analysis_framework(self):
        prompt = build_system_prompt()
        assert "Analysis Framework" in prompt

    def test_contains_narrative_arc(self):
        prompt = build_system_prompt()
        assert "Lead with the verdict" in prompt
        assert "Confront your priors" in prompt

    def test_contains_editorial_voice(self):
        prompt = build_system_prompt()
        assert "Editorial Voice" in prompt
        assert "Opinionated but honest" in prompt

    def test_framework_before_behavior(self):
        prompt = build_system_prompt()
        framework_pos = prompt.index("Analysis Framework")
        behavior_pos = prompt.index("Editorial Voice")
        assert framework_pos < behavior_pos

    def test_calibrating_depth(self):
        prompt = build_system_prompt()
        assert "Simple lookup" in prompt
        assert "Open-ended analysis" in prompt


class TestPlanningPrompt:
    def test_planning_prompt_includes_addendum(self):
        from explorer.system_prompt import build_planning_prompt
        base = build_system_prompt()
        planning = build_planning_prompt(base)
        assert "PLANNING phase" in planning
        assert "Thesis" in planning
        assert planning.startswith(base)

    def test_planning_addendum_not_in_base(self):
        base = build_system_prompt()
        assert "PLANNING phase" not in base


class TestLoadPriors:
    def test_loads_yaml(self):
        priors = load_priors()
        assert "market_structure" in priors
        assert "player_evaluation" in priors
        assert "signal_hierarchy" in priors
        assert "red_flags" in priors
        assert "thresholds" in priors
        assert priors["thresholds"]["trust_weight_reliable"] == 0.70
