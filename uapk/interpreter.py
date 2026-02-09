"""
UAPK Interpreter
Loads, validates, and resolves UAPK manifests into deterministic execution plans.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Any

from uapk.manifest_schema import UAPKManifest, ResolvedPlan


class ManifestInterpreter:
    """Interprets and resolves UAPK manifests"""

    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.manifest: Optional[UAPKManifest] = None
        self.manifest_hash: str = ""

    def load(self) -> UAPKManifest:
        """Load and validate manifest from JSON-LD"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        with open(self.manifest_path, 'r') as f:
            manifest_data = json.load(f)

        # Validate with Pydantic
        self.manifest = UAPKManifest(**manifest_data)

        # Compute manifest hash (canonical JSON)
        manifest_json = self.manifest.model_dump(by_alias=True, exclude={'cryptoHeader'})
        canonical = json.dumps(manifest_json, sort_keys=True, separators=(',', ':'))
        self.manifest_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

        # Update crypto header
        self.manifest.cryptoHeader.manifestHash = self.manifest_hash

        return self.manifest

    def resolve_plan(self) -> ResolvedPlan:
        """
        Resolve the manifest into a deterministic execution plan.
        This includes all runtime configuration, agents, workflows, connectors, and policies.
        """
        if not self.manifest:
            raise RuntimeError("Manifest not loaded. Call load() first.")

        # Build resolved plan
        plan = ResolvedPlan(
            manifestHash=self.manifest_hash,
            executionMode=self.manifest.executionMode,
            agents=self.manifest.aiOsModules.agentProfiles,
            workflows=self.manifest.aiOsModules.workflows,
            connectors={
                'httpApi': self.manifest.connectors.httpApi.model_dump(),
                'database': self.manifest.connectors.database.model_dump(),
                'objectStore': self.manifest.connectors.objectStore.model_dump(),
                'vectorStore': self.manifest.connectors.vectorStore.model_dump(),
                'mailer': self.manifest.connectors.mailer.model_dump(),
                'payments': self.manifest.connectors.payments.model_dump(),
                'nftChain': self.manifest.connectors.nftChain.model_dump(),
                'contentAddressing': self.manifest.connectors.contentAddressing.model_dump()
            },
            policyRules={
                'toolPermissions': self.manifest.corporateModules.policyGuardrails.toolPermissions,
                'denyRules': self.manifest.corporateModules.policyGuardrails.denyRules,
                'rateLimits': self.manifest.corporateModules.policyGuardrails.rateLimits,
                'liveActionGates': self.manifest.corporateModules.policyGuardrails.liveActionGates
            }
        )

        # Compute plan hash (canonical JSON of the plan, excluding planHash itself)
        plan_dict = plan.model_dump(exclude={'planHash', 'merkleRoot'})
        canonical_plan = json.dumps(plan_dict, sort_keys=True, separators=(',', ':'))
        plan_hash = hashlib.sha256(canonical_plan.encode('utf-8')).hexdigest()

        plan.planHash = plan_hash
        self.manifest.cryptoHeader.planHash = plan_hash

        return plan

    def write_plan(self, plan: ResolvedPlan, output_path: str = "runtime/plan.json"):
        """Write resolved plan to JSON file"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, 'w') as f:
            json.dump(plan.model_dump(), f, indent=2, sort_keys=False)

        # Also write a deterministic lock file (sorted keys, no whitespace)
        lock_path = output.parent / "plan.lock.json"
        with open(lock_path, 'w') as f:
            json.dump(plan.model_dump(), f, sort_keys=True, separators=(',', ':'))

    def write_manifest_with_hashes(self, output_path: str = "runtime/manifest_resolved.jsonld"):
        """Write manifest with updated crypto header to file"""
        if not self.manifest:
            raise RuntimeError("Manifest not loaded")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, 'w') as f:
            json.dump(
                self.manifest.model_dump(by_alias=True),
                f,
                indent=2
            )


def load_manifest(manifest_path: str) -> UAPKManifest:
    """Convenience function to load a manifest"""
    interpreter = ManifestInterpreter(manifest_path)
    return interpreter.load()


def verify_manifest(manifest_path: str) -> Dict[str, Any]:
    """
    Verify manifest: load, validate schema, compute hashes, resolve plan.
    Returns verification result with hashes.
    """
    interpreter = ManifestInterpreter(manifest_path)

    try:
        # Load and validate
        manifest = interpreter.load()

        # Resolve plan
        plan = interpreter.resolve_plan()

        # Write outputs
        interpreter.write_plan(plan)
        interpreter.write_manifest_with_hashes()

        return {
            'valid': True,
            'manifestHash': interpreter.manifest_hash,
            'planHash': plan.planHash,
            'executionMode': manifest.executionMode,
            'message': 'Manifest verified successfully'
        }

    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'message': f'Manifest verification failed: {e}'
        }
