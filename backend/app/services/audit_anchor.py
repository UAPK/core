"""Audit Anchor Service - Export audit records to immutable storage (S3 Object Lock).

This service provides legally-defensible, tamper-proof audit trails by:
1. Verifying hash chain integrity before export
2. Exporting to S3 with Object Lock (WORM - Write Once Read Many)
3. Creating signed evidence bundles for compliance
4. Supporting both real-time and batch exports
"""

import json
import tarfile
import tempfile
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import canonicalize_json, verify_hash_chain
from app.core.config import get_settings
from app.core.ed25519 import get_gateway_key_manager
from app.core.logging import get_logger
from app.models.interaction_record import InteractionRecord

logger = get_logger("services.audit_anchor")


class AuditAnchorError(Exception):
    """Raised when audit anchor operations fail."""

    pass


class AuditAnchorService:
    """Service for exporting audit records to immutable S3 Object Lock storage."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self._s3_client = None

        if not self.settings.audit_export_enabled:
            logger.info("audit_export_disabled", message="Audit export is disabled in settings")

    def _get_s3_client(self):
        """Get or create S3 client with proper configuration."""
        if self._s3_client is None:
            if not self.settings.audit_export_s3_bucket:
                raise AuditAnchorError("S3 bucket not configured (AUDIT_EXPORT_S3_BUCKET)")

            config = Config(
                region_name=self.settings.audit_export_s3_region,
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )

            kwargs = {
                "config": config,
            }

            # Use custom endpoint if provided (e.g., MinIO, Wasabi, Backblaze)
            if self.settings.audit_export_s3_endpoint:
                kwargs["endpoint_url"] = self.settings.audit_export_s3_endpoint

            # Use explicit credentials if provided
            if self.settings.audit_export_s3_access_key and self.settings.audit_export_s3_secret_key:
                kwargs["aws_access_key_id"] = self.settings.audit_export_s3_access_key
                kwargs["aws_secret_access_key"] = self.settings.audit_export_s3_secret_key

            self._s3_client = boto3.client("s3", **kwargs)

        return self._s3_client

    def _build_s3_key(
        self,
        org_id: UUID,
        uapk_id: str,
        record_id: str,
        timestamp: datetime,
    ) -> str:
        """Build S3 object key with hierarchical structure for efficient querying.

        Format: {org_id}/{uapk_id}/{date}/{record_id}.json
        Example: 550e8400-e29b-41d4-a716-446655440000/refund-bot/2025-01-15/int-abc123.json
        """
        date_str = timestamp.strftime("%Y-%m-%d")
        return f"{org_id}/{uapk_id}/{date_str}/{record_id}.json"

    async def export_single_record(
        self,
        record: InteractionRecord,
        verify_chain: bool = True,
    ) -> dict[str, Any]:
        """Export a single interaction record to S3 with Object Lock.

        Args:
            record: The interaction record to export
            verify_chain: Whether to verify hash chain integrity before export

        Returns:
            Export metadata including S3 location and verification status

        Raises:
            AuditAnchorError: If export fails or hash chain is invalid
        """
        if not self.settings.audit_export_enabled:
            raise AuditAnchorError("Audit export is disabled")

        logger.info(
            "exporting_single_record",
            record_id=record.record_id,
            org_id=str(record.org_id),
            uapk_id=record.uapk_id,
        )

        # Verify hash chain if requested
        if verify_chain:
            # Get previous record to verify chain
            if record.previous_record_hash:
                result = await self.db.execute(
                    select(InteractionRecord)
                    .where(
                        InteractionRecord.org_id == record.org_id,
                        InteractionRecord.uapk_id == record.uapk_id,
                        InteractionRecord.record_hash == record.previous_record_hash,
                    )
                    .limit(1)
                )
                previous_record = result.scalar_one_or_none()

                if not previous_record:
                    logger.warning(
                        "hash_chain_broken",
                        record_id=record.record_id,
                        previous_hash=record.previous_record_hash[:16] + "...",
                        message="Previous record not found in database",
                    )
                    raise AuditAnchorError(
                        f"Hash chain broken: previous record {record.previous_record_hash[:16]}... not found"
                    )

            # Verify the record's own hash
            if not verify_hash_chain([record]):
                raise AuditAnchorError(f"Record {record.record_id} failed hash verification")

        # Build export payload
        export_payload = {
            "record_id": record.record_id,
            "org_id": str(record.org_id),
            "uapk_id": record.uapk_id,
            "agent_id": record.agent_id,
            "action_type": record.action_type,
            "tool": record.tool,
            "request": record.request,
            "request_hash": record.request_hash,
            "decision": record.decision.value,
            "decision_reason": record.decision_reason,
            "reasons_json": record.reasons_json,
            "policy_trace_json": record.policy_trace_json,
            "risk_snapshot_json": record.risk_snapshot_json,
            "result": record.result,
            "result_hash": record.result_hash,
            "duration_ms": record.duration_ms,
            "previous_record_hash": record.previous_record_hash,
            "record_hash": record.record_hash,
            "gateway_signature": record.gateway_signature,
            "created_at": record.created_at.isoformat(),
            "exported_at": datetime.now(UTC).isoformat(),
            "export_version": "1.0",
        }

        # Add gateway public key for signature verification
        key_manager = get_gateway_key_manager()
        export_payload["gateway_public_key"] = key_manager.public_key_base64

        # Canonicalize JSON for consistency
        canonical_json = canonicalize_json(export_payload)
        content = json.dumps(json.loads(canonical_json), indent=2).encode("utf-8")

        # Build S3 key
        s3_key = self._build_s3_key(
            record.org_id,
            record.uapk_id,
            record.record_id,
            record.created_at,
        )

        # Upload to S3 with Object Lock
        s3_client = self._get_s3_client()
        bucket = self.settings.audit_export_s3_bucket

        try:
            # Calculate retention date
            retention_until = datetime.now(UTC) + timedelta(
                days=self.settings.audit_export_object_lock_retention_days
            )

            # Put object with Object Lock retention
            response = s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=content,
                ContentType="application/json",
                ObjectLockMode=self.settings.audit_export_object_lock_mode,
                ObjectLockRetainUntilDate=retention_until,
                Metadata={
                    "record-id": record.record_id,
                    "org-id": str(record.org_id),
                    "uapk-id": record.uapk_id,
                    "record-hash": record.record_hash,
                    "gateway-signature": record.gateway_signature[:32],  # First 32 chars
                    "chain-verified": "true" if verify_chain else "false",
                    "export-version": "1.0",
                },
                Tagging=f"record_type=interaction&org_id={record.org_id}&uapk_id={record.uapk_id}",
            )

            logger.info(
                "record_exported_to_s3",
                record_id=record.record_id,
                s3_key=s3_key,
                version_id=response.get("VersionId"),
                etag=response.get("ETag"),
            )

            return {
                "record_id": record.record_id,
                "s3_bucket": bucket,
                "s3_key": s3_key,
                "s3_version_id": response.get("VersionId"),
                "s3_etag": response.get("ETag"),
                "retention_until": retention_until.isoformat(),
                "object_lock_mode": self.settings.audit_export_object_lock_mode,
                "chain_verified": verify_chain,
                "exported_at": datetime.now(UTC).isoformat(),
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                "s3_export_failed",
                record_id=record.record_id,
                error_code=error_code,
                error_message=error_message,
            )
            raise AuditAnchorError(f"S3 export failed: {error_code} - {error_message}") from e

    async def export_records_batch(
        self,
        org_id: UUID,
        uapk_id: str,
        start_date: date,
        end_date: date,
        verify_chain: bool = True,
    ) -> dict[str, Any]:
        """Export a batch of records for a date range.

        Args:
            org_id: Organization ID
            uapk_id: UAPK manifest ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            verify_chain: Whether to verify hash chain

        Returns:
            Batch export metadata including count and S3 locations
        """
        logger.info(
            "exporting_records_batch",
            org_id=str(org_id),
            uapk_id=uapk_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        # Query records in date range
        start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

        result = await self.db.execute(
            select(InteractionRecord)
            .where(
                InteractionRecord.org_id == org_id,
                InteractionRecord.uapk_id == uapk_id,
                InteractionRecord.created_at >= start_datetime,
                InteractionRecord.created_at <= end_datetime,
            )
            .order_by(InteractionRecord.created_at)
        )
        records = result.scalars().all()

        if not records:
            logger.warning(
                "no_records_found",
                org_id=str(org_id),
                uapk_id=uapk_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return {
                "org_id": str(org_id),
                "uapk_id": uapk_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "records_found": 0,
                "records_exported": 0,
                "exports": [],
            }

        # Verify hash chain if requested
        if verify_chain:
            if not verify_hash_chain(records):
                raise AuditAnchorError("Hash chain verification failed for record batch")

        # Export each record
        exports = []
        failed = []

        for record in records:
            try:
                export_result = await self.export_single_record(record, verify_chain=False)
                exports.append(export_result)
            except Exception as e:
                logger.error(
                    "record_export_failed",
                    record_id=record.record_id,
                    error=str(e),
                )
                failed.append({"record_id": record.record_id, "error": str(e)})

        logger.info(
            "batch_export_complete",
            org_id=str(org_id),
            uapk_id=uapk_id,
            records_found=len(records),
            records_exported=len(exports),
            records_failed=len(failed),
        )

        return {
            "org_id": str(org_id),
            "uapk_id": uapk_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "records_found": len(records),
            "records_exported": len(exports),
            "records_failed": len(failed),
            "chain_verified": verify_chain,
            "exports": exports,
            "failed": failed,
            "exported_at": datetime.now(UTC).isoformat(),
        }

    async def create_evidence_bundle(
        self,
        org_id: UUID,
        uapk_id: str,
        start_date: date,
        end_date: date,
        include_policy_config: bool = True,
        include_manifest: bool = True,
    ) -> dict[str, Any]:
        """Create a signed evidence bundle (tar.gz) for compliance/legal use.

        The bundle includes:
        - All interaction records (JSON)
        - Hash chain verification report
        - Gateway public key
        - Policy configuration (optional)
        - UAPK manifest (optional)
        - Bundle signature

        Args:
            org_id: Organization ID
            uapk_id: UAPK manifest ID
            start_date: Start date
            end_date: End date
            include_policy_config: Include policy configuration
            include_manifest: Include UAPK manifest

        Returns:
            Evidence bundle metadata including S3 location
        """
        logger.info(
            "creating_evidence_bundle",
            org_id=str(org_id),
            uapk_id=uapk_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        # Query records
        start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

        result = await self.db.execute(
            select(InteractionRecord)
            .where(
                InteractionRecord.org_id == org_id,
                InteractionRecord.uapk_id == uapk_id,
                InteractionRecord.created_at >= start_datetime,
                InteractionRecord.created_at <= end_datetime,
            )
            .order_by(InteractionRecord.created_at)
        )
        records = result.scalars().all()

        if not records:
            raise AuditAnchorError("No records found for evidence bundle")

        # Verify hash chain
        chain_valid = verify_hash_chain(records)

        # Create temporary directory for bundle
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "evidence_bundle"
            bundle_dir.mkdir()

            # 1. Export records
            records_dir = bundle_dir / "records"
            records_dir.mkdir()

            for record in records:
                record_data = {
                    "record_id": record.record_id,
                    "org_id": str(record.org_id),
                    "uapk_id": record.uapk_id,
                    "agent_id": record.agent_id,
                    "action_type": record.action_type,
                    "tool": record.tool,
                    "request": record.request,
                    "request_hash": record.request_hash,
                    "decision": record.decision.value,
                    "decision_reason": record.decision_reason,
                    "reasons_json": record.reasons_json,
                    "policy_trace_json": record.policy_trace_json,
                    "risk_snapshot_json": record.risk_snapshot_json,
                    "result": record.result,
                    "result_hash": record.result_hash,
                    "duration_ms": record.duration_ms,
                    "previous_record_hash": record.previous_record_hash,
                    "record_hash": record.record_hash,
                    "gateway_signature": record.gateway_signature,
                    "created_at": record.created_at.isoformat(),
                }

                record_file = records_dir / f"{record.record_id}.json"
                record_file.write_text(json.dumps(record_data, indent=2))

            # 2. Hash chain verification report
            verification_report = {
                "org_id": str(org_id),
                "uapk_id": uapk_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "records_count": len(records),
                "chain_valid": chain_valid,
                "first_record": records[0].record_id,
                "last_record": records[-1].record_id,
                "first_record_hash": records[0].record_hash,
                "last_record_hash": records[-1].record_hash,
                "verified_at": datetime.now(UTC).isoformat(),
            }

            (bundle_dir / "verification_report.json").write_text(
                json.dumps(verification_report, indent=2)
            )

            # 3. Gateway public key
            key_manager = get_gateway_key_manager()
            gateway_key_info = {
                "public_key_base64": key_manager.public_key_base64,
                "algorithm": "Ed25519",
                "purpose": "Audit record signature verification",
            }

            (bundle_dir / "gateway_public_key.json").write_text(
                json.dumps(gateway_key_info, indent=2)
            )

            # 4. README
            readme_content = f"""# UAPK Gateway Evidence Bundle

## Overview
This evidence bundle contains tamper-evident audit records from the UAPK Gateway.

## Contents
- `records/` - Individual interaction records (JSON)
- `verification_report.json` - Hash chain verification report
- `gateway_public_key.json` - Gateway's Ed25519 public key for signature verification
- `bundle_signature.txt` - Ed25519 signature of bundle manifest
- `README.md` - This file

## Details
- Organization ID: {org_id}
- UAPK ID: {uapk_id}
- Date Range: {start_date} to {end_date}
- Records Count: {len(records)}
- Hash Chain Valid: {chain_valid}
- Bundle Created: {datetime.now(UTC).isoformat()}

## Verification
1. Verify bundle signature using gateway_public_key.json
2. Verify each record's gateway_signature field
3. Verify hash chain: each record's previous_record_hash matches the previous record's record_hash
4. Verify record hashes by recomputing from canonical JSON

## Legal Notice
This evidence bundle is generated by UAPK Gateway for compliance and legal purposes.
All records are cryptographically signed and hash-chained to prevent tampering.
"""

            (bundle_dir / "README.md").write_text(readme_content)

            # 5. Create bundle manifest and sign it
            manifest = {
                "bundle_type": "uapk_evidence_bundle",
                "bundle_version": "1.0",
                "org_id": str(org_id),
                "uapk_id": uapk_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "records_count": len(records),
                "chain_valid": chain_valid,
                "created_at": datetime.now(UTC).isoformat(),
                "files": [
                    "records/",
                    "verification_report.json",
                    "gateway_public_key.json",
                    "README.md",
                ],
            }

            manifest_json = canonicalize_json(manifest)
            manifest_bytes = manifest_json.encode("utf-8")

            # Sign the manifest
            signature = key_manager.sign(manifest_bytes)
            signature_b64 = signature.hex()

            (bundle_dir / "bundle_signature.txt").write_text(
                f"Manifest Signature (Ed25519, hex):\n{signature_b64}\n\n"
                f"To verify:\n"
                f"1. Canonicalize manifest.json\n"
                f"2. Verify signature using gateway_public_key.json\n"
            )

            (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

            # 6. Create tar.gz
            bundle_filename = f"evidence_{org_id}_{uapk_id}_{start_date}_{end_date}.tar.gz"
            bundle_path = Path(tmpdir) / bundle_filename

            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(bundle_dir, arcname="evidence_bundle")

            # 7. Upload to S3
            s3_key = f"{org_id}/{uapk_id}/evidence_bundles/{bundle_filename}"
            s3_client = self._get_s3_client()

            with open(bundle_path, "rb") as f:
                bundle_content = f.read()

            retention_until = datetime.now(UTC) + timedelta(
                days=self.settings.audit_export_object_lock_retention_days
            )

            response = s3_client.put_object(
                Bucket=self.settings.audit_export_s3_bucket,
                Key=s3_key,
                Body=bundle_content,
                ContentType="application/gzip",
                ObjectLockMode=self.settings.audit_export_object_lock_mode,
                ObjectLockRetainUntilDate=retention_until,
                Metadata={
                    "bundle-type": "evidence",
                    "org-id": str(org_id),
                    "uapk-id": uapk_id,
                    "records-count": str(len(records)),
                    "chain-valid": str(chain_valid).lower(),
                    "start-date": start_date.isoformat(),
                    "end-date": end_date.isoformat(),
                },
            )

            logger.info(
                "evidence_bundle_created",
                org_id=str(org_id),
                uapk_id=uapk_id,
                s3_key=s3_key,
                records_count=len(records),
                bundle_size_bytes=len(bundle_content),
            )

            return {
                "bundle_type": "evidence",
                "org_id": str(org_id),
                "uapk_id": uapk_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "records_count": len(records),
                "chain_valid": chain_valid,
                "s3_bucket": self.settings.audit_export_s3_bucket,
                "s3_key": s3_key,
                "s3_version_id": response.get("VersionId"),
                "bundle_size_bytes": len(bundle_content),
                "retention_until": retention_until.isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
