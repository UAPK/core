"""
UAPK CLI
Commands: verify, run, mint
"""
import sys
import json
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install typer", file=sys.stderr)
    sys.exit(1)

from uapk.interpreter import ManifestInterpreter, verify_manifest
from uapk.policy import init_policy_engine
from uapk.audit import get_audit_log, AuditLog  # M1.2
from uapk.cas import ContentAddressedStore


app = typer.Typer(
    name="uapk",
    help="UAPK CLI - OpsPilotOS Autonomous SaaS Runtime",
    add_completion=False
)


@app.command()
def verify(
    manifest: str = typer.Argument(..., help="Path to UAPK manifest (JSON-LD)"),
    output: str = typer.Option("runtime/plan.json", help="Output path for resolved plan")
):
    """
    Verify UAPK manifest: validate schema, compute hashes, resolve plan.
    Produces deterministic plan.json and plan.lock.json files.
    """
    typer.echo(f"[UAPK VERIFY] Loading manifest: {manifest}")

    result = verify_manifest(manifest)

    if result['valid']:
        typer.secho("✓ Manifest verified successfully", fg=typer.colors.GREEN)
        typer.echo(f"  manifestHash: {result['manifestHash']}")
        typer.echo(f"  planHash: {result['planHash']}")
        typer.echo(f"  executionMode: {result['executionMode']}")
        typer.echo(f"  Outputs:")
        typer.echo(f"    - runtime/plan.json")
        typer.echo(f"    - runtime/plan.lock.json")
        typer.echo(f"    - runtime/manifest_resolved.jsonld")
        sys.exit(0)
    else:
        typer.secho(f"✗ Manifest verification failed: {result['message']}", fg=typer.colors.RED)
        sys.exit(1)


@app.command()
def run(
    manifest: str = typer.Argument(..., help="Path to UAPK manifest (JSON-LD)"),
    daemon: bool = typer.Option(False, help="Run in daemon mode (background)")
):
    """
    Run OpsPilotOS: verify manifest, boot services, start agents.
    This command starts the FastAPI server and autonomous agents.
    """
    typer.echo(f"[UAPK RUN] Starting OpsPilotOS from: {manifest}")

    # Step 1: Verify manifest
    typer.echo("Step 1/4: Verifying manifest...")
    result = verify_manifest(manifest)

    if not result['valid']:
        typer.secho(f"✗ Verification failed: {result['message']}", fg=typer.colors.RED)
        sys.exit(1)

    typer.secho("✓ Manifest verified", fg=typer.colors.GREEN)

    # Step 2: Load manifest
    typer.echo("Step 2/4: Loading manifest...")
    interpreter = ManifestInterpreter(manifest)
    loaded_manifest = interpreter.load()

    # Step 3: Initialize subsystems
    typer.echo("Step 3/4: Initializing subsystems...")
    init_policy_engine(loaded_manifest)
    audit_log = get_audit_log()

    # Log startup event
    audit_log.append_event(
        event_type="system",
        action="startup",
        params={
            'manifestHash': result['manifestHash'],
            'planHash': result['planHash'],
            'executionMode': result['executionMode']
        }
    )

    typer.secho("✓ Subsystems initialized", fg=typer.colors.GREEN)

    # Step 4: Start API server
    typer.echo("Step 4/4: Starting API server...")
    typer.echo(f"  executionMode: {loaded_manifest.executionMode}")
    typer.echo(f"  API: http://localhost:8000")
    typer.echo(f"  Docs: http://localhost:8000/docs")

    # Import and run FastAPI app
    try:
        from uapk.api.main import create_app
        import uvicorn

        app_instance = create_app(loaded_manifest)

        typer.secho("✓ OpsPilotOS running", fg=typer.colors.GREEN)

        uvicorn.run(
            app_instance,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )

    except ImportError as e:
        typer.secho(f"✗ Failed to start API: {e}", fg=typer.colors.RED)
        typer.echo("  Run: pip install fastapi uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        typer.echo("\n[UAPK RUN] Shutting down...")
        audit_log.append_event(
            event_type="system",
            action="shutdown",
            params={}
        )
        sys.exit(0)


@app.command()
def mint(
    manifest: str = typer.Argument(..., help="Path to UAPK manifest (JSON-LD)"),
    force: bool = typer.Option(False, help="Force mint without approval (dangerous)")
):
    """
    Mint NFT representing this business instance.
    Creates content-addressed bundle and mints on local blockchain.
    Requires approval in dry_run mode unless --force is used.
    """
    typer.echo(f"[UAPK MINT] Minting NFT for: {manifest}")

    # Verify manifest
    typer.echo("Step 1/5: Verifying manifest...")
    result = verify_manifest(manifest)

    if not result['valid']:
        typer.secho(f"✗ Verification failed: {result['message']}", fg=typer.colors.RED)
        sys.exit(1)

    # Load manifest
    interpreter = ManifestInterpreter(manifest)
    loaded_manifest = interpreter.load()

    # Check execution mode
    if loaded_manifest.executionMode == "dry_run" and not force:
        typer.echo("\n⚠️  WARNING: Execution mode is 'dry_run'")
        typer.echo("   NFT minting requires approval or --force flag")
        typer.echo("   Use 'uapk mint --force' to bypass (not recommended)")
        sys.exit(1)

    # Step 2: Compute merkle root
    typer.echo("Step 2/5: Computing audit merkle root...")
    audit_log = get_audit_log()
    merkle_root = audit_log.compute_merkle_root()

    typer.echo(f"  merkleRoot: {merkle_root}")

    # Step 3: Create CAS bundle
    typer.echo("Step 3/5: Creating content-addressed bundle...")
    cas = ContentAddressedStore()

    # Store manifest
    manifest_content = Path(manifest).read_bytes()
    manifest_cas_hash = cas.put(manifest_content)

    # Store plan
    plan_content = Path("runtime/plan.lock.json").read_bytes()
    plan_cas_hash = cas.put(plan_content)

    # Create NFT metadata
    nft_metadata = {
        "name": f"{loaded_manifest.name} Business Instance",
        "description": loaded_manifest.description,
        "image": "ipfs://placeholder",  # Would be actual logo
        "attributes": [
            {"trait_type": "Manifest Hash", "value": result['manifestHash']},
            {"trait_type": "Plan Hash", "value": result['planHash']},
            {"trait_type": "Audit Merkle Root", "value": merkle_root},
            {"trait_type": "Execution Mode", "value": loaded_manifest.executionMode}
        ],
        "properties": {
            "manifestCAS": manifest_cas_hash,
            "planCAS": plan_cas_hash,
            "uapkVersion": loaded_manifest.uapkVersion
        }
    }

    metadata_hash = cas.put_json(nft_metadata)
    typer.echo(f"  metadataHash: {metadata_hash}")

    # Step 4: Mint NFT (simulated for now; would call blockchain)
    typer.echo("Step 4/5: Minting NFT on local chain...")

    try:
        from uapk.nft.minter import mint_business_nft

        receipt = mint_business_nft(
            metadata_uri=cas.uri(metadata_hash),
            manifest_hash=result['manifestHash'],
            plan_hash=result['planHash'],
            merkle_root=merkle_root
        )

        typer.secho("✓ NFT minted successfully", fg=typer.colors.GREEN)
        typer.echo(f"  Contract: {receipt['contract']}")
        typer.echo(f"  Token ID: {receipt['tokenId']}")
        typer.echo(f"  Chain ID: {receipt['chainId']}")

    except ImportError:
        # Fallback: create simulated receipt
        typer.echo("  (Blockchain not available, creating simulated receipt)")

        receipt = {
            "contract": "0x0000000000000000000000000000000000000000",
            "tokenId": 1,
            "chainId": 31337,
            "metadataURI": cas.uri(metadata_hash),
            "manifestHash": result['manifestHash'],
            "planHash": result['planHash'],
            "merkleRoot": merkle_root,
            "mintedAt": "simulated",
            "transactionHash": "0x0000000000000000000000000000000000000000000000000000000000000000"
        }

        typer.secho("✓ Simulated NFT mint", fg=typer.colors.YELLOW)

    # Step 5: Write receipt
    typer.echo("Step 5/5: Writing mint receipt...")
    receipt_path = Path("runtime/nft_mint_receipt.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    with open(receipt_path, 'w') as f:
        json.dump(receipt, f, indent=2)

    typer.echo(f"  Receipt: {receipt_path}")

    # Audit event
    audit_log.append_event(
        event_type="nft",
        action="mint_business_instance",
        params=nft_metadata,
        result=receipt
    )

    typer.secho("\n✓ NFT minting complete", fg=typer.colors.GREEN, bold=True)


@app.command()
def info(
    manifest: str = typer.Argument(..., help="Path to UAPK manifest (JSON-LD)")
):
    """
    Display information about a UAPK manifest.
    """
    interpreter = ManifestInterpreter(manifest)
    loaded_manifest = interpreter.load()

    typer.echo(f"\n{loaded_manifest.name}")
    typer.echo(f"{'=' * len(loaded_manifest.name)}")
    typer.echo(f"Description: {loaded_manifest.description}")
    typer.echo(f"Version: {loaded_manifest.uapkVersion}")
    typer.echo(f"Execution Mode: {loaded_manifest.executionMode}")
    typer.echo(f"\nAgents: {len(loaded_manifest.aiOsModules.agentProfiles)}")
    for agent in loaded_manifest.aiOsModules.agentProfiles:
        typer.echo(f"  - {agent.agentId} ({agent.role})")

    typer.echo(f"\nWorkflows: {len(loaded_manifest.aiOsModules.workflows)}")
    for workflow in loaded_manifest.aiOsModules.workflows:
        typer.echo(f"  - {workflow.workflowId} ({len(workflow.steps)} steps)")

    typer.echo()


@app.command()
def verify_audit(
    audit_log_path: str = typer.Argument("runtime/audit.jsonl", help="Path to audit log file")
):
    """
    M1.2: Verify audit log integrity (hash chain + Ed25519 signatures).
    Checks both previousHash chain and event signatures.
    """
    typer.echo(f"[UAPK VERIFY-AUDIT] Verifying audit log: {audit_log_path}")

    # Load audit log
    audit_log = AuditLog(log_path=audit_log_path)

    # Step 1: Verify hash chain
    typer.echo("\nStep 1/3: Verifying hash chain...")
    chain_result = audit_log.verify_chain()

    if chain_result['valid']:
        typer.secho(f"✓ Hash chain valid ({chain_result['eventCount']} events)", fg=typer.colors.GREEN)
    else:
        typer.secho(f"✗ Hash chain INVALID: {chain_result['message']}", fg=typer.colors.RED)
        sys.exit(1)

    # Step 2: Verify Ed25519 signatures
    typer.echo("\nStep 2/3: Verifying Ed25519 signatures...")
    sig_result = audit_log.verify_signatures()

    if sig_result['valid']:
        typer.secho(
            f"✓ All signatures valid ({sig_result['verified_count']} verified)",
            fg=typer.colors.GREEN
        )
    else:
        typer.secho(
            f"✗ Signature verification FAILED: {sig_result['message']}",
            fg=typer.colors.RED
        )
        if sig_result.get('failed_events'):
            typer.echo("\nFailed events:")
            for failed in sig_result['failed_events'][:5]:
                typer.echo(f"  - Event {failed['eventId']}: {failed['reason']}")
        sys.exit(1)

    # Step 3: Compute merkle root
    typer.echo("\nStep 3/3: Computing merkle root...")
    merkle_root = audit_log.compute_merkle_root()
    typer.echo(f"  Merkle root: {merkle_root}")

    typer.secho("\n✓ Audit log verification complete", fg=typer.colors.GREEN)
    typer.echo(f"  Events: {chain_result['eventCount']}")
    typer.echo(f"  Hash chain: VALID")
    typer.echo(f"  Signatures: VALID ({sig_result['verified_count']} verified)")
    typer.echo(f"  Merkle root: {merkle_root}")


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
