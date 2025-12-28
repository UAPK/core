"""Audit Export API endpoints - Immutable audit trail exports to S3 Object Lock."""

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import ApiKeyAuth, CurrentUser, DbSession
from app.services.audit_anchor import AuditAnchorError, AuditAnchorService

router = APIRouter(prefix="/audit-export", tags=["Audit Export"])


class ExportRecordsRequest(BaseModel):
    """Request to export audit records for a date range."""

    uapk_id: str = Field(..., description="UAPK manifest ID")
    start_date: date = Field(..., description="Start date (inclusive)")
    end_date: date = Field(..., description="End date (inclusive)")
    verify_chain: bool = Field(True, description="Verify hash chain before export")


class ExportRecordsResponse(BaseModel):
    """Response from batch export operation."""

    org_id: str
    uapk_id: str
    start_date: str
    end_date: str
    records_found: int
    records_exported: int
    records_failed: int
    chain_verified: bool
    exports: list[dict[str, Any]]
    failed: list[dict[str, Any]]
    exported_at: str


class CreateEvidenceBundleRequest(BaseModel):
    """Request to create a signed evidence bundle."""

    uapk_id: str = Field(..., description="UAPK manifest ID")
    start_date: date = Field(..., description="Start date (inclusive)")
    end_date: date = Field(..., description="End date (inclusive)")
    include_policy_config: bool = Field(True, description="Include policy configuration")
    include_manifest: bool = Field(True, description="Include UAPK manifest")


class EvidenceBundleResponse(BaseModel):
    """Response from evidence bundle creation."""

    bundle_type: str
    org_id: str
    uapk_id: str
    start_date: str
    end_date: str
    records_count: int
    chain_valid: bool
    s3_bucket: str
    s3_key: str
    s3_version_id: str | None
    bundle_size_bytes: int
    retention_until: str
    created_at: str


class ExportStatusResponse(BaseModel):
    """Status of audit export configuration."""

    enabled: bool
    s3_bucket: str | None
    s3_region: str
    object_lock_mode: str
    retention_days: int
    auto_export_enabled: bool


@router.get("/status", response_model=ExportStatusResponse)
async def get_export_status(
    user: CurrentUser,
    db: DbSession,
) -> ExportStatusResponse:
    """Get audit export configuration status.

    Returns the current export configuration including:
    - Whether export is enabled
    - S3 bucket and region
    - Object Lock settings
    - Auto-export status
    """
    from app.core.config import get_settings

    settings = get_settings()

    return ExportStatusResponse(
        enabled=settings.audit_export_enabled,
        s3_bucket=settings.audit_export_s3_bucket,
        s3_region=settings.audit_export_s3_region,
        object_lock_mode=settings.audit_export_object_lock_mode,
        retention_days=settings.audit_export_object_lock_retention_days,
        auto_export_enabled=settings.audit_export_auto_export_enabled,
    )


@router.post("/export-records", response_model=ExportRecordsResponse)
async def export_records(
    request: ExportRecordsRequest,
    user: CurrentUser,
    db: DbSession,
) -> ExportRecordsResponse:
    """Export audit records for a date range to S3 Object Lock.

    This endpoint:
    1. Queries interaction records for the specified UAPK and date range
    2. Verifies hash chain integrity (if requested)
    3. Exports each record to S3 with Object Lock retention
    4. Returns export metadata including S3 locations

    **Use Cases:**
    - Periodic compliance exports
    - Legal hold / eDiscovery requests
    - External audit preparation
    - Backup to immutable storage

    **Object Lock:**
    Records are stored with WORM (Write Once Read Many) protection.
    Default retention: 7 years (2555 days) in COMPLIANCE mode.
    """
    from app.core.config import get_settings

    settings = get_settings()

    if not settings.audit_export_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit export is not enabled. Set AUDIT_EXPORT_ENABLED=true and configure S3.",
        )

    anchor_service = AuditAnchorService(db)

    try:
        # Use the user's organization ID
        result = await anchor_service.export_records_batch(
            org_id=user.default_org_id,
            uapk_id=request.uapk_id,
            start_date=request.start_date,
            end_date=request.end_date,
            verify_chain=request.verify_chain,
        )

        return ExportRecordsResponse(**result)

    except AuditAnchorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        ) from e


@router.post("/create-evidence-bundle", response_model=EvidenceBundleResponse)
async def create_evidence_bundle(
    request: CreateEvidenceBundleRequest,
    user: CurrentUser,
    db: DbSession,
) -> EvidenceBundleResponse:
    """Create a signed evidence bundle for compliance/legal use.

    An evidence bundle is a tar.gz archive containing:
    - All interaction records (JSON)
    - Hash chain verification report
    - Gateway public key (for signature verification)
    - Bundle manifest (signed with Ed25519)
    - README with verification instructions

    **Use Cases:**
    - Legal proceedings (evidence submission)
    - Regulatory audits
    - Internal compliance reviews
    - Customer transparency reports

    **Bundle Structure:**
    ```
    evidence_bundle/
    ├── records/
    │   ├── int-abc123.json
    │   └── int-def456.json
    ├── verification_report.json
    ├── gateway_public_key.json
    ├── manifest.json
    ├── bundle_signature.txt
    └── README.md
    ```

    **Verification:**
    Recipients can verify:
    1. Bundle signature (Ed25519)
    2. Hash chain integrity
    3. Individual record signatures
    4. Record hash recomputation
    """
    from app.core.config import get_settings

    settings = get_settings()

    if not settings.audit_export_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit export is not enabled. Set AUDIT_EXPORT_ENABLED=true and configure S3.",
        )

    anchor_service = AuditAnchorService(db)

    try:
        result = await anchor_service.create_evidence_bundle(
            org_id=user.default_org_id,
            uapk_id=request.uapk_id,
            start_date=request.start_date,
            end_date=request.end_date,
            include_policy_config=request.include_policy_config,
            include_manifest=request.include_manifest,
        )

        return EvidenceBundleResponse(**result)

    except AuditAnchorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle creation failed: {str(e)}",
        ) from e


@router.get("/health")
async def export_health_check(db: DbSession) -> dict[str, str]:
    """Health check for audit export service.

    Verifies:
    - Export is enabled
    - S3 configuration is present
    - S3 bucket is accessible (if credentials provided)
    """
    from app.core.config import get_settings

    settings = get_settings()

    if not settings.audit_export_enabled:
        return {
            "status": "disabled",
            "message": "Audit export is not enabled",
        }

    if not settings.audit_export_s3_bucket:
        return {
            "status": "misconfigured",
            "message": "S3 bucket not configured",
        }

    # Try to create service to validate configuration
    try:
        anchor_service = AuditAnchorService(db)
        s3_client = anchor_service._get_s3_client()

        # Test bucket access
        s3_client.head_bucket(Bucket=settings.audit_export_s3_bucket)

        return {
            "status": "healthy",
            "message": "Audit export is configured and S3 bucket is accessible",
            "bucket": settings.audit_export_s3_bucket,
            "region": settings.audit_export_s3_region,
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"S3 connection failed: {str(e)}",
        }
