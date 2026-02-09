"""
Test that UAPK Vision Alignment Scorecard artifacts exist and are well-formed.
"""
import pytest
from pathlib import Path
import yaml


class TestScorecardArtifactsExist:
    """Test that scorecard artifacts exist"""

    def test_scorecard_md_exists(self):
        """Test that main scorecard markdown exists"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD.md")
        assert path.exists(), "Main scorecard markdown file missing"
        assert path.stat().st_size > 1000, "Scorecard file is too small"

    def test_scorecard_yaml_exists(self):
        """Test that scorecard YAML exists"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD.yaml")
        assert path.exists(), "Scorecard YAML file missing"
        assert path.stat().st_size > 500, "Scorecard YAML is too small"

    def test_scorecard_diff_exists(self):
        """Test that delta plan markdown exists"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md")
        assert path.exists(), "Delta plan markdown file missing"
        assert path.stat().st_size > 1000, "Delta plan file is too small"

    def test_evaluator_index_updated(self):
        """Test that evaluator index exists and references scorecard"""
        path = Path("EVALUATOR_INDEX.md")
        assert path.exists(), "Evaluator index missing"

        content = path.read_text()
        assert "UAPK_VISION_ALIGNMENT_SCORECARD" in content, \
            "Evaluator index doesn't reference scorecard"
        assert "Vision Alignment" in content, \
            "Evaluator index missing vision alignment section"


class TestScorecardMarkdownStructure:
    """Test that scorecard markdown has required sections"""

    @pytest.fixture
    def scorecard_content(self):
        """Load scorecard markdown content"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD.md")
        return path.read_text()

    def test_has_executive_summary(self, scorecard_content):
        """Test scorecard has executive summary"""
        assert "Executive Summary" in scorecard_content, \
            "Missing Executive Summary section"
        assert "Overall Alignment Score" in scorecard_content, \
            "Missing overall score in executive summary"

    def test_has_pillar_a_gateway(self, scorecard_content):
        """Test scorecard has Pillar A (Gateway)"""
        assert "Pillar A: UAPK Gateway" in scorecard_content, \
            "Missing Pillar A section"
        assert "Policy Membrane" in scorecard_content, \
            "Missing A1: Policy Membrane dimension"

    def test_has_pillar_b_protocol(self, scorecard_content):
        """Test scorecard has Pillar B (Protocol)"""
        assert "Pillar B: UAPK Protocol" in scorecard_content, \
            "Missing Pillar B section"
        assert "Manifest Semantics" in scorecard_content, \
            "Missing B1: Manifest Semantics dimension"

    def test_has_pillar_c_compiler(self, scorecard_content):
        """Test scorecard has Pillar C (Compiler)"""
        assert "Pillar C: UAPK Compiler" in scorecard_content, \
            "Missing Pillar C section"
        assert "Template → Instance Compilation" in scorecard_content, \
            "Missing C1: Template Compilation dimension"

    def test_has_scoring_model(self, scorecard_content):
        """Test scorecard has scoring model"""
        assert "Scoring Model" in scorecard_content, \
            "Missing Scoring Model section"
        assert "0-5" in scorecard_content or "0–5" in scorecard_content, \
            "Missing 0-5 scale description"

    def test_has_heatmap(self, scorecard_content):
        """Test scorecard has heatmap"""
        assert "Heatmap" in scorecard_content or "Scoring Heatmap" in scorecard_content, \
            "Missing heatmap section"

    def test_has_top_gaps(self, scorecard_content):
        """Test scorecard lists top gaps"""
        assert "Top 5 Gaps" in scorecard_content or "Top Gaps" in scorecard_content, \
            "Missing top gaps section"

    def test_has_narrative_summary(self, scorecard_content):
        """Test scorecard has narrative summary"""
        assert "Narrative Summary" in scorecard_content or "Summary" in scorecard_content, \
            "Missing narrative summary section"
        assert "Strategic Options" in scorecard_content or "Recommendation" in scorecard_content, \
            "Missing strategic recommendations"

    def test_dimensions_have_evidence(self, scorecard_content):
        """Test dimensions include evidence links"""
        assert "Evidence:" in scorecard_content or "**Evidence**:" in scorecard_content, \
            "Missing evidence links in dimensions"
        assert "Current:" in scorecard_content or "**Current State**:" in scorecard_content, \
            "Missing current state descriptions"
        assert "Target:" in scorecard_content or "**Target State**:" in scorecard_content, \
            "Missing target state descriptions"
        assert "Gap:" in scorecard_content or "**Gap**:" in scorecard_content, \
            "Missing gap descriptions"
        assert "Next Action:" in scorecard_content or "**Next Action**:" in scorecard_content, \
            "Missing next action items"


class TestScorecardYAMLStructure:
    """Test that scorecard YAML is well-formed"""

    @pytest.fixture
    def scorecard_data(self):
        """Load and parse scorecard YAML"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD.yaml")
        with open(path) as f:
            return yaml.safe_load(f)

    def test_yaml_parses(self, scorecard_data):
        """Test that YAML parses without errors"""
        assert scorecard_data is not None, "YAML failed to parse"

    def test_has_version(self, scorecard_data):
        """Test YAML has version"""
        assert "version" in scorecard_data, "Missing version field"
        assert scorecard_data["version"] == "2.0.0", "Expected version 2.0.0"

    def test_has_overall_score(self, scorecard_data):
        """Test YAML has overall score"""
        assert "overall" in scorecard_data, "Missing overall field"
        assert "score" in scorecard_data["overall"], "Missing overall.score"
        assert scorecard_data["overall"]["score"] == 48, \
            f"Expected score 48, got {scorecard_data['overall']['score']}"

    def test_has_three_pillars(self, scorecard_data):
        """Test YAML has three pillars"""
        assert "pillars" in scorecard_data, "Missing pillars field"
        assert len(scorecard_data["pillars"]) == 3, \
            f"Expected 3 pillars, got {len(scorecard_data['pillars'])}"

        pillar_codes = [p["code"] for p in scorecard_data["pillars"]]
        assert "A" in pillar_codes, "Missing pillar A (Gateway)"
        assert "B" in pillar_codes, "Missing pillar B (Protocol)"
        assert "C" in pillar_codes, "Missing pillar C (Compiler)"

    def test_pillars_have_dimensions(self, scorecard_data):
        """Test each pillar has dimensions"""
        total_dimensions = 0
        for pillar in scorecard_data["pillars"]:
            assert "dimensions" in pillar, \
                f"Pillar {pillar['name']} missing dimensions"
            assert len(pillar["dimensions"]) > 0, \
                f"Pillar {pillar['name']} has no dimensions"
            total_dimensions += len(pillar["dimensions"])

        # Should have 19 dimensions total (9 Gateway + 5 Protocol + 5 Compiler)
        assert total_dimensions >= 14, \
            f"Expected at least 14 dimensions, got {total_dimensions}"

    def test_dimensions_have_required_fields(self, scorecard_data):
        """Test dimensions have required fields"""
        required_fields = ["name", "code", "score", "current", "target", "gap", "evidence", "next_action"]

        for pillar in scorecard_data["pillars"]:
            for dimension in pillar["dimensions"]:
                for field in required_fields:
                    assert field in dimension, \
                        f"Dimension {dimension.get('name', 'unknown')} missing field: {field}"

    def test_has_top_gaps(self, scorecard_data):
        """Test YAML has top gaps"""
        assert "top_gaps" in scorecard_data, "Missing top_gaps field"
        assert len(scorecard_data["top_gaps"]) >= 5, \
            f"Expected at least 5 top gaps, got {len(scorecard_data['top_gaps'])}"

    def test_has_milestones(self, scorecard_data):
        """Test YAML has milestones"""
        assert "milestones" in scorecard_data, "Missing milestones field"
        assert len(scorecard_data["milestones"]) >= 3, \
            f"Expected at least 3 milestones, got {len(scorecard_data['milestones'])}"

    def test_has_strategic_options(self, scorecard_data):
        """Test YAML has strategic options"""
        assert "strategic_options" in scorecard_data, "Missing strategic_options field"
        assert len(scorecard_data["strategic_options"]) >= 1, \
            "Expected at least 1 strategic option"


class TestDeltaPlanStructure:
    """Test that delta plan has required structure"""

    @pytest.fixture
    def delta_content(self):
        """Load delta plan content"""
        path = Path("docs/_audit/UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md")
        return path.read_text()

    def test_has_overview(self, delta_content):
        """Test delta plan has overview"""
        assert ("Overview" in delta_content or "Executive Summary" in delta_content), \
            "Missing overview or executive summary section"
        assert "Baseline Score" in delta_content, "Missing baseline score"

    def test_has_milestone_1(self, delta_content):
        """Test delta plan has Milestone 1"""
        assert "Milestone 1" in delta_content, "Missing Milestone 1"
        assert "Gateway-Hardening" in delta_content or "Gateway Hardening" in delta_content, \
            "Milestone 1 should be about gateway hardening"

    def test_has_milestone_2(self, delta_content):
        """Test delta plan has Milestone 2"""
        assert "Milestone 2" in delta_content, "Missing Milestone 2"
        assert "Protocol" in delta_content, \
            "Milestone 2 should be about protocol"

    def test_has_milestone_3(self, delta_content):
        """Test delta plan has Milestone 3"""
        assert "Milestone 3" in delta_content, "Missing Milestone 3"
        assert "Compiler" in delta_content or "Fleet" in delta_content, \
            "Milestone 3 should be about compiler/fleet"

    def test_has_acceptance_criteria(self, delta_content):
        """Test delta plan has acceptance criteria"""
        assert "Acceptance Criteria" in delta_content, \
            "Missing acceptance criteria"
        # Should have criteria for each milestone
        assert delta_content.count("Acceptance Criteria") >= 3, \
            "Should have acceptance criteria for each milestone"

    def test_has_risk_register(self, delta_content):
        """Test delta plan has risk register"""
        assert "Risk" in delta_content, "Missing risk information"

    def test_has_timeline(self, delta_content):
        """Test delta plan has timeline"""
        assert "Timeline" in delta_content or "Duration" in delta_content, \
            "Missing timeline information"

    def test_has_files_to_modify(self, delta_content):
        """Test delta plan lists files to modify"""
        assert "Files to Create" in delta_content or "Files to Modify" in delta_content, \
            "Missing file change lists"

    def test_has_non_goals(self, delta_content):
        """Test delta plan has explicit non-goals"""
        assert "Non-Goals" in delta_content or "NOT implementing" in delta_content, \
            "Missing non-goals section"

    def test_milestones_have_acceptance_criteria(self, delta_content):
        """Test each milestone has acceptance criteria with verifiable commands"""
        # Should have bash code blocks with curl/pytest commands
        assert "```bash" in delta_content, \
            "Missing bash command examples in acceptance criteria"
        assert "pytest" in delta_content, \
            "Missing pytest commands in acceptance criteria"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
