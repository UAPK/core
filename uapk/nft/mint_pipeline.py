"""
NFT Minting Pipeline (Phase 4)
Complete workflow for minting business instance NFTs.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from uapk.cas import ContentAddressedStore
from uapk.platform.paths import get_platform_paths
from uapk.fleet.db import get_fleet_db
from uapk.nft.deployer import get_deployed_contract, CONTRACT_ABI
from uapk.audit import get_audit_log


def create_nft_metadata(instance_dir: Path) -> Dict[str, Any]:
    """
    Create NFT metadata for business instance.

    Args:
        instance_dir: Path to instance directory

    Returns:
        Metadata dict
    """
    # Load manifest
    manifest_path = instance_dir / 'manifest.jsonld'
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Load plan lock
    plan_lock_path = instance_dir / 'plan.lock.json'
    plan_hash = None
    if plan_lock_path.exists():
        with open(plan_lock_path, 'r') as f:
            plan = json.load(f)
            plan_hash = plan.get('planHash', '')

    # Load package info
    package_path = instance_dir / 'package.json'
    package_hash = None
    if package_path.exists():
        with open(package_path, 'r') as f:
            pkg = json.load(f)
            package_hash = pkg.get('packageHash', '')

    # Get audit merkle root (if instance has run)
    audit_merkle_root = None
    audit_path = instance_dir / 'audit.jsonl'
    if audit_path.exists():
        try:
            audit_log = get_audit_log(str(audit_path))
            audit_merkle_root = audit_log.compute_merkle_root()
        except:
            pass

    # Get instance ID
    instance_id = instance_dir.name

    # Get manifest hash from crypto header or compute
    manifest_hash = manifest.get('cryptoHeader', {}).get('manifestHash', '')

    # Create metadata
    metadata = {
        "name": f"UAPK Business Instance: {manifest.get('name', instance_id)}",
        "description": manifest.get('description', 'Autonomous business instance compiled via UAPK'),
        "image": "ipfs://placeholder",  # Future: actual image
        "attributes": [
            {"trait_type": "Instance ID", "value": instance_id},
            {"trait_type": "Manifest Hash", "value": manifest_hash},
            {"trait_type": "Plan Hash", "value": plan_hash or "not_resolved"},
            {"trait_type": "Package Hash", "value": package_hash or "not_packaged"},
            {"trait_type": "Audit Merkle Root", "value": audit_merkle_root or "no_audit"},
            {"trait_type": "Execution Mode", "value": manifest.get('executionMode', 'dry_run')},
            {"trait_type": "UAPK Version", "value": manifest.get('uapkVersion', '0.1')},
            {"trait_type": "Compiler Version", "value": "0.1.0"}
        ],
        "properties": {
            "manifestHash": manifest_hash,
            "planHash": plan_hash,
            "packageHash": package_hash,
            "auditMerkleRoot": audit_merkle_root,
            "instanceId": instance_id,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "compilerVersion": "0.1.0"
        }
    }

    return metadata


def mint_nft(
    instance_dir: Path,
    rpc_url: str,
    private_key: str,
    contract_address: str,
    require_approval: bool = True,
    override_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mint NFT for business instance.

    Args:
        instance_dir: Instance directory
        rpc_url: Chain RPC URL
        private_key: Private key for minting
        contract_address: NFT contract address
        require_approval: If True and no override_token, create HITL request
        override_token: Override token from HITL approval

    Returns:
        Mint result
    """
    instance_id = instance_dir.name

    # If require_approval and no override token, create HITL request
    if require_approval and not override_token:
        from uapk.hitl.minimal import get_hitl_queue

        hitl = get_hitl_queue()
        request_id = hitl.create_request(
            action="MINT_NFT",
            payload={"instance_id": instance_id, "instance_dir": str(instance_dir)}
        )
        hitl.close()

        return {
            "success": False,
            "requires_approval": True,
            "hitl_request_id": request_id,
            "message": f"Action requires approval. Approve with: uapk hitl approve {request_id}"
        }

    # TODO: Validate override token if provided

    # Create metadata and store in CAS
    metadata = create_nft_metadata(instance_dir)

    paths = get_platform_paths()
    cas = ContentAddressedStore(str(paths.cas_dir()))

    metadata_hash = cas.put_json(metadata)
    token_uri = f"cas://{metadata_hash}"

    # Mint NFT on chain
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            return {"success": False, "message": "Cannot connect to chain"}

        account = w3.eth.account.from_key(private_key)
        contract = w3.eth.contract(address=contract_address, abi=CONTRACT_ABI)

        # Build mint transaction
        tx = contract.functions.mint(
            account.address,
            token_uri,
            instance_id,
            metadata['properties']['manifestHash'],
            metadata['properties']['planHash'] or "",
            metadata['properties']['packageHash'] or "",
            metadata['properties']['auditMerkleRoot'] or "",
            metadata['properties']['compilerVersion']
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt['status'] == 1:
            # Parse token ID from logs
            token_id = contract.events.Transfer().process_receipt(receipt)[0]['args']['tokenId']

            # Save receipt
            receipt_data = {
                "token_id": token_id,
                "contract_address": contract_address,
                "token_uri": token_uri,
                "metadata_hash": metadata_hash,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt['blockNumber'],
                "minted_at": datetime.utcnow().isoformat() + "Z"
            }

            receipt_path = instance_dir / 'nft_mint_receipt.json'
            with open(receipt_path, 'w') as f:
                json.dump(receipt_data, f, indent=2)

            # Update fleet DB
            fleet_db = get_fleet_db()
            fleet_db.update_nft_info(instance_id, token_id, contract_address)
            fleet_db.close()

            return {
                "success": True,
                "token_id": token_id,
                "contract_address": contract_address,
                "token_uri": token_uri,
                "metadata_hash": metadata_hash,
                "tx_hash": tx_hash.hex()
            }

        return {"success": False, "message": "Transaction failed"}

    except ImportError:
        return {"success": False, "message": "web3 not installed. Run: pip install web3"}
    except Exception as e:
        return {"success": False, "message": f"Minting failed: {str(e)}"}


def verify_nft(instance_id: str) -> Dict[str, Any]:
    """
    Verify NFT matches local instance state.

    Args:
        instance_id: Instance ID

    Returns:
        Verification result
    """
    # Get instance from fleet
    fleet_db = get_fleet_db()
    instance = fleet_db.get_instance(instance_id)
    fleet_db.close()

    if not instance:
        return {"success": False, "message": f"Instance {instance_id} not found"}

    if not instance['nft_token_id']:
        return {"success": False, "message": "Instance has not been minted"}

    # Load NFT receipt
    paths = get_platform_paths()
    instance_dir = paths.instance_dir(instance_id)
    receipt_path = instance_dir / 'nft_mint_receipt.json'

    if not receipt_path.exists():
        return {"success": False, "message": "NFT receipt not found"}

    with open(receipt_path, 'r') as f:
        receipt = json.load(f)

    # Get contract info
    rpc_url = os.environ.get('UAPK_CHAIN_RPC', 'http://127.0.0.1:8545')

    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(rpc_url))
        contract = w3.eth.contract(address=receipt['contract_address'], abi=CONTRACT_ABI)

        # Fetch on-chain metadata
        token_id = receipt['token_id']
        on_chain_uri = contract.functions.tokenURI(token_id).call()
        on_chain_metadata = contract.functions.getBusinessMetadata(token_id).call()

        # Verify matches
        uri_match = on_chain_uri == receipt['token_uri']
        manifest_match = on_chain_metadata[0] == instance['manifest_hash']
        plan_match = on_chain_metadata[1] == (instance['plan_hash'] or "")
        instance_id_match = on_chain_metadata[4] == instance_id

        all_match = uri_match and manifest_match and plan_match and instance_id_match

        return {
            "success": True,
            "verified": all_match,
            "checks": {
                "token_uri": uri_match,
                "manifest_hash": manifest_match,
                "plan_hash": plan_match,
                "instance_id": instance_id_match
            },
            "on_chain": {
                "token_id": token_id,
                "token_uri": on_chain_uri,
                "manifest_hash": on_chain_metadata[0],
                "instance_id": on_chain_metadata[4]
            },
            "local": {
                "manifest_hash": instance['manifest_hash'],
                "plan_hash": instance['plan_hash'],
                "instance_id": instance_id
            }
        }

    except ImportError:
        return {"success": False, "message": "web3 not installed"}
    except Exception as e:
        return {"success": False, "message": f"Verification failed: {str(e)}"}
