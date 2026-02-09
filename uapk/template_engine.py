"""
Template Engine for UAPK Manifests (M3.1)
Provides Jinja2-based variable substitution for parameterized manifests.
"""
import json
import os
import yaml
from typing import Dict, Any
from pathlib import Path


# Try to import Jinja2, provide graceful fallback
try:
    from jinja2 import Environment, Template, FileSystemLoader, StrictUndefined
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class TemplateEngine:
    """
    Manifest template engine using Jinja2.
    Supports variable substitution, conditionals, and loops.
    """

    def __init__(self):
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2 not installed. Install with: pip install Jinja2"
            )

        # Create Jinja2 environment with strict undefined (fail on missing variables)
        self.env = Environment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )

        # Add custom filters
        self.env.filters['env'] = self._env_filter
        self.env.filters['tojson'] = self._tojson_filter

    def _tojson_filter(self, value: Any) -> str:
        """Convert Python value to JSON (handles booleans correctly)"""
        return json.dumps(value)

    def _env_filter(self, var_name: str, default: str = None) -> str:
        """
        Jinja2 filter to load environment variables.
        Usage: {{ "OPENAI_API_KEY" | env }}
        """
        value = os.environ.get(var_name, default)
        if value is None:
            raise ValueError(f"Environment variable {var_name} not set")
        return value

    def compile_template(
        self,
        template_path: Path,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compile a manifest template by substituting variables.

        Args:
            template_path: Path to template file (.jsonld or .json with Jinja2 syntax)
            variables: Dictionary of variables to substitute

        Returns:
            Compiled manifest as dict

        Raises:
            FileNotFoundError: Template file not found
            ValueError: Invalid template or missing variables
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Load template file
        with open(template_path, 'r') as f:
            template_content = f.read()

        # Add environment variables to context
        context = variables.copy()
        context['env'] = os.environ

        # Render template
        try:
            template = self.env.from_string(template_content)
            # Add tojson to globals for auto-conversion
            rendered = template.render(context, tojson=json.dumps)
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}")

        # Parse rendered JSON
        try:
            manifest = json.loads(rendered)
        except json.JSONDecodeError as e:
            raise ValueError(f"Rendered template is not valid JSON: {e}")

        return manifest

    def load_variables(self, vars_path: Path) -> Dict[str, Any]:
        """
        Load variables from YAML file.

        Args:
            vars_path: Path to variables file (.yaml or .yml)

        Returns:
            Variables dictionary
        """
        if not vars_path.exists():
            raise FileNotFoundError(f"Variables file not found: {vars_path}")

        with open(vars_path, 'r') as f:
            try:
                variables = yaml.safe_load(f)
                if not isinstance(variables, dict):
                    raise ValueError("Variables file must contain a YAML dictionary")
                return variables
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in variables file: {e}")

    def validate_template(self, template_path: Path) -> tuple[bool, list[str]]:
        """
        Validate template syntax without rendering.

        Args:
            template_path: Path to template file

        Returns:
            (valid: bool, errors: list[str])
        """
        errors = []

        if not template_path.exists():
            return False, [f"Template file not found: {template_path}"]

        try:
            with open(template_path, 'r') as f:
                template_content = f.read()

            # Parse template (checks Jinja2 syntax)
            self.env.from_string(template_content)

        except Exception as e:
            errors.append(f"Invalid template syntax: {e}")

        return len(errors) == 0, errors


def compile_manifest_template(
    template_path: str,
    vars_path: str = None,
    variables: Dict[str, Any] = None,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Convenience function to compile a manifest template.

    Args:
        template_path: Path to template file
        vars_path: Path to variables YAML file (optional)
        variables: Variables dict (optional, overrides vars_path)
        output_path: Output path to write compiled manifest (optional)

    Returns:
        Compiled manifest dict
    """
    engine = TemplateEngine()

    # Load variables
    if variables is None:
        if vars_path:
            variables = engine.load_variables(Path(vars_path))
        else:
            variables = {}

    # Compile template
    manifest = engine.compile_template(Path(template_path), variables)

    # Write output if specified
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    return manifest


# Simple string-based template rendering (fallback if Jinja2 not available)
def simple_substitute(template: str, variables: Dict[str, Any]) -> str:
    """
    Simple variable substitution without Jinja2.
    Only supports {{variable}} syntax, no conditionals or loops.

    Args:
        template: Template string
        variables: Variables to substitute

    Returns:
        Rendered string
    """
    result = template
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result
