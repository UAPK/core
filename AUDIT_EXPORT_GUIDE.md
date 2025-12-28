# Audit Export Guide - S3 Object Lock Integration

## Overview

The UAPK Gateway now supports **immutable audit trail exports** to S3 with Object Lock (WORM storage). This provides legally-defensible, tamper-proof audit records for compliance, legal proceedings, and regulatory requirements.

### Key Features

- ✅ **S3 Object Lock** - WORM (Write Once Read Many) protection
- ✅ **Hash Chain Verification** - Cryptographic integrity checks before export
- ✅ **Ed25519 Signatures** - All records digitally signed
- ✅ **Evidence Bundles** - Signed tar.gz archives for legal use
- ✅ **7-Year Retention** - Configurable retention periods (default: 7 years)
- ✅ **Compliance Mode** - Records cannot be deleted even by AWS root account
- ✅ **Batch & Real-time Export** - Flexible export strategies

---

## S3 Bucket Setup

### Prerequisites

1. AWS account (or S3-compatible storage: MinIO, Wasabi, Backblaze, etc.)
2. S3 bucket with Object Lock enabled
3. IAM user/role with appropriate permissions

### Step 1: Create S3 Bucket with Object Lock

**Using AWS Console:**
1. Go to S3 → Create bucket
2. **Bucket name**: `uapk-audit-{org-name}` (must be globally unique)
3. **Region**: Choose your preferred region
4. **Object Lock**: Enable ✅
5. **Versioning**: Enabled (required for Object Lock)
6. **Default retention**: Configure if desired (we set this programmatically)
7. Create bucket

**Using AWS CLI:**
```bash
aws s3api create-bucket \
  --bucket uapk-audit-yourcompany \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1 \
  --object-lock-enabled-for-bucket

# Enable versioning (required)
aws s3api put-bucket-versioning \
  --bucket uapk-audit-yourcompany \
  --versioning-configuration Status=Enabled

# Set default Object Lock configuration (optional)
aws s3api put-object-lock-configuration \
  --bucket uapk-audit-yourcompany \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 2555
      }
    }
  }'
```

**Using Terraform:**
```hcl
resource "aws_s3_bucket" "audit" {
  bucket = "uapk-audit-yourcompany"

  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 2555  # 7 years
    }
  }
}
```

### Step 2: Create IAM Policy

Create an IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AuditExportPermissions",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectRetention",
        "s3:PutObjectLegalHold",
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::uapk-audit-yourcompany",
        "arn:aws:s3:::uapk-audit-yourcompany/*"
      ]
    }
  ]
}
```

### Step 3: Create IAM User/Role

**Option A: IAM User (for self-hosted)**
```bash
# Create user
aws iam create-user --user-name uapk-audit-exporter

# Attach policy
aws iam attach-user-policy \
  --user-name uapk-audit-exporter \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/UAPKAuditExport

# Create access key
aws iam create-access-key --user-name uapk-audit-exporter
# Save the AccessKeyId and SecretAccessKey
```

**Option B: IAM Role (for EKS/EC2)**
```bash
# Create role with trust policy for your EKS/EC2
aws iam create-role \
  --role-name uapk-audit-exporter \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy \
  --role-name uapk-audit-exporter \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/UAPKAuditExport
```

---

## Gateway Configuration

### Environment Variables

Add these to your `.env` or deployment config:

```bash
# Enable audit export
AUDIT_EXPORT_ENABLED=true

# S3 Configuration
AUDIT_EXPORT_S3_BUCKET=uapk-audit-yourcompany
AUDIT_EXPORT_S3_REGION=us-east-1

# Optional: Custom endpoint (for MinIO, Wasabi, etc.)
# AUDIT_EXPORT_S3_ENDPOINT=https://s3.wasabisys.com

# AWS Credentials (if not using IAM role)
AUDIT_EXPORT_S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AUDIT_EXPORT_S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Object Lock Settings
AUDIT_EXPORT_OBJECT_LOCK_MODE=COMPLIANCE  # or GOVERNANCE
AUDIT_EXPORT_OBJECT_LOCK_RETENTION_DAYS=2555  # 7 years

# Auto-export (optional)
AUDIT_EXPORT_AUTO_EXPORT_ENABLED=false  # Enable real-time export
AUDIT_EXPORT_BATCH_INTERVAL_MINUTES=60  # Batch interval if not real-time
```

### Object Lock Modes

**COMPLIANCE Mode** (Recommended for regulatory compliance)
- Records **cannot be deleted** by anyone, including AWS root account
- Retention period **cannot be shortened**
- Meets SEC 17a-4, FINRA, HIPAA requirements
- Use for: Legal holds, regulatory archives

**GOVERNANCE Mode** (For operational flexibility)
- Can be deleted by users with `s3:BypassGovernanceRetention` permission
- Retention can be shortened with special permission
- Use for: Testing, non-regulatory use cases

---

## API Usage

### 1. Check Export Status

```bash
GET /api/v1/audit-export/status
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "enabled": true,
  "s3_bucket": "uapk-audit-yourcompany",
  "s3_region": "us-east-1",
  "object_lock_mode": "COMPLIANCE",
  "retention_days": 2555,
  "auto_export_enabled": false
}
```

### 2. Export Records for Date Range

```bash
POST /api/v1/audit-export/export-records
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "uapk_id": "refund-bot-v1",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "verify_chain": true
}
```

**Response:**
```json
{
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "uapk_id": "refund-bot-v1",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "records_found": 1523,
  "records_exported": 1523,
  "records_failed": 0,
  "chain_verified": true,
  "exports": [
    {
      "record_id": "int-abc123...",
      "s3_bucket": "uapk-audit-yourcompany",
      "s3_key": "550e8400.../refund-bot-v1/2025-01-15/int-abc123.json",
      "s3_version_id": "3/L4kqtJlcpXroDTDmpUMLUo",
      "retention_until": "2032-01-15T10:30:00Z",
      "object_lock_mode": "COMPLIANCE",
      "chain_verified": true,
      "exported_at": "2025-01-15T10:30:00Z"
    }
  ],
  "failed": [],
  "exported_at": "2025-01-15T10:30:00Z"
}
```

### 3. Create Evidence Bundle

```bash
POST /api/v1/audit-export/create-evidence-bundle
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "uapk_id": "refund-bot-v1",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "include_policy_config": true,
  "include_manifest": true
}
```

**Response:**
```json
{
  "bundle_type": "evidence",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "uapk_id": "refund-bot-v1",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "records_count": 1523,
  "chain_valid": true,
  "s3_bucket": "uapk-audit-yourcompany",
  "s3_key": "550e8400.../refund-bot-v1/evidence_bundles/evidence_550e8400_refund-bot-v1_2025-01-01_2025-01-31.tar.gz",
  "s3_version_id": "3/L4kqtJlcpXroDTDmpUMLUo",
  "bundle_size_bytes": 4523890,
  "retention_until": "2032-01-15T10:30:00Z",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### 4. Health Check

```bash
GET /api/v1/audit-export/health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "Audit export is configured and S3 bucket is accessible",
  "bucket": "uapk-audit-yourcompany",
  "region": "us-east-1"
}
```

---

## Evidence Bundle Structure

When you create an evidence bundle, you get a signed tar.gz archive:

```
evidence_bundle/
├── records/
│   ├── int-abc123.json          # Individual interaction records
│   ├── int-def456.json
│   └── ...
├── verification_report.json     # Hash chain verification report
├── gateway_public_key.json      # Ed25519 public key for verification
├── manifest.json                # Bundle manifest
├── bundle_signature.txt         # Ed25519 signature of manifest
└── README.md                    # Verification instructions
```

### Verification Process

1. **Verify Bundle Signature**
```python
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519

# Load gateway public key
with open('gateway_public_key.json') as f:
    key_data = json.load(f)
    public_key_bytes = base64.b64decode(key_data['public_key_base64'])
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

# Load manifest and signature
with open('manifest.json') as f:
    manifest = f.read()

with open('bundle_signature.txt') as f:
    signature_hex = f.read().split('\n')[1]  # Second line
    signature = bytes.fromhex(signature_hex)

# Verify
public_key.verify(signature, manifest.encode())
print("✅ Bundle signature valid!")
```

2. **Verify Hash Chain**
```python
# Check that each record's previous_record_hash matches previous record's record_hash
records = sorted(records, key=lambda r: r['created_at'])
for i in range(1, len(records)):
    assert records[i]['previous_record_hash'] == records[i-1]['record_hash']
print("✅ Hash chain valid!")
```

3. **Verify Individual Record Signatures**
```python
# Each record has a gateway_signature field
for record in records:
    signature = bytes.fromhex(record['gateway_signature'])
    hash_bytes = record['record_hash'].encode('utf-8')
    public_key.verify(signature, hash_bytes)
print("✅ All record signatures valid!")
```

---

## S3 Object Structure

### Hierarchical Key Structure

```
{org_id}/
└── {uapk_id}/
    ├── 2025-01-15/
    │   ├── int-abc123.json
    │   ├── int-def456.json
    │   └── int-ghi789.json
    ├── 2025-01-16/
    │   └── ...
    └── evidence_bundles/
        ├── evidence_550e8400_refund-bot-v1_2025-01-01_2025-01-31.tar.gz
        └── evidence_550e8400_refund-bot-v1_2025-02-01_2025-02-28.tar.gz
```

### Object Metadata

Each exported record includes metadata tags:

```json
{
  "Metadata": {
    "record-id": "int-abc123",
    "org-id": "550e8400-e29b-41d4-a716-446655440000",
    "uapk-id": "refund-bot-v1",
    "record-hash": "sha256:abc123...",
    "gateway-signature": "ed25519:def456...",
    "chain-verified": "true",
    "export-version": "1.0"
  },
  "Tags": {
    "record_type": "interaction",
    "org_id": "550e8400-e29b-41d4-a716-446655440000",
    "uapk_id": "refund-bot-v1"
  },
  "ObjectLockMode": "COMPLIANCE",
  "ObjectLockRetainUntilDate": "2032-01-15T00:00:00Z"
}
```

---

## Use Cases

### 1. Monthly Compliance Export

```bash
# Export last month's records
curl -X POST https://gateway.yourcompany.com/api/v1/audit-export/export-records \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "refund-bot-v1",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "verify_chain": true
  }'
```

### 2. Legal Hold / eDiscovery

```bash
# Create evidence bundle for litigation
curl -X POST https://gateway.yourcompany.com/api/v1/audit-export/create-evidence-bundle \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "refund-bot-v1",
    "start_date": "2024-06-01",
    "end_date": "2024-12-31",
    "include_policy_config": true,
    "include_manifest": true
  }'

# Download from S3
aws s3 cp s3://uapk-audit-yourcompany/{s3_key} ./evidence.tar.gz
```

### 3. Regulatory Audit

```bash
# Export all records for a UAPK
for month in {01..12}; do
  curl -X POST https://gateway.yourcompany.com/api/v1/audit-export/create-evidence-bundle \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"uapk_id\": \"trading-bot-v1\",
      \"start_date\": \"2024-$month-01\",
      \"end_date\": \"2024-$month-31\"
    }"
done
```

### 4. Disaster Recovery Verification

```bash
# Verify all exported records
aws s3 ls s3://uapk-audit-yourcompany/{org_id}/{uapk_id}/ --recursive > exported_files.txt

# Verify Object Lock is active
aws s3api head-object \
  --bucket uapk-audit-yourcompany \
  --key {org_id}/{uapk_id}/2025-01-15/int-abc123.json \
  --query '{Mode:ObjectLockMode,RetainUntil:ObjectLockRetainUntilDate}'
```

---

## Compliance Frameworks

### SEC 17a-4(f) - Financial Records

✅ **Records stored in WORM format**
✅ **Retention period enforced (7 years)**
✅ **Audit trail of all access**
✅ **Hash verification for integrity**

### FINRA 4511 - Books and Records

✅ **Immutable storage**
✅ **Readily accessible for 6 years**
✅ **Tamper-evident design**

### HIPAA - Healthcare Records

✅ **Encryption in transit and at rest**
✅ **Access controls (IAM)**
✅ **Audit trail of PHI access**
✅ **6-year retention**

### GDPR - Right to Erasure

⚠️ **Note**: COMPLIANCE mode prevents deletion. For GDPR compliance:
- Use GOVERNANCE mode if you need "right to erasure"
- Or maintain a separate deletion log
- Or use pseudonymization before export

---

## Troubleshooting

### Error: "S3 bucket not configured"

**Solution**: Set `AUDIT_EXPORT_S3_BUCKET` environment variable.

### Error: "The bucket does not have Object Lock enabled"

**Solution**: Recreate bucket with Object Lock, or:
```bash
# Cannot enable Object Lock on existing bucket
# Must create new bucket
aws s3api create-bucket --bucket new-bucket --object-lock-enabled-for-bucket
# Migrate data from old bucket to new bucket
```

### Error: "Access Denied" when uploading

**Solution**: Check IAM permissions, especially:
- `s3:PutObject`
- `s3:PutObjectRetention`
- `s3:PutObjectLegalHold`

### Error: "Hash chain verification failed"

**Possible causes:**
1. Database corruption
2. Records queried out of order
3. Missing records in database

**Solution**: Query records ordered by `created_at`, investigate missing records.

---

## Cost Estimation

### S3 Storage Costs

**Assumptions:**
- 1,000 actions/day
- ~10KB per record
- 7-year retention
- US East (N. Virginia) pricing

**Monthly Costs:**
```
Daily data: 1,000 records × 10KB = 10MB
Monthly data: 10MB × 30 = 300MB
Yearly data: 300MB × 12 = 3.6GB
7-year storage: 3.6GB × 7 = 25.2GB

S3 Standard storage: 25.2GB × $0.023/GB = $0.58/month
Requests (PUT): 30,000/month × $0.005/1000 = $0.15/month
Requests (GET): Varies

Total: ~$0.73/month for 1,000 actions/day
```

**At scale (100,000 actions/day):**
- 7-year storage: ~2.5TB
- Monthly cost: ~$73/month

**Evidence bundles add:**
- Tar.gz compression: ~60% size reduction
- Negligible additional cost (created on-demand)

---

## Security Best Practices

1. **Use IAM Roles** instead of access keys when possible (EC2/EKS)
2. **Enable MFA Delete** on the S3 bucket
3. **Enable S3 Access Logging** for audit trail
4. **Use VPC Endpoints** for S3 access (avoid public internet)
5. **Rotate access keys** every 90 days (if using keys)
6. **Enable CloudTrail** for AWS API audit trail
7. **Set bucket policy** to deny non-HTTPS access
8. **Enable S3 Block Public Access**

---

## Next Steps

- [ ] Configure S3 bucket with Object Lock
- [ ] Set environment variables
- [ ] Test export with `/audit-export/health`
- [ ] Export test records
- [ ] Create evidence bundle
- [ ] Verify bundle signature
- [ ] Document in runbook
- [ ] Train operations team
- [ ] Set up monitoring/alerting

---

## Support

For questions or issues:
- Check logs: `journalctl -u uapk-gateway -f`
- Health check: `GET /api/v1/audit-export/health`
- S3 bucket policy: `aws s3api get-bucket-policy --bucket {bucket}`
- Object Lock status: `aws s3api get-object-lock-configuration --bucket {bucket}`
