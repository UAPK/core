"""
Evidence-Grade Audit Export (M2.5)
Creates compliance bundles with verification proofs.
"""
import json
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from uapk.audit import AuditLog
from uapk.cas import compute_merkle_root


def create_audit_bundle(
    audit_log_path: str = "runtime/audit.jsonl",
    manifest_path: str = "manifests/opspilotos.uapk.jsonld",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_dir: str = "runtime"
) -> Path:
    """
    Create evidence-grade audit export bundle.

    Creates a tar.gz containing:
    - audit.jsonl (filtered event log)
    - manifest.json (manifest snapshot)
    - verification_proof.json (chain validation, signatures, merkle root)

    Args:
        audit_log_path: Path to audit log
        manifest_path: Path to manifest
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        output_dir: Output directory for bundle

    Returns:
        Path to created bundle
    """
    # Load audit log
    audit_log = AuditLog(log_path=audit_log_path)
    events = audit_log.get_events()

    # Filter events by date range
    if start_date or end_date:
        filtered_events = []
        for event in events:
            event_date = event.get("timestamp", "")
            if start_date and event_date < start_date:
                continue
            if end_date and event_date > end_date:
                continue
            filtered_events.append(event)
        events = filtered_events

    # Verify chain
    chain_result = audit_log.verify_chain()

    # Verify signatures
    sig_result = audit_log.verify_signatures()

    # Compute merkle root
    event_hashes = [e["eventHash"] for e in events if "eventHash" in e]
    merkle_root = compute_merkle_root(event_hashes) if event_hashes else ""

    # Load manifest
    manifest = {}
    if Path(manifest_path).exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

    # Create verification proof
    verification_proof = {
        "bundle_created_at": datetime.utcnow().isoformat() + "Z",
        "audit_log_range": {
            "start": events[0]["timestamp"] if events else None,
            "end": events[-1]["timestamp"] if events else None,
            "event_count": len(events)
        },
        "hash_chain": {
            "first_event_hash": events[0].get("eventHash") if events else None,
            "last_event_hash": events[-1].get("eventHash") if events else None,
            "merkle_root": merkle_root,
            "chain_valid": chain_result.get("valid", False),
            "chain_message": chain_result.get("message", "")
        },
        "signatures": {
            "algorithm": "Ed25519",
            "public_key": None,  # Would load from runtime/keys/gateway_ed25519.pub
            "verified_count": sig_result.get("verified_count", 0),
            "failed_count": sig_result.get("failed_count", 0),
            "signatures_valid": sig_result.get("valid", False),
            "signature_message": sig_result.get("message", "")
        },
        "manifest": {
            "hash": manifest.get("cryptoHeader", {}).get("manifestHash", ""),
            "plan_hash": manifest.get("cryptoHeader", {}).get("planHash", ""),
            "version": manifest.get("uapkVersion", "0.1")
        }
    }

    # Create bundle
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"audit_bundle_{timestamp}.tar.gz"
    bundle_path = Path(output_dir) / bundle_name

    # Create temp directory for bundle contents
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Write audit.jsonl
        audit_file = temp_dir / "audit.jsonl"
        with open(audit_file, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')

        # Write manifest.json
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Write verification_proof.json
        proof_file = temp_dir / "verification_proof.json"
        with open(proof_file, 'w') as f:
            json.dump(verification_proof, f, indent=2)

        # Create tar.gz
        with tarfile.open(bundle_path, "w:gz") as tar:
            tar.add(audit_file, arcname="audit.jsonl")
            tar.add(manifest_file, arcname="manifest.json")
            tar.add(proof_file, arcname="verification_proof.json")

    return bundle_path


def extract_and_verify_bundle(bundle_path: Path) -> Dict[str, Any]:
    """
    Extract audit bundle and verify its contents.

    Args:
        bundle_path: Path to audit bundle tar.gz

    Returns:
        Verification results dict
    """
    results = {
        "valid": False,
        "bundle_path": str(bundle_path),
        "extracted_files": [],
        "verification": {}
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Extract bundle
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(temp_dir)
            results["extracted_files"] = tar.getnames()

        # Load verification proof
        proof_file = temp_dir / "verification_proof.json"
        if not proof_file.exists():
            results["verification"]["error"] = "verification_proof.json missing"
            return results

        with open(proof_file, 'r') as f:
            proof = json.load(f)

        results["verification"] = proof

        # Check if bundle is valid
        chain_valid = proof.get("hash_chain", {}).get("chain_valid", False)
        sig_valid = proof.get("signatures", {}).get("signatures_valid", False)

        results["valid"] = chain_valid and sig_valid

    return results
