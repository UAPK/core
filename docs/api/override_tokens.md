# Override Tokens API

**Feature**: Ed25519-signed, short-lived, single-use tokens for approved HITL requests
**Implemented**: Milestone 1.1
**Version**: 2.0.0

---

## Overview

Override tokens allow agents to retry gated actions after receiving human approval. The token proves that:

1. **Approval was granted** (approval_id references HITLRequest)
2. **For this specific action** (action_hash binds to action + params)
3. **Recently** (5-minute expiry)
4. **Not yet used** (one-time-use enforcement via consumed_at)
5. **Cryptographically authentic** (Ed25519 signature from gateway)

---

## Token Format

Override tokens use a JWT-like format with Ed25519 signatures:

```
<header_base64>.<payload_base64>.<signature_base64>
```

**Header**:
```json
{
  "alg": "EdDSA",
  "typ": "OVR"
}
```

**Payload**:
```json
{
  "approval_id": 123,
  "action_hash": "abc123...",
  "iat": 1707408000,
  "exp": 1707408300
}
```

**Signature**: Ed25519 signature of `header.payload` using gateway private key

---

## Workflow

### 1. Agent Attempts Gated Action

```bash
POST /nft/mint
Authorization: Bearer <user_jwt>
{
  "force": false
}
```

**Response** (if in dry_run mode):
```json
{
  "error": "Action 'mint_nft' requires approval in dry_run mode",
  "approval_required": true,
  "approval_id": 123
}
```

### 2. Human Approves via HITL

```bash
POST /hitl/requests/123/approve
Authorization: Bearer <admin_jwt>
```

**Response**:
```json
{
  "id": 123,
  "status": "approved",
  "approved_by": 1,
  "override_token": "eyJhbGc...full_token...xyz"
}
```

### 3. Agent Retries with Override Token

```bash
POST /nft/mint
Authorization: Bearer <user_jwt>
{
  "force": false,
  "override_token": "eyJhbGc...full_token...xyz"
}
```

**Response** (if token valid):
```json
{
  "status": "success",
  "token_id": 1,
  "transaction_hash": "0x..."
}
```

---

## API Endpoints

### Approval (Modified in M1.1)

**Endpoint**: `POST /hitl/requests/{id}/approve`

**Request**:
```bash
curl -X POST http://localhost:8000/hitl/requests/123/approve \
  -H "Authorization: Bearer <admin_jwt>"
```

**Response**:
```json
{
  "id": 123,
  "status": "approved",
  "approved_by": 1,
  "override_token": "eyJhbGciOiJFZERTQSIsInR5cCI6Ik9WUiJ9.eyJhcHByb3ZhbF9pZCI6MTIzLCJhY3Rpb25faGFzaCI6ImFiYzEyMyIsImlhdCI6MTcwNzQwODAwMCwiZXhwIjoxNzA3NDA4MzAwfQ.signature_base64"
}
```

**New Field**: `override_token` (string) - Ed25519-signed token for retry

---

## Policy Engine Integration

### PolicyEngine.evaluate() - New Parameter

```python
def evaluate(
    agent_id: Optional[str],
    action: str,
    tool: Optional[str] = None,
    user_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    override_token: Optional[str] = None,  # NEW in M1.1
    session: Optional[Session] = None      # NEW in M1.1 (for consumption tracking)
) -> PolicyResult:
    ...
```

**Evaluation flow with override token**:

1. If `override_token` provided:
   - Verify Ed25519 signature
   - Check expiry (iat + 5 minutes)
   - Check action_hash matches (binds to specific action + params)
   - Load HITLRequest by approval_id (with SELECT FOR UPDATE lock)
   - Check consumed_at is NULL (one-time-use)
   - If all valid: mark consumed, return ALLOW
   - If any check fails: return DENY with reason

2. If no `override_token`:
   - Continue with normal 5-step policy evaluation

---

## Security Properties

### Cryptographic Binding

- **Signature**: Ed25519 prevents forgery
- **Action hash**: Binds token to specific action + params (cannot reuse for different action)
- **Expiry**: 5-minute window limits window of opportunity
- **One-time-use**: consumed_at prevents replay attacks

### Attack Mitigations

| Attack | Mitigation |
|--------|------------|
| **Token forgery** | Ed25519 signature verification |
| **Replay attack** | consumed_at timestamp (one-time-use) |
| **Action substitution** | action_hash binds to action + params |
| **Time extension** | exp claim enforced (5 minutes) |
| **Approval ID spoofing** | approval_id must exist in database |

---

## Database Schema Changes (M1.1)

### HITLRequest Table

**New columns**:
```sql
ALTER TABLE hitl_requests
ADD COLUMN override_token_hash VARCHAR(64) NULL;

ALTER TABLE hitl_requests
ADD COLUMN consumed_at TIMESTAMP NULL;
```

**Fields**:
- `override_token_hash` (VARCHAR(64)): SHA-256 hash of issued override token (for audit)
- `consumed_at` (TIMESTAMP): When override token was consumed (NULL = not consumed)

**Note**: In SQLModel with create_all(), these columns are auto-created.

---

## Testing

### Unit Tests

```bash
pytest tests/test_override_tokens.py -v
```

**Test cases**:
- Override token creation and format
- Token payload structure
- Action hash determinism
- Valid token verification
- Expired token rejection
- Wrong action rejection
- Wrong params rejection
- Tampered token rejection
- Invalid signature rejection
- One-time-use enforcement
- Gated action without token still escalates

### Integration Test (Manual)

```bash
# 1. Start app
python -m uapk.cli run manifests/opspilotos.uapk.jsonld

# 2. Login as admin
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -d '{"email": "admin@opspilotos.local", "password": "changeme123"}' \
  | jq -r '.access_token')

# 3. Create HITL request (via mint_nft without override token)
# This will escalate and create HITL request automatically
# OR create manually:
curl -X POST http://localhost:8000/hitl/requests \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"org_id": 1, "action": "mint_nft", "reason": "Test approval", "params": {}}'

# 4. Approve request (get override token)
RESPONSE=$(curl -X POST http://localhost:8000/hitl/requests/1/approve \
  -H "Authorization: Bearer $TOKEN")
echo $RESPONSE | jq .

OVERRIDE_TOKEN=$(echo $RESPONSE | jq -r '.override_token')
echo "Override token: $OVERRIDE_TOKEN"

# 5. Retry action with override token (should succeed)
curl -X POST http://localhost:8000/nft/mint \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"override_token\": \"$OVERRIDE_TOKEN\"}"

# 6. Try again with same token (should fail - already consumed)
curl -X POST http://localhost:8000/nft/mint \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"override_token\": \"$OVERRIDE_TOKEN\"}"
# Expected: Error "Override token already consumed"
```

---

## Configuration

### Environment Variables

**Development mode** (auto-generates keypair):
- Keys stored in `runtime/keys/gateway_ed25519.pem` (private)
- Keys stored in `runtime/keys/gateway_ed25519.pub` (public)

**Production mode** (use env var):
```bash
export UAPK_ED25519_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...PEM content...
-----END PRIVATE KEY-----"
```

**Generation**:
```bash
# Option 1: Let UAPK generate on first run (development)
python -m uapk.cli run manifests/...
# Prints: "Generated Ed25519 keypair at runtime/keys/"

# Option 2: Generate manually (production)
# (In future: `uapk keygen --output-dir ./keys/`)
ssh-keygen -t ed25519 -f gateway_ed25519 -N ""
# Then convert to PKCS8 PEM format if needed
```

---

## Limitations (M1.1 Scope)

- **No delegation depth**: Override tokens cannot be delegated further
- **No capability tokens**: Override tokens are single-purpose (one action), not capability grants
- **No revocation**: Cannot revoke issued override tokens (they expire in 5 minutes anyway)
- **No token renewal**: Cannot extend expiry (must request new approval)

---

## Next Steps (Beyond M1.1)

- **M1.2**: Add Ed25519 signatures to audit events (uses same keypair)
- **Future**: Implement capability tokens for broader authorization scopes
- **Future**: Token revocation list (CRL)
- **Future**: Delegation chains (approve-then-delegate)

---

**Related Documentation**:
- `docs/audit/signature_verification.md` (M1.2)
- `docs/security/key-management.md` (Future)
- `UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md` (M1.1 acceptance criteria)
