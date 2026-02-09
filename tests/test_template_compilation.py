"""
Tests for Template Compilation (M3.1)
"""
import json
import pytest
from pathlib import Path
import tempfile

# Check if Jinja2 is available
try:
    from uapk.template_engine import (
        TemplateEngine,
        compile_manifest_template,
        simple_substitute,
        JINJA2_AVAILABLE
    )
except ImportError:
    JINJA2_AVAILABLE = False


@pytest.mark.skipif(not JINJA2_AVAILABLE, reason="Jinja2 not installed")
class TestTemplateEngine:
    """Test M3.1: Template Variable Substitution"""

    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing"""
        template_content = """{
  "name": "{{ business_name }}",
  "agent_prefix": "{{ agent_prefix }}",
  "rate_limit": {{ rate_limit | default(100) }},
  "enabled": {{ enabled | default(true) | tojson }}
}"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(template_content)
            return Path(f.name)

    @pytest.fixture
    def sample_vars(self):
        """Sample variables"""
        return {
            "business_name": "Test Business",
            "agent_prefix": "test",
            "rate_limit": 50,
            "enabled": False
        }

    def test_template_engine_initialization(self):
        """Test template engine can be initialized"""
        engine = TemplateEngine()
        assert engine is not None
        assert engine.env is not None

    def test_compile_template_basic(self, sample_template, sample_vars):
        """Test basic template compilation"""
        engine = TemplateEngine()
        manifest = engine.compile_template(sample_template, sample_vars)

        assert manifest["name"] == "Test Business"
        assert manifest["agent_prefix"] == "test"
        assert manifest["rate_limit"] == 50
        assert manifest["enabled"] is False

        # Clean up
        sample_template.unlink()

    def test_compile_template_with_defaults(self, sample_template):
        """Test template compilation with default values"""
        engine = TemplateEngine()
        vars_minimal = {
            "business_name": "Minimal Business",
            "agent_prefix": "minimal"
        }

        manifest = engine.compile_template(sample_template, vars_minimal)

        assert manifest["name"] == "Minimal Business"
        assert manifest["rate_limit"] == 100  # Default value
        assert manifest["enabled"] is True  # Default value

        # Clean up
        sample_template.unlink()

    def test_compile_template_missing_required_variable(self, sample_template):
        """Test error when required variable is missing"""
        engine = TemplateEngine()
        vars_incomplete = {
            "business_name": "Test"
            # Missing agent_prefix (required, no default)
        }

        with pytest.raises(ValueError, match="rendering failed"):
            engine.compile_template(sample_template, vars_incomplete)

        # Clean up
        sample_template.unlink()

    def test_compile_template_with_conditional(self):
        """Test template with conditional blocks"""
        template_content = """{
  "name": "Test",
  "features": [
    {% if enable_feature_a %}
    "feature_a",
    {% endif %}
    "feature_b"
  ]
}"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(template_content)
            template_path = Path(f.name)

        engine = TemplateEngine()

        # With feature enabled
        manifest1 = engine.compile_template(template_path, {"enable_feature_a": True})
        assert "feature_a" in manifest1["features"]

        # With feature disabled
        manifest2 = engine.compile_template(template_path, {"enable_feature_a": False})
        assert "feature_a" not in manifest2["features"]

        # Clean up
        template_path.unlink()

    def test_load_variables_from_yaml(self):
        """Test loading variables from YAML file"""
        vars_content = """
business_name: "YAML Business"
agent_prefix: "yaml"
config:
  timeout: 30
  retries: 3
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(vars_content)
            vars_path = Path(f.name)

        engine = TemplateEngine()
        variables = engine.load_variables(vars_path)

        assert variables["business_name"] == "YAML Business"
        assert variables["agent_prefix"] == "yaml"
        assert variables["config"]["timeout"] == 30

        # Clean up
        vars_path.unlink()

    def test_validate_template_valid(self, sample_template):
        """Test template validation for valid template"""
        engine = TemplateEngine()
        valid, errors = engine.validate_template(sample_template)

        assert valid is True
        assert len(errors) == 0

        # Clean up
        sample_template.unlink()

    def test_validate_template_invalid(self):
        """Test template validation for invalid template"""
        invalid_template = """
{
  "name": "{{ unclosed_variable
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_template)
            template_path = Path(f.name)

        engine = TemplateEngine()
        valid, errors = engine.validate_template(template_path)

        assert valid is False
        assert len(errors) > 0

        # Clean up
        template_path.unlink()

    def test_compile_manifest_template_convenience_function(self, sample_template, sample_vars):
        """Test convenience function for template compilation"""
        # Create vars file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(sample_vars, f)
            vars_path = f.name

        manifest = compile_manifest_template(
            str(sample_template),
            vars_path=vars_path
        )

        assert manifest["name"] == "Test Business"

        # Clean up
        sample_template.unlink()
        Path(vars_path).unlink()

    def test_opspilotos_template_compiles(self):
        """Test that the OpsPilotOS template compiles successfully"""
        template_path = Path("templates/opspilotos.template.jsonld")
        if not template_path.exists():
            pytest.skip("OpsPilotOS template not found")

        variables = {
            "business_name": "Test SaaS",
            "agent_prefix": "testsaas",
            "description": "Test Description",
            "execution_mode": "dry_run",
            "enable_nft_minting": True,
            "actions_per_minute": 100,
            "invoices_per_day": 500,
            "nft_mints_per_day": 10,
            "deliverable_completion_hours": 24,
            "escalation_timeout": 60,
            "audit_retention_days": 2555,
            "database_path": "runtime/test.db",
            "llm_provider": "local-stub",
            "llm_model": "deterministic-v1"
        }

        manifest = compile_manifest_template(str(template_path), variables=variables)

        # Verify compiled manifest
        assert manifest["name"] == "Test SaaS"
        assert manifest["@id"] == "urn:uapk:testsaas:v1"
        assert "mint_nft" in manifest["corporateModules"]["policyGuardrails"]["liveActionGates"]


def test_simple_substitute():
    """Test simple string substitution (fallback when Jinja2 not available)"""
    template = "Hello {{name}}, your age is {{age}}"
    variables = {"name": "Alice", "age": 30}

    result = simple_substitute(template, variables)

    assert result == "Hello Alice, your age is 30"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
