# P0 Security Fixes - Deployment Guide

## ✅ Fixes Applied

This document outlines the critical P0 security fixes that have been applied to the UAPK Gateway codebase, making it **pilot-ready**.

### Security Fixes

1. **Override Token Validation & Binding** - Prevents token reuse for different actions
2. **One-Time-Use Enforcement** - Atomic consumption prevents replay attacks
3. **Action Hash Validation** - Ensures tokens match approved actions exactly
4. **Agent Identity Binding** - Prevents cross-agent token reuse
5. **SSRF Protection** - WebhookConnector validates domains and blocks private IPs
6. **Deterministic Hashing** - Consistent action hashing across all components

### Runtime Fixes

7. **default_org_id Property** - Prevents AttributeError crashes in UI/API routes
8. **Eager Loading** - AuthService loads memberships to prevent lazy-load errors
9. **Centralized Action Hashing** - Single source of truth for action hash computation

---

## 🚀 Deployment Steps

### Step 1: Backup Database

Before applying migrations, **always backup your database**:

```bash
# For PostgreSQL
pg_dump -h localhost -U postgres -d uapk_gateway > backup_$(date +%Y%m%d_%H%M%S).sql

# Or using Docker
docker exec uapk-postgres pg_dump -U postgres uapk_gateway > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Stop Running Services

```bash
# Stop the backend service
docker-compose stop backend

# Or if running locally
pkill -f "uvicorn app.main:app"
```

### Step 3: Run Database Migration

The migration adds two columns to the `approvals` table for tracking override token consumption:
- `consumed_at` - Timestamp when approval was consumed
- `consumed_interaction_id` - Which interaction consumed the approval

```bash
# Using Docker Compose
docker-compose run --rm migrate

# Or using Alembic directly
cd backend
alembic upgrade head

# Or using make (if available)
make migrate
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade 0007 -> 0008, Add one-time override token consumption tracking
```

### Step 4: Verify Migration

Check the database schema:

```bash
# Connect to database
docker exec -it uapk-postgres psql -U postgres -d uapk_gateway

# Verify new columns exist
\d approvals

# Expected output should include:
# consumed_at              | timestamp with time zone |
# consumed_interaction_id  | character varying(64)    |
```

### Step 5: Restart Services

```bash
# Using Docker Compose
docker-compose up -d

# Or locally
cd backend
uvicorn app.main:app --reload
```

### Step 6: Run Integration Tests

```bash
# Run the P0 fixes integration test suite
pytest backend/tests/test_p0_fixes_integration.py -v

# Expected output: 8 tests passing
# ✓ P0-1: default_org_id property works without crashes
# ✓ P0-2: Action hash is deterministic
# ✓ P0-3: Override token validates for matching action
# ✓ P0-4: Override token rejects different action (prevents token reuse)
# ✓ P0-5: First override token consumption succeeds
# ✓ P0-6: Override token replay attack prevented (one-time-use)
# ✓ P0-7: Expired approval correctly rejected
# ✓ P0-8: Override token identity binding enforced
```

---

## 🧪 Pilot Customer Validation

### Pre-Flight Checklist

Before demonstrating to a pilot customer:

- [ ] Database migration 0008 applied successfully
- [ ] All 8 P0 integration tests passing
- [ ] Gateway service starts without errors
- [ ] Health check endpoint returns 200: `GET /health`
- [ ] Can create a manifest: `POST /api/v1/manifests`
- [ ] Can create an approval: Trigger an ESCALATE decision
- [ ] Can generate override token: `POST /api/v1/approvals/{id}/approve`
- [ ] Override token works: `POST /api/v1/gateway/execute` with override token
- [ ] Replay protection works: Second use of same override token is DENIED

### Quick Smoke Test

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Login (get JWT)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme123"}'

# 3. Create manifest
curl -X POST http://localhost:8000/api/v1/manifests \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d @examples/manifests/legal-ip-enforcement.json

# 4. Test gateway evaluate (dry-run)
curl -X POST http://localhost:8000/api/v1/gateway/evaluate \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "legal-ip-enforcement",
    "agent_id": "instance-1",
    "action": {
      "type": "send_email",
      "tool": "smtp",
      "params": {"to": "target@example.com"}
    }
  }'
```

---

## 🔒 Security Validation

### Test Override Token Security

```python
# Test script: validate_override_token_security.py
import requests
import json

BASE_URL = "http://localhost:8000"
JWT = "your-jwt-token"  # Get from /api/v1/auth/login

# 1. Create action that triggers ESCALATE
response = requests.post(
    f"{BASE_URL}/api/v1/gateway/evaluate",
    headers={"Authorization": f"Bearer {JWT}"},
    json={
        "uapk_id": "test-agent",
        "agent_id": "instance-1",
        "action": {
            "type": "wire_transfer",
            "tool": "bank_api",
            "params": {"amount": 100000, "currency": "USD"}  # Exceeds cap
        }
    }
)

assert response.json()["decision"] == "escalate"
approval_id = response.json()["approval_id"]

# 2. Approve and get override token
response = requests.post(
    f"{BASE_URL}/api/v1/approvals/{approval_id}/approve",
    headers={"Authorization": f"Bearer {JWT}"},
    json={"notes": "Approved by CFO"}
)

override_token = response.json()["override_token"]

# 3. Execute with override token (should succeed)
response = requests.post(
    f"{BASE_URL}/api/v1/gateway/execute",
    headers={"Authorization": f"Bearer {JWT}"},
    json={
        "uapk_id": "test-agent",
        "agent_id": "instance-1",
        "capability_token": override_token,  # Use override token
        "action": {
            "type": "wire_transfer",
            "tool": "bank_api",
            "params": {"amount": 100000, "currency": "USD"}  # SAME action
        }
    }
)

assert response.json()["decision"] == "allow"
print("✓ Override token works for approved action")

# 4. Try to replay token (should fail)
response = requests.post(
    f"{BASE_URL}/api/v1/gateway/execute",
    headers={"Authorization": f"Bearer {JWT}"},
    json={
        "uapk_id": "test-agent",
        "agent_id": "instance-1",
        "capability_token": override_token,  # SAME token
        "action": {
            "type": "wire_transfer",
            "tool": "bank_api",
            "params": {"amount": 100000, "currency": "USD"}
        }
    }
)

assert response.json()["decision"] == "deny"
assert "already_used" in str(response.json()["reasons"]).lower()
print("✓ Replay attack prevented (one-time-use)")

# 5. Try to use token for different action (should fail)
# (Create new approval first, then try to use its token for different params)
```

---

## 📊 Monitoring

### Key Metrics to Watch

After deployment, monitor these metrics:

1. **Override Token Usage**
   - Total override tokens issued
   - Override tokens consumed successfully
   - Override tokens rejected (replay attempts)
   - Override tokens rejected (action mismatch)

2. **Approval Flow**
   - Approvals created per day
   - Average time to approval
   - Approval expiration rate
   - Approval consumption rate

3. **Gateway Decisions**
   - ALLOW rate
   - DENY rate
   - ESCALATE rate
   - Decision latency

### Database Queries

```sql
-- Check override token consumption
SELECT
    approval_id,
    status,
    consumed_at,
    consumed_interaction_id,
    created_at,
    decided_at
FROM approvals
WHERE consumed_at IS NOT NULL
ORDER BY consumed_at DESC
LIMIT 10;

-- Check for replay attempts (would be denied at gateway level)
-- Look for repeated capability_token values in interaction_records
SELECT
    uapk_id,
    agent_id,
    decision,
    COUNT(*) as attempt_count
FROM interaction_records
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY uapk_id, agent_id, decision
HAVING COUNT(*) > 10  -- Potential replay attack
ORDER BY attempt_count DESC;

-- Approval statistics
SELECT
    status,
    COUNT(*) as count,
    COUNT(CASE WHEN consumed_at IS NOT NULL THEN 1 END) as consumed_count
FROM approvals
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY status;
```

---

## 🐛 Troubleshooting

### Migration Fails

**Error:** `revision 0007 not found`

**Solution:** Your database is not at revision 0007. Check current revision:
```bash
alembic current
alembic history
```

If behind, upgrade incrementally:
```bash
alembic upgrade +1  # Upgrade one step at a time
alembic current     # Check progress
```

### Override Token Always Denied

**Symptoms:** All override tokens return `override_token_invalid`

**Check:**
1. Approval exists: `SELECT * FROM approvals WHERE approval_id = 'appr-xxx'`
2. Approval is APPROVED: `status = 'approved'`
3. Approval not expired: `expires_at > NOW()`
4. Approval not consumed: `consumed_at IS NULL`
5. Action hash matches: Compute hash and compare

**Debug:**
```python
from app.core.action_hash import compute_action_hash

# Hash from approval
approval_hash = compute_action_hash(approval.action)

# Hash from current request
request_hash = compute_action_hash(current_action)

print(f"Approval hash: {approval_hash}")
print(f"Request hash:  {request_hash}")
print(f"Match: {approval_hash == request_hash}")
```

### default_org_id Returns None

**Symptoms:** UI shows "No organization" or API returns 400

**Check:**
1. User has memberships: `SELECT * FROM memberships WHERE user_id = 'xxx'`
2. Memberships are loaded: Check logs for "SELECT ... memberships"
3. AuthService uses selectinload: `selectinload(User.memberships)`

**Fix:** Ensure AuthService.get_user_by_id uses eager loading (already applied in P0 fixes)

---

## 📝 Rollback Plan

If issues occur, rollback in reverse order:

### 1. Rollback Code

```bash
git revert HEAD  # Or checkout previous commit
docker-compose build
docker-compose up -d
```

### 2. Rollback Database

```bash
# Downgrade migration
alembic downgrade -1

# Or restore from backup
psql -U postgres -d uapk_gateway < backup_TIMESTAMP.sql
```

### 3. Verify Rollback

```bash
# Check migration version
alembic current  # Should show 0007

# Check columns removed
docker exec -it uapk-postgres psql -U postgres -d uapk_gateway -c "\d approvals"
# Should NOT have consumed_at or consumed_interaction_id
```

---

## ✅ Success Criteria

Deployment is successful when:

- [x] Migration 0008 applied without errors
- [x] All services start cleanly
- [x] 8 P0 integration tests pass
- [x] Smoke tests pass
- [x] Override token flow works end-to-end
- [x] Replay protection confirmed working
- [x] No AttributeError crashes in logs
- [x] Monitoring dashboard shows healthy metrics

---

## 🎯 Pilot Customer Demo Script

### Demo 1: Normal Flow

1. Show manifest registration
2. Execute action → ALLOW
3. Show tamper-evident audit log

### Demo 2: Approval Flow

1. Execute high-risk action → ESCALATE
2. Show approval task in dashboard
3. Approve action → get override token
4. Execute with override token → ALLOW
5. Show audit log with approval reference

### Demo 3: Security Features

1. Try to replay override token → DENY
2. Try to modify action params → DENY
3. Show hash-chained audit log integrity

---

## 📞 Support

For issues during deployment:

1. Check logs: `docker-compose logs backend -f`
2. Check database: `docker exec -it uapk-postgres psql -U postgres -d uapk_gateway`
3. Run health check: `curl http://localhost:8000/health`
4. Review this document's Troubleshooting section

**Critical Issues:** If pilot customer is waiting, prioritize rollback over debugging in production.
