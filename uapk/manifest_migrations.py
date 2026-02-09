"""
Manifest Migration Utilities (M2.1)
Converts between OpsPilotOS extended schema and canonical UAPK Gateway schema.
"""
import json
from typing import Dict, Any, List


def extract_capabilities_from_extended(extended: Dict[str, Any]) -> List[str]:
    """
    Extract capability list from extended OpsPilotOS manifest.
    Maps tool permissions and live action gates to capability strings.
    """
    capabilities = []

    # Extract from tool permissions (agentId:tool format)
    tool_perms = extended.get("corporateModules", {}).get("policyGuardrails", {}).get("toolPermissions", {})
    for agent_id, tools in tool_perms.items():
        for tool in tools:
            capability = f"{agent_id.lower()}:{tool}"
            if capability not in capabilities:
                capabilities.append(capability)

    # Extract from live action gates (gated actions)
    gates = extended.get("corporateModules", {}).get("policyGuardrails", {}).get("liveActionGates", [])
    for gate in gates:
        if gate not in capabilities:
            capabilities.append(gate)

    # If no capabilities found, add a default
    if not capabilities:
        capabilities = ["default:execute"]

    return sorted(capabilities)


def migrate_extended_to_canonical(extended: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OpsPilotOS extended manifest to canonical UAPK Gateway format.

    Canonical structure:
    {
      "version": "1.0",
      "agent": {...},
      "capabilities": {"requested": [...]},
      "constraints": {...},
      "metadata": {...},
      "policy": {...},
      "tools": {...},
      "extensions": {"opspilotos": <original_extended_manifest>}
    }

    Args:
        extended: OpsPilotOS extended manifest dict

    Returns:
        Canonical UAPK Gateway manifest dict
    """
    # Extract core identifiers
    agent_id = extended.get("@id", "").replace("urn:uapk:", "").replace(":", "-")
    if not agent_id:
        agent_id = "opspilotos-001"

    # Build canonical agent section
    agent = {
        "id": agent_id,
        "name": extended.get("name", "OpsPilotOS"),
        "version": extended.get("uapkVersion", "0.1"),
        "description": extended.get("description", ""),
        "organization": "default",
        "team": None
    }

    # Build capabilities section
    capabilities = {
        "requested": extract_capabilities_from_extended(extended)
    }

    # Build constraints section
    guardrails = extended.get("corporateModules", {}).get("policyGuardrails", {})
    rate_limits = guardrails.get("rateLimits", {})

    constraints = {
        "max_actions_per_hour": rate_limits.get("actionsPerMinute", 100) * 60,
        "max_actions_per_day": rate_limits.get("actionsPerMinute", 100) * 60 * 24,
        "require_human_approval": guardrails.get("liveActionGates", []),
        "allowed_hours": None  # Not in extended schema
    }

    # Build metadata section
    metadata = {
        "contact": None,
        "documentation": None,
        "source": "OpsPilotOS Extended Schema"
    }

    # Build policy section (maps OpsPilotOS policy to canonical)
    policy = {
        "budgets": {},
        "counterparty_allowlist": None,
        "counterparty_denylist": None,
        "jurisdiction_allowlist": None,
        "tool_allowlist": None,
        "tool_denylist": None,
        "amount_caps": None,
        "approval_thresholds": {
            "action_types": guardrails.get("liveActionGates", []),
            "tools": None,
            "amount": None,
            "currency": None
        },
        "require_capability_token": False
    }

    # Add rate limit budgets
    if rate_limits:
        # Map rate limits to budgets per action type
        for gate in guardrails.get("liveActionGates", []):
            policy["budgets"][gate] = {
                "hourly_limit": rate_limits.get("actionsPerMinute", 100) * 60,
                "daily_limit": rate_limits.get("invoicesPerDay") if gate == "send_invoice_email" else None,
                "total_limit": None
            }

    # Build tools section (from connectors)
    tools = {}
    connectors = extended.get("aiOsModules", {}).get("connectors", {})
    for connector_name, connector_config in connectors.items():
        connector_type = connector_config.get("type", "mock")

        # Map connector type
        if connector_type == "simulated":
            tool_type = "mock"
        elif connector_type in ["http", "httpApi"]:
            tool_type = "http_request"
        elif connector_type == "webhook":
            tool_type = "webhook"
        else:
            tool_type = "mock"

        tools[connector_name] = {
            "type": tool_type,
            "config": connector_config
        }

    # Build canonical manifest
    canonical = {
        "version": "1.0",
        "agent": agent,
        "capabilities": capabilities,
        "constraints": constraints,
        "metadata": metadata,
        "policy": policy,
        "tools": tools if tools else None,
        "extensions": {
            "opspilotos": extended  # Preserve full extended manifest
        }
    }

    return canonical


def migrate_canonical_to_extended(canonical: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert canonical UAPK Gateway manifest back to OpsPilotOS extended format.
    Uses extensions.opspilotos if present, otherwise reconstructs.

    Args:
        canonical: Canonical UAPK Gateway manifest

    Returns:
        OpsPilotOS extended manifest dict
    """
    # If extensions.opspilotos exists, use it
    if "extensions" in canonical and "opspilotos" in canonical["extensions"]:
        return canonical["extensions"]["opspilotos"]

    # Otherwise, reconstruct extended format (lossy conversion)
    agent = canonical.get("agent", {})
    constraints = canonical.get("constraints", {})
    policy = canonical.get("policy", {})

    extended = {
        "@context": "https://uapk.ai/context/v0.1",
        "@id": f"urn:uapk:{agent.get('id', 'opspilotos-001')}",
        "uapkVersion": agent.get("version", "0.1"),
        "name": agent.get("name", "OpsPilotOS"),
        "description": agent.get("description", ""),
        "executionMode": "dry_run",
        "cryptoHeader": {
            "hashAlg": "sha256",
            "manifestHash": "",
            "planHash": "",
            "merkleRoot": "",
            "signature": "dev-signature-placeholder",
            "signedBy": "OpsPilotOS-Dev-Key",
            "signedAt": None
        },
        "corporateModules": {
            "policyGuardrails": {
                "toolPermissions": {},  # Would need to reconstruct from capabilities
                "denyRules": [],
                "rateLimits": {
                    "actionsPerMinute": constraints.get("max_actions_per_hour", 100) // 60
                },
                "liveActionGates": constraints.get("require_human_approval", [])
            }
        }
    }

    return extended


def validate_canonical_manifest(manifest: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a canonical UAPK manifest against schema requirements.

    Returns:
        (valid: bool, errors: List[str])
    """
    errors = []

    # Check required top-level fields
    required_fields = ["version", "agent", "capabilities"]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    # Check version
    if "version" in manifest and manifest["version"] != "1.0":
        errors.append(f"Invalid version: {manifest['version']} (expected '1.0')")

    # Check agent
    if "agent" in manifest:
        agent = manifest["agent"]
        required_agent_fields = ["id", "name", "version"]
        for field in required_agent_fields:
            if field not in agent:
                errors.append(f"Missing required agent field: {field}")

    # Check capabilities
    if "capabilities" in manifest:
        capabilities = manifest["capabilities"]
        if "requested" not in capabilities:
            errors.append("Missing 'requested' field in capabilities")
        elif not isinstance(capabilities["requested"], list):
            errors.append("'requested' must be a list")
        elif len(capabilities["requested"]) == 0:
            errors.append("'requested' capabilities list cannot be empty")

    return len(errors) == 0, errors


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m uapk.manifest_migrations <extended_manifest.jsonld>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        extended = json.load(f)

    canonical = migrate_extended_to_canonical(extended)

    # Validate
    valid, errors = validate_canonical_manifest(canonical)
    if not valid:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Output canonical
    print(json.dumps(canonical, indent=2))
