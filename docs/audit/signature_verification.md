# Audit Event Signature Verification (M1.2)

**Feature**: Ed25519 signatures on every audit event
**Implemented**: Milestone 1.2
**Version**: 2.0.0

---

## Overview

Every audit event is now signed with the gateway's Ed25519 private key, providing:

1. **Authenticity**: Proves event was created by the gateway (not forged)
2. **Integrity**: Detects any tampering with event contents
3. **Non-repudiation**: Gateway cannot deny creating signed events
4. **Chain + Signature**: Dual protection (hash chain prevents reordering, signatures prevent forgery)

---

## Event Structure (M1.2)

### Before M1.2
```json
{
  "eventId": "evt-abc123",
  "timestamp": "2026-02-08T12:00:00Z",
  "eventType": "agent_action",
  "action": "complete_fulfillment",
  "params": {...},
  "result": {...},
  "previousHash": "def456...",
  "eventHash": "ghi789..."
}
```

### After M1.2
```json
{
  "eventId": "evt-abc123",
  "timestamp": "2026-02-08T12:00:00Z",
  "eventType": "agent_action",
  "action": "complete_fulfillment",
  "params": {...},
  "result": {...},
  "previousHash": "def456...",
  "eventHash": "ghi789...",
  "eventSignature": "MEUCIQDx...base64_ed25519_signature..."
}
```

**New Field**: `eventSignature` (string) - Base64-encoded Ed25519 signature

---

## Signature Algorithm

### Signing Process

1. **Canonical JSON construction** (excludes eventSignature):
   ```python
   canonical_fields = {
       'eventId': event['eventId'],
       'timestamp': event['timestamp'],
       'eventType': event['eventType'],
       'agentId': event.get('agentId', ''),
       'userId': event.get('userId', ''),
       'action': event['action'],
       'params': event.get('params', {}),
       'result': event.get('result'),
       'decision': event.get('decision', ''),
       'previousHash': event.get('previousHash', ''),
       'eventHash': event['eventHash']  # Hash computed first
   }
   canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(',', ':'))
   ```

2. **Ed25519 signing**:
   ```python
   message = canonical_json.encode('utf-8')
   signature = private_key.sign(message)  # Ed25519
   event['eventSignature'] = base64.b64encode(signature).decode('utf-8')
   ```

3. **Key used**: Gateway Ed25519 private key (from `runtime/keys/gateway_ed25519.pem` or `UAPK_ED25519_PRIVATE_KEY` env var)

---

## Verification

### Programmatic Verification

```python
from uapk.audit import get_audit_log

audit_log = get_audit_log()
result = audit_log.verify_signatures()

print(result)
# Output:
# {
#   'valid': True,
#   'verified_count': 1234,
#   'failed_count': 0,
#   'failed_events': [],
#   'message': 'Verified 1234/1234 signatures'
# }
```

### CLI Verification

```bash
python -m uapk.cli verify-audit runtime/audit.jsonl
```

**Output** (success):
```
[UAPK VERIFY-AUDIT] Verifying audit log: runtime/audit.jsonl

Step 1/3: Verifying hash chain...
✓ Hash chain valid (1234 events)

Step 2/3: Verifying Ed25519 signatures...
✓ All signatures valid (1234 verified)

Step 3/3: Computing merkle root...
  Merkle root: abc123def456...

✓ Audit log verification complete
  Events: 1234
  Hash chain: VALID
  Signatures: VALID (1234 verified)
  Merkle root: abc123def456...
```

**Output** (failure - tampered event):
```
[UAPK VERIFY-AUDIT] Verifying audit log: runtime/audit.jsonl

Step 1/3: Verifying hash chain...
✓ Hash chain valid (1234 events)

Step 2/3: Verifying Ed25519 signatures...
✗ Signature verification FAILED: Verified 1233/1234 signatures, 1 failed

Failed events:
  - Event evt-abc789: Invalid Ed25519 signature

Exit code: 1
```

---

## Security Properties

### Tamper Detection

**Scenario 1: Modify event field**
- Event field changed (e.g., change action from "mint_nft" to "delete_audit")
- Canonical JSON changes
- Ed25519 signature verification fails
- `verify_signatures()` returns `valid: False`

**Scenario 2: Modify signature**
- Signature tampered or replaced
- Ed25519 verification fails
- Detected immediately

**Scenario 3: Remove event**
- Hash chain breaks (previousHash mismatch)
- `verify_chain()` returns `valid: False`
- Signatures also missing

**Scenario 4: Reorder events**
- Hash chain breaks (previousHash sequence wrong)
- `verify_chain()` returns `valid: False`

**Scenario 5: Inject new event**
- Cannot compute valid eventSignature without gateway private key
- Signature verification fails

### Key Protection

**Development mode**:
- Private key: `runtime/keys/gateway_ed25519.pem` (600 permissions)
- Public key: `runtime/keys/gateway_ed25519.pub` (644 permissions)
- Warning displayed on first generation

**Production mode**:
- Private key from `UAPK_ED25519_PRIVATE_KEY` env var (never written to disk)
- Loaded from environment or secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Backup public key stored securely for verification

---

## Key Management

### Generate Keys (Development)

**Auto-generation**:
```bash
# On first run, keys auto-generated
python -m uapk.cli run manifests/opspilotos.uapk.jsonld

# Output:
# ⚠️  Generating new Ed25519 keypair at runtime/keys
# ⚠️  For production, use UAPK_ED25519_PRIVATE_KEY env var instead
# ✅ Generated and saved Ed25519 keypair to runtime/keys
```

**Manual generation** (future - `uapk keygen` in M2):
```bash
# Will be available in M2.4
uapk keygen --output-dir ./keys/
```

### Load Keys (Production)

```bash
# Generate keypair externally
ssh-keygen -t ed25519 -f gateway_ed25519 -N ""

# Convert to PKCS8 PEM (if needed)
ssh-keygen -p -m PEM -f gateway_ed25519

# Load via env var
export UAPK_ED25519_PRIVATE_KEY="$(cat gateway_ed25519)"

# Run gateway
python -m uapk.cli run manifests/opspilotos.uapk.jsonld
# Output: "✅ Loaded Ed25519 private key from UAPK_ED25519_PRIVATE_KEY env var"
```

---

## Integration with Hash Chain

Audit log now has **dual protection**:

1. **Hash chain** (previousHash → eventHash linking):
   - Prevents reordering
   - Prevents removal
   - Detects sequence breaks

2. **Ed25519 signatures** (eventSignature):
   - Prevents forgery
   - Prevents modification
   - Proves gateway authenticity

**Verification must check BOTH**:
```bash
python -m uapk.cli verify-audit runtime/audit.jsonl
# Checks: hash chain valid? signatures valid?
```

---

## Performance

**Signing overhead**:
- Ed25519 signing: ~10,000 signatures/second (negligible)
- Signature size: 64 bytes (88 bytes base64-encoded)
- Per-event overhead: ~88 bytes storage

**Verification overhead**:
- Ed25519 verification: ~10,000 verifications/second
- Batch verification possible for compliance exports

---

## Testing

### Unit Tests

```bash
pytest tests/test_opspilotos.py::test_audit_signatures -v
```

**Test cases** (added to existing test_opspilotos.py):
- Event signatures created on append
- Signature verification passes for valid events
- Signature verification fails for tampered events
- Signature verification fails with wrong public key
- Verify-audit CLI command works

### Manual Testing

```bash
# 1. Create some audit events
python -m uapk.cli run manifests/opspilotos.uapk.jsonld &
SERVER_PID=$!
sleep 5

# Trigger some actions (creates audit events)
curl http://localhost:8000/healthz

# Stop server
kill $SERVER_PID

# 2. Check event signatures exist
cat runtime/audit.jsonl | jq '.eventSignature' | head -5
# Expected: Base64-encoded signatures (not null)

# 3. Verify signatures
python -m uapk.cli verify-audit runtime/audit.jsonl
# Expected: All checks pass

# 4. Tamper with an event (change a field)
# Manually edit runtime/audit.jsonl, change an action name

# 5. Verify again (should detect tampering)
python -m uapk.cli verify-audit runtime/audit.jsonl
# Expected: Signature verification FAILED
```

---

## Compliance Use Cases

### Evidence-Grade Exports

With M1.2 signatures, audit logs are now suitable for:

- **Legal proceedings**: Cryptographic proof of gateway actions
- **Regulatory audits**: Tamper-evident trail with external verification
- **Internal compliance**: Non-repudiable record of agent operations
- **Incident investigation**: Authentic timeline of events

### Third-Party Verification

External auditors can verify signatures with public key:

1. Obtain public key: `runtime/keys/gateway_ed25519.pub`
2. Load audit log: `runtime/audit.jsonl`
3. Run verification: `python -m uapk.cli verify-audit runtime/audit.jsonl --key path/to/public.pem`
4. Confirm: hash chain valid + signatures valid

---

## Limitations (M1.2 Scope)

- **No database storage**: Signatures in JSONL only (database storage deferred)
- **No S3 Object Lock export**: Export bundles deferred to M2.5
- **No replay capability**: Re-execution from audit log not implemented
- **No timestamp authority**: System clock used (not RFC 3161 TSA)

---

## Next Steps (Beyond M1.2)

- **M2.5**: Evidence-grade audit exports (tar.gz bundles with verification proof)
- **Future**: Database storage for InteractionRecord with signatures
- **Future**: Replay capability (re-execute from audit log)
- **Future**: Timestamp authority integration (RFC 3161)

---

**Related Documentation**:
- `docs/api/override_tokens.md` (M1.1 - uses same Ed25519 keypair)
- `UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md` (M1.2 acceptance criteria)
