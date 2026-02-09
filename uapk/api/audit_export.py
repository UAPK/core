"""
Audit Export API Endpoint (M2.5)
Provides HTTP endpoint for evidence-grade audit exports.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path

from uapk.api.auth import get_current_user
from uapk.api.rbac import require_role
from uapk.db.models import User
from uapk.audit_export import create_audit_bundle


router = APIRouter()


@router.post("/export")
@require_role("Owner", "Admin")  # M1.4: Only owners/admins can export audit logs
async def export_audit(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """
    Export evidence-grade audit bundle.

    Creates a tar.gz bundle containing:
    - audit.jsonl: Filtered audit events
    - manifest.json: Manifest snapshot
    - verification_proof.json: Chain validation, signatures, merkle root

    Requires Owner or Admin role.
    """
    # Create bundle
    bundle_path = create_audit_bundle(
        start_date=start_date,
        end_date=end_date
    )

    # Return as downloadable file
    return FileResponse(
        path=bundle_path,
        media_type="application/gzip",
        filename=bundle_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{bundle_path.name}"'
        }
    )
