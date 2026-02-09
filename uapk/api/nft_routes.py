"""NFT minting endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uapk.api.auth import get_current_user
from uapk.api.main import get_manifest
from uapk.db.models import User
from uapk.policy import check_policy
from uapk.audit import get_audit_log
from uapk.cas import ContentAddressedStore
from uapk.nft.minter import mint_business_nft
from pathlib import Path
import json

router = APIRouter()

class MintNFTRequest(BaseModel):
    force: bool = False

@router.post("/mint")
async def mint_nft(request: MintNFTRequest, current_user: User = Depends(get_current_user)):
    """Mint NFT representing business instance"""
    manifest = get_manifest()

    # Check policy
    if manifest.executionMode == "dry_run" and not request.force:
        policy_result = check_policy(
            agent_id=None,
            action="mint_nft",
            user_id=current_user.id
        )

        if policy_result.decision != "ALLOW":
            raise HTTPException(
                status_code=403,
                detail=f"NFT minting requires approval in dry_run mode. Reasons: {', '.join(policy_result.reasons)}"
            )

    # Compute hashes
    plan_path = Path("runtime/plan.lock.json")
    if not plan_path.exists():
        raise HTTPException(status_code=400, detail="Plan not resolved. Run 'uapk verify' first.")

    plan_data = json.loads(plan_path.read_text())
    manifest_hash = plan_data.get("manifestHash", "")
    plan_hash = plan_data.get("planHash", "")

    # Compute merkle root
    audit_log = get_audit_log()
    merkle_root = audit_log.compute_merkle_root()

    # Create CAS bundle
    cas = ContentAddressedStore()

    # Store NFT metadata
    nft_metadata = {
        "name": f"{manifest.name} Business Instance",
        "description": manifest.description,
        "attributes": [
            {"trait_type": "Manifest Hash", "value": manifest_hash},
            {"trait_type": "Plan Hash", "value": plan_hash},
            {"trait_type": "Audit Merkle Root", "value": merkle_root},
            {"trait_type": "Execution Mode", "value": manifest.executionMode}
        ],
        "properties": {
            "uapkVersion": manifest.uapkVersion
        }
    }

    metadata_hash = cas.put_json(nft_metadata)

    # Mint NFT
    receipt = mint_business_nft(
        metadata_uri=cas.uri(metadata_hash),
        manifest_hash=manifest_hash,
        plan_hash=plan_hash,
        merkle_root=merkle_root
    )

    # Save receipt
    receipt_path = Path("runtime/nft_mint_receipt.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2))

    # Audit
    audit_log.append_event(
        event_type="nft",
        action="mint_business_instance",
        params=nft_metadata,
        result=receipt,
        user_id=current_user.id
    )

    return receipt
