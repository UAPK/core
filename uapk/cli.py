"""
UAPK CLI
Commands: verify, run, mint, compile, plan, package, chain, nft, fleet, doctor
"""
import sys
import os
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
from uapk.manifest_migrations import migrate_extended_to_canonical, validate_canonical_manifest  # M2.1
from uapk.platform.paths import get_platform_paths  # Phase 0


app = typer.Typer(
    name="uapk",
    help="UAPK CLI - Compiler/Transformator Node & Gateway Runtime",
    add_completion=False
)


@app.command()
def doctor():
    """
    Phase 0: Check VM transformator platform health.
    Verifies paths, environment variables, and service readiness.
    """
    typer.echo("[UAPK DOCTOR] Checking platform health...")
    typer.echo("")

    paths = get_platform_paths()

    # Check paths
    typer.echo("Platform Paths:")
    typer.echo(f"  Code:      {paths.code_dir}")
    typer.echo(f"  Data:      {paths.data_dir}")
    typer.echo(f"  Instances: {paths.instances_dir()}")
    typer.echo(f"  CAS:       {paths.cas_dir()}")
    typer.echo(f"  DB:        {paths.db_dir()}")
    typer.echo(f"  Runtime:   {paths.runtime_dir()}")
    typer.echo(f"  Logs:      {paths.log_dir}")
    typer.echo("")

    # Check writability
    typer.echo("Writability Check:")
    writable_results = paths.check_writable()
    all_writable = True

    for name, result in writable_results.items():
        status = "✓" if result['writable'] else "✗"
        color = typer.colors.GREEN if result['writable'] else typer.colors.RED
        typer.secho(f"  {status} {name}: {result['path']}", fg=color)
        if not result['writable']:
            typer.echo(f"     Error: {result.get('error', 'Not writable')}")
            all_writable = False

    typer.echo("")

    # Check required environment variables
    typer.echo("Environment Variables:")
    required_vars = {
        'UAPK_JWT_SECRET_KEY': 'JWT signing key',
        'UAPK_FERNET_KEY': 'Database encryption key'
    }

    optional_vars = {
        'UAPK_CHAIN_RPC': 'Local chain RPC (default: http://127.0.0.1:8545)',
        'UAPK_CHAIN_PRIVATE_KEY': 'Chain private key for minting',
        'UAPK_NFT_CONTRACT_ADDRESS': 'Deployed NFT contract address'
    }

    all_env_ok = True
    for var, desc in required_vars.items():
        if os.environ.get(var):
            typer.secho(f"  ✓ {var}: SET", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ✗ {var}: MISSING ({desc})", fg=typer.colors.RED)
            all_env_ok = False

    for var, desc in optional_vars.items():
        if os.environ.get(var):
            typer.secho(f"  ✓ {var}: SET", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ⚠ {var}: NOT SET ({desc})", fg=typer.colors.YELLOW)

    typer.echo("")

    # Check chain RPC reachability
    typer.echo("Chain Connectivity:")
    chain_rpc = os.environ.get('UAPK_CHAIN_RPC', 'http://127.0.0.1:8545')
    try:
        import requests
        response = requests.post(
            chain_rpc,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=2
        )
        if response.status_code == 200:
            typer.secho(f"  ✓ Chain RPC reachable: {chain_rpc}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ✗ Chain RPC error: {response.status_code}", fg=typer.colors.RED)
    except ImportError:
        typer.secho(f"  ⚠ requests module not available (cannot test)", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"  ✗ Chain RPC unreachable: {chain_rpc}", fg=typer.colors.RED)
        typer.echo(f"     Error: {str(e)}")

    typer.echo("")

    # Check database connectivity
    typer.echo("Database Connectivity:")
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            # Try to import SQLAlchemy
            from sqlalchemy import create_engine, text
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            typer.secho(f"  ✓ Database connected: {database_url.split('@')[-1] if '@' in database_url else 'local'}", fg=typer.colors.GREEN)
        except ImportError:
            typer.secho(f"  ⚠ SQLAlchemy not available (cannot test)", fg=typer.colors.YELLOW)
        except Exception as e:
            typer.secho(f"  ✗ Database connection failed", fg=typer.colors.RED)
            typer.echo(f"     Error: {str(e)}")
    else:
        typer.secho(f"  ⚠ DATABASE_URL not set (using SQLite or not configured)", fg=typer.colors.YELLOW)

    typer.echo("")

    # Overall status
    if all_writable and all_env_ok:
        typer.secho("✓ Platform is healthy and ready!", fg=typer.colors.GREEN)
        sys.exit(0)
    else:
        typer.secho("⚠ Platform has issues. Fix above errors to continue.", fg=typer.colors.YELLOW)
        sys.exit(1)


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
    manifest: Optional[str] = typer.Argument(None, help="Path to UAPK manifest (JSON-LD)"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Instance ID from fleet registry"),
    daemon: bool = typer.Option(False, help="Run in daemon mode (background)")
):
    """
    Run OpsPilotOS: verify manifest, boot services, start agents.
    This command starts the FastAPI server and autonomous agents.

    You can specify either a manifest path or an instance ID (from fleet).
    """
    # Resolve manifest path from instance ID if provided
    if instance:
        from uapk.fleet.db import get_fleet_db
        fleet_db = get_fleet_db()
        instance_data = fleet_db.get_instance(instance)
        fleet_db.close()

        if not instance_data:
            typer.secho(f"✗ Instance '{instance}' not found in fleet registry", fg=typer.colors.RED)
            sys.exit(1)

        manifest = instance_data['manifest_path']
        typer.echo(f"[UAPK RUN] Running instance '{instance}' from fleet registry")
    elif not manifest:
        typer.secho("✗ Either manifest path or --instance must be provided", fg=typer.colors.RED)
        sys.exit(1)

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


@app.command()
def migrate(
    manifest: str = typer.Argument(..., help="Path to source manifest (extended schema)"),
    output: str = typer.Option(None, "--output", "-o", help="Output path for canonical manifest"),
    validate_only: bool = typer.Option(False, "--validate-only", help="Only validate, don't write output")
):
    """
    M2.1: Migrate OpsPilotOS extended manifest to canonical UAPK Gateway format.
    Converts corporateModules/aiOsModules structure to canonical agent/capabilities/policy structure.
    """
    typer.echo(f"[UAPK MIGRATE] Migrating manifest: {manifest}")

    # Load source manifest
    try:
        with open(manifest, 'r') as f:
            extended = json.load(f)
    except Exception as e:
        typer.secho(f"✗ Failed to load manifest: {e}", fg=typer.colors.RED)
        sys.exit(1)

    # Migrate to canonical
    try:
        canonical = migrate_extended_to_canonical(extended)
    except Exception as e:
        typer.secho(f"✗ Migration failed: {e}", fg=typer.colors.RED)
        sys.exit(1)

    # Validate canonical manifest
    valid, errors = validate_canonical_manifest(canonical)
    if not valid:
        typer.secho("✗ Canonical manifest validation failed:", fg=typer.colors.RED)
        for error in errors:
            typer.echo(f"  - {error}")
        sys.exit(1)

    typer.secho("✓ Migration successful", fg=typer.colors.GREEN)
    typer.echo(f"  Canonical version: {canonical['version']}")
    typer.echo(f"  Agent ID: {canonical['agent']['id']}")
    typer.echo(f"  Capabilities: {len(canonical['capabilities']['requested'])} requested")

    # Output
    if validate_only:
        typer.echo("  (validate-only mode: no output written)")
        sys.exit(0)

    if output:
        output_path = Path(output)
    else:
        # Default: same directory, add _canonical suffix
        manifest_path = Path(manifest)
        output_path = manifest_path.parent / f"{manifest_path.stem}_canonical{manifest_path.suffix}"

    try:
        with open(output_path, 'w') as f:
            json.dump(canonical, f, indent=2)
        typer.secho(f"✓ Canonical manifest written to: {output_path}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✗ Failed to write output: {e}", fg=typer.colors.RED)
        sys.exit(1)


def main():
    """Main entry point"""
    app()


# ============================================================================
# PHASE 2: COMPILER COMMANDS
# ============================================================================

@app.command()
def compile(
    template: str = typer.Argument(..., help="Path to template manifest"),
    params: str = typer.Option(None, "--params", "-p", help="Path to params YAML file"),
    out: str = typer.Option(None, "--out", "-o", help="Output instance directory")
):
    """
    Phase 2: Compile a business instance from template.
    Substitutes variables and creates instance manifest.
    """
    from uapk.template_engine import compile_manifest_template
    from uapk.fleet.db import get_fleet_db
    import yaml
    import hashlib

    typer.echo(f"[UAPK COMPILE] Compiling from template: {template}")

    # Load params
    if params:
        with open(params, 'r') as f:
            variables = yaml.safe_load(f)
    else:
        variables = {}

    # Get instance_id from params or generate
    instance_id = variables.get('instance_id') or variables.get('agent_prefix', 'instance-001')

    # Determine output directory
    if out:
        instance_dir = Path(out)
    else:
        paths = get_platform_paths()
        instance_dir = paths.instance_dir(instance_id)

    instance_dir.mkdir(parents=True, exist_ok=True)

    # Compile template
    try:
        manifest = compile_manifest_template(template, variables=variables)
    except Exception as e:
        typer.secho(f"✗ Compilation failed: {e}", fg=typer.colors.RED)
        sys.exit(1)

    # Write manifest
    manifest_path = instance_dir / 'manifest.jsonld'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    # Compute manifest hash
    canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
    manifest_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    # Register in fleet DB
    fleet_db = get_fleet_db()
    template_id = Path(template).stem
    fleet_db.register_instance(instance_id, template_id, str(manifest_path), manifest_hash)
    fleet_db.close()

    typer.secho("✓ Instance compiled successfully", fg=typer.colors.GREEN)
    typer.echo(f"  Instance ID: {instance_id}")
    typer.echo(f"  Manifest: {manifest_path}")
    typer.echo(f"  manifestHash: {manifest_hash[:16]}...")


@app.command()
def plan(
    manifest: str = typer.Argument(..., help="Path to instance manifest"),
    lock: str = typer.Option(None, "--lock", help="Output path for plan.lock.json")
):
    """
    Phase 2: Resolve deterministic execution plan from manifest.
    """
    from uapk.fleet.db import get_fleet_db

    typer.echo(f"[UAPK PLAN] Resolving plan from: {manifest}")

    # Use interpreter to resolve plan
    interpreter = ManifestInterpreter(manifest)

    try:
        # Load manifest
        loaded_manifest = interpreter.load()

        # Resolve plan
        resolved_plan = interpreter.resolve_plan()

        # Determine lock path
        if lock:
            lock_path = Path(lock)
        else:
            # Default: same directory as manifest
            lock_path = Path(manifest).parent / 'plan.lock.json'

        # Write plan lock
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, 'w') as f:
            json.dump(resolved_plan.model_dump(), f, sort_keys=True, separators=(',', ':'))

        # Update fleet DB
        instance_id = Path(manifest).parent.name
        fleet_db = get_fleet_db()
        fleet_db.update_plan_hash(instance_id, resolved_plan.planHash)
        fleet_db.close()

        typer.secho("✓ Plan resolved successfully", fg=typer.colors.GREEN)
        typer.echo(f"  planHash: {resolved_plan.planHash[:16]}...")
        typer.echo(f"  Plan lock: {lock_path}")
        typer.echo(f"  Agents: {len(resolved_plan.agents)}")
        typer.echo(f"  Workflows: {len(resolved_plan.workflows)}")

    except Exception as e:
        typer.secho(f"✗ Plan resolution failed: {e}", fg=typer.colors.RED)
        sys.exit(1)


@app.command()
def package(
    instance_dir: str = typer.Argument(..., help="Path to instance directory"),
    format: str = typer.Option("zip", help="Package format (zip)")
):
    """
    Phase 2: Package instance into CAS-addressed bundle.
    """
    from uapk.compiler.packager import package_instance
    from uapk.fleet.db import get_fleet_db

    typer.echo(f"[UAPK PACKAGE] Packaging instance: {instance_dir}")

    try:
        result = package_instance(Path(instance_dir), format=format)

        # Update fleet DB
        instance_id = Path(instance_dir).name
        fleet_db = get_fleet_db()
        fleet_db.update_package_hash(instance_id, result['packageHash'])
        fleet_db.close()

        typer.secho("✓ Package created successfully", fg=typer.colors.GREEN)
        typer.echo(f"  packageHash: {result['packageHash'][:16]}...")
        typer.echo(f"  Files: {len(result['files'])}")
        if result['package_path']:
            typer.echo(f"  ZIP: {result['package_path']}")

    except Exception as e:
        typer.secho(f"✗ Packaging failed: {e}", fg=typer.colors.RED)
        sys.exit(1)


# ============================================================================
# FLEET COMMANDS
# ============================================================================

fleet_app = typer.Typer(help="Fleet management commands")
app.add_typer(fleet_app, name="fleet")


@fleet_app.command("list")
def fleet_list(
    status: str = typer.Option(None, help="Filter by status")
):
    """List all instances in fleet"""
    from uapk.fleet.db import get_fleet_db

    fleet_db = get_fleet_db()
    instances = fleet_db.list_instances(status_filter=status)
    fleet_db.close()

    if not instances:
        typer.echo("No instances found")
        return

    typer.echo(f"Fleet Instances ({len(instances)} total):")
    typer.echo("")

    for inst in instances:
        status_color = {
            'compiled': typer.colors.BLUE,
            'planned': typer.colors.CYAN,
            'packaged': typer.colors.YELLOW,
            'minted': typer.colors.GREEN
        }.get(inst['status'], typer.colors.WHITE)

        typer.secho(f"  • {inst['instance_id']}", fg=typer.colors.BRIGHT_WHITE, bold=True)
        typer.echo(f"    Status: {inst['status']}", color=status_color)
        typer.echo(f"    Template: {inst['template_id']}")
        typer.echo(f"    Created: {inst['created_at'][:19]}")
        if inst['manifest_hash']:
            typer.echo(f"    manifestHash: {inst['manifest_hash'][:16]}...")
        if inst['nft_token_id']:
            typer.echo(f"    NFT Token: #{inst['nft_token_id']}")
        typer.echo("")


@fleet_app.command("show")
def fleet_show(
    instance_id: str = typer.Argument(..., help="Instance ID")
):
    """Show detailed info for an instance"""
    from uapk.fleet.db import get_fleet_db

    fleet_db = get_fleet_db()
    instance = fleet_db.get_instance(instance_id)
    versions = fleet_db.get_versions(instance_id)
    fleet_db.close()

    if not instance:
        typer.secho(f"✗ Instance not found: {instance_id}", fg=typer.colors.RED)
        sys.exit(1)

    typer.echo(f"Instance: {instance_id}")
    typer.echo("=" * 60)
    typer.echo(f"  Template: {instance['template_id']}")
    typer.echo(f"  Status: {instance['status']}")
    typer.echo(f"  Created: {instance['created_at']}")
    typer.echo(f"  Manifest: {instance['manifest_path']}")
    typer.echo(f"  manifestHash: {instance['manifest_hash']}")
    typer.echo(f"  planHash: {instance['plan_hash'] or 'Not resolved'}")
    typer.echo(f"  packageHash: {instance['package_hash'] or 'Not packaged'}")

    if instance['nft_token_id']:
        typer.echo(f"  NFT Token ID: {instance['nft_token_id']}")
        typer.echo(f"  NFT Contract: {instance['nft_contract']}")

    typer.echo("")
    typer.echo(f"Version History: {len(versions)} version(s)")
    for ver in versions:
        typer.echo(f"  v{ver['version']}: {ver['created_at'][:19]} (manifest: {ver['manifest_hash'][:16]}...)")



# ============================================================================
# PHASE 4: CHAIN COMMANDS
# ============================================================================

chain_app = typer.Typer(help="Local blockchain management")
app.add_typer(chain_app, name="chain")


@chain_app.command("up")
def chain_up():
    """Start local Anvil blockchain"""
    from uapk.nft.chain_manager import start_chain

    typer.echo("[UAPK CHAIN] Starting local Anvil blockchain...")

    result = start_chain()

    if result['success']:
        typer.secho(f"✓ {result['message']}", fg=typer.colors.GREEN)
        typer.echo(f"  RPC: {result.get('rpc', 'http://127.0.0.1:8545')}")
        typer.echo(f"  Chain ID: {result.get('chain_id', 31337)}")
    else:
        typer.secho(f"✗ {result['message']}", fg=typer.colors.RED)
        sys.exit(1)


@chain_app.command("down")
def chain_down():
    """Stop local Anvil blockchain"""
    from uapk.nft.chain_manager import stop_chain

    typer.echo("[UAPK CHAIN] Stopping local blockchain...")

    result = stop_chain()

    if result['success']:
        typer.secho(f"✓ {result['message']}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"✗ {result['message']}", fg=typer.colors.RED)
        sys.exit(1)


@chain_app.command("status")
def chain_status():
    """Check local chain status"""
    from uapk.nft.chain_manager import check_chain_status

    result = check_chain_status()

    if result['reachable']:
        typer.secho("✓ Chain is running", fg=typer.colors.GREEN)
        typer.echo(f"  RPC: {result['rpc']}")
        typer.echo(f"  Block: {result['block_number']}")
    else:
        typer.secho("✗ Chain is not reachable", fg=typer.colors.RED)
        if 'error' in result:
            typer.echo(f"  Error: {result['error']}")


# ============================================================================
# PHASE 4: NFT COMMANDS
# ============================================================================

nft_app = typer.Typer(help="NFT management commands")
app.add_typer(nft_app, name="nft")


@nft_app.command("deploy")
def nft_deploy(
    network: str = typer.Option("local", help="Network (local)")
):
    """Deploy BusinessInstanceNFT contract"""
    from uapk.nft.deployer import deploy_contract, get_deployed_contract

    typer.echo("[UAPK NFT] Deploying BusinessInstanceNFT contract...")

    # Check if already deployed
    existing = get_deployed_contract()
    if existing:
        typer.secho(f"⚠ Contract already deployed: {existing['contract_address']}", fg=typer.colors.YELLOW)
        return

    # Get chain config
    rpc_url = os.environ.get('UAPK_CHAIN_RPC', 'http://127.0.0.1:8545')
    private_key = os.environ.get('UAPK_CHAIN_PRIVATE_KEY')

    if not private_key:
        typer.secho("✗ UAPK_CHAIN_PRIVATE_KEY not set", fg=typer.colors.RED)
        typer.echo("  Set in .env or use Anvil default: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
        sys.exit(1)

    # Deploy
    result = deploy_contract(rpc_url, private_key)

    if result['success']:
        typer.secho("✓ Contract deployed successfully", fg=typer.colors.GREEN)
        typer.echo(f"  Address: {result['contract_address']}")
        typer.echo(f"  Deployer: {result['deployer']}")
        typer.echo(f"  Tx: {result['tx_hash']}")
    else:
        typer.secho(f"✗ {result['message']}", fg=typer.colors.RED)
        sys.exit(1)


# ============================================================================
# PHASE 4: HITL COMMANDS
# ============================================================================

hitl_app = typer.Typer(help="Human-in-the-loop approval queue")
app.add_typer(hitl_app, name="hitl")


@hitl_app.command("list")
def hitl_list():
    """List HITL approval requests"""
    from uapk.hitl.minimal import get_hitl_queue

    hitl = get_hitl_queue()
    requests = hitl.list_requests()
    hitl.close()

    if not requests:
        typer.echo("No HITL requests")
        return

    typer.echo(f"HITL Requests ({len(requests)} total):")
    typer.echo("")

    for req in requests:
        status_color = {
            'pending': typer.colors.YELLOW,
            'approved': typer.colors.GREEN,
            'rejected': typer.colors.RED
        }.get(req['status'], typer.colors.WHITE)

        typer.secho(f"  #{req['id']}: {req['action']}", fg=typer.colors.BRIGHT_WHITE, bold=True)
        typer.secho(f"    Status: {req['status']}", fg=status_color)
        typer.echo(f"    Created: {req['created_at'][:19]}")
        if req['approved_at']:
            typer.echo(f"    Approved: {req['approved_at'][:19]}")
        typer.echo("")


@hitl_app.command("approve")
def hitl_approve(
    request_id: int = typer.Argument(..., help="HITL request ID")
):
    """Approve HITL request and get override token"""
    from uapk.hitl.minimal import get_hitl_queue

    hitl = get_hitl_queue()

    try:
        override_token = hitl.approve_request(request_id)
        hitl.close()

        if override_token:
            typer.secho(f"✓ Request #{request_id} approved", fg=typer.colors.GREEN)
            typer.echo("")
            typer.echo("Override Token (valid for 5 minutes):")
            typer.echo(f"  {override_token}")
            typer.echo("")
            typer.echo("Use with --override-token flag on original command")
        else:
            typer.secho(f"✗ Request #{request_id} not found", fg=typer.colors.RED)
            sys.exit(1)

    except ValueError as e:
        typer.secho(f"✗ {str(e)}", fg=typer.colors.RED)
        hitl.close()
        sys.exit(1)




# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
