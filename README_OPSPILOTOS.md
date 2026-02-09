# OpsPilotOS - Autonomous SaaS Business-in-a-Box

**A self-operating micro-SaaS that ingests customer requests, generates deliverables, invoices customers, tracks VAT/taxes, manages subscriptions, and produces compliance artifacts — all run by autonomous agents with strict policy controls.**

OpsPilotOS demonstrates the UAPK (Universal Agent Protocol Kit) vision: a **signed manifest as single source of truth** for an entire autonomous business instance, mintable as an NFT with tamper-evident audit trails.

---

## Table of Contents

- [Vision & Value Proposition](#vision--value-proposition)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Manifest as Source of Truth](#manifest-as-source-of-truth)
- [Core Features](#core-features)
- [Tax/VAT Implementation](#taxvat-implementation)
- [Policy Guardrails & Governance](#policy-guardrails--governance)
- [NFT Business Instance](#nft-business-instance)
- [Observability & Audit](#observability--audit)
- [Development](#development)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [FAQ](#faq)

---

## Vision & Value Proposition

OpsPilotOS proves that an **entire SaaS business can be instantiated from a signed manifest**, with:

1. **Deterministic Runtime**: Manifest → Plan → Execution (fully reproducible)
2. **Autonomous Operations**: 7 agents handle intake, fulfillment, billing, tax, support, monitoring
3. **Policy Enforcement**: Non-bypassable guardrails, approval gates, rate limits
4. **Tax/VAT Compliance**: EU VAT rules, reverse charge, jurisdictional handling
5. **Tamper-Evident Audit**: Hash-chained event log + Ed25519 signatures
6. **NFT-Mintable**: Business instance as NFT with merkle root of audit trail
7. **Safety by Default**: `executionMode: dry_run` requires human approval for destructive actions

**Use Cases:**
- Content-as-a-Service businesses
- Automated consulting/advisory services
- Compliance-heavy SaaS requiring audit trails
- Multi-tenant AI agent platforms
- Micro-SaaS templates for rapid deployment

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  UAPK Manifest (JSON-LD)                     │
│  Single Source of Truth: Policy, Agents, Workflows, Config  │
└──────────────────────┬──────────────────────────────────────┘
                       │ uapk verify
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               Deterministic Plan Resolution                  │
│  manifestHash → planHash → runtime/plan.lock.json            │
└──────────────────────┬───────────────────────────────────────┘
                       │ uapk run
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    OpsPilotOS Runtime                         │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │   FastAPI   │  │   Agents    │  │   Workflows  │        │
│  │     API     │  │  (7 types)  │  │   (4 pipes)  │        │
│  └─────────────┘  └─────────────┘  └──────────────┘        │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │   Policy    │  │  Tax/VAT    │  │     CAS      │        │
│  │   Engine    │  │  Calculator │  │  (Content)   │        │
│  └─────────────┘  └─────────────┘  └──────────────┘        │
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │  Tamper-Evident Audit Log (Hash Chain)          │        │
│  └─────────────────────────────────────────────────┘        │
└───────────────────────┬──────────────────────────────────────┘
                        │ merkleRoot
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    NFT Minting (Anvil)                        │
│  tokenURI → CAS bundle (manifestHash + planHash + merkle)    │
└──────────────────────────────────────────────────────────────┘
```

### Request Flow

```
User Request (API/CLI)
    │
    ├──> FastAPI Endpoint
    │       │
    │       ├──> Auth (JWT/API Key)
    │       │
    │       └──> Policy Engine
    │              ├─ ALLOW  → Execute
    │              ├─ DENY   → Reject
    │              └─ ESCALATE → HITL Queue
    │
    ├──> Agent Execution
    │       ├─ FulfillmentAgent (RAG + Content Gen + PDF Export)
    │       ├─ BillingAgent (Invoice + VAT Calc + Ledger)
    │       ├─ TaxAgent (VAT Reports + Compliance)
    │       └─ ...
    │
    └──> Audit Event (Hash Chain)
           └──> Merkle Root Update
```

---

## Quick Start

### Prerequisites
- **Python 3.12+**
- **Docker** (optional, for Anvil blockchain)

### Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.opspilotos.txt

# 2. Run bootstrap script (creates DB, admin user, plans)
chmod +x scripts/bootstrap_demo.sh
./scripts/bootstrap_demo.sh

# 3. Verify manifest and resolve plan
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld

# 4. Run the application
python -m uapk.cli run manifests/opspilotos.uapk.jsonld
```

### Access

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

**Default Credentials:**
- Email: `admin@opspilotos.local`
- Password: `changeme123`

### End-to-End Demo

```bash
# In terminal 1: Run the application
python -m uapk.cli run manifests/opspilotos.uapk.jsonld

# In terminal 2: Run E2E demo
chmod +x scripts/run_e2e_demo.sh
./scripts/run_e2e_demo.sh
```

**Demo Flow:**
1. Login as admin
2. Create project
3. Upload KB documents
4. Request deliverable → FulfillmentAgent generates content (MD + PDF)
5. Generate invoice → BillingAgent applies VAT rules
6. Export VAT report
7. Export ledger (DATEV-style CSV)
8. Attempt NFT mint (requires HITL approval in dry_run)

---

## Manifest as Source of Truth

The **UAPK Manifest** (`manifests/opspilotos.uapk.jsonld`) is the canonical definition of the entire business:

### Structure

```json
{
  "@context": "https://uapk.ai/context/v0.1",
  "@id": "urn:uapk:opspilotos:v1",
  "uapkVersion": "0.1",
  "name": "OpsPilotOS",
  "executionMode": "dry_run",

  "cryptoHeader": {
    "hashAlg": "sha256",
    "manifestHash": "",
    "planHash": "",
    "merkleRoot": "",
    "signature": "dev-signature"
  },

  "corporateModules": {
    "governance": { /* roles, approvals, retention */ },
    "policyGuardrails": { /* tool permissions, deny rules, gates */ },
    "financeOps": { /* chart of accounts, invoice numbering */ },
    "taxOps": { /* VAT rules, jurisdictions, rates */ }
  },

  "aiOsModules": {
    "agentProfiles": [ /* 7 agent definitions */ ],
    "workflows": [ /* 4 workflow pipelines */ ],
    "promptTemplates": { /* LLM prompts */ },
    "rag": { /* KB config */ }
  },

  "saasModules": {
    "userManagement": { /* auth, sessions */ },
    "billing": { /* plans, pricing */ },
    "contentManagement": { /* projects, deliverables */ }
  },

  "connectors": {
    "database": { "type": "sqlite", "path": "runtime/opspilotos.db" },
    "nftChain": { "type": "anvil", "rpcUrl": "http://localhost:8545" },
    "contentAddressing": { "type": "local-cas" }
  }
}
```

### Verification & Resolution

```bash
# Verify manifest (validates schema, computes hashes, resolves plan)
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld
```

**Outputs:**
- `runtime/plan.json`: Human-readable resolved plan
- `runtime/plan.lock.json`: Deterministic (sorted keys, no whitespace)
- `runtime/manifest_resolved.jsonld`: Manifest with computed hashes

**Hashes:**
- `manifestHash`: SHA-256 of canonical manifest (excluding cryptoHeader)
- `planHash`: SHA-256 of resolved plan (deterministic)
- `merkleRoot`: Merkle root of audit events (computed during run)

---

## Core Features

### 1. User Management
- JWT-based authentication
- RBAC: Owner, Admin, Operator, Viewer
- Organizations with multi-tenancy
- API keys for programmatic access

### 2. Content Management
- **Projects**: Organize deliverables
- **Knowledge Base**: Upload markdown docs for RAG
- **Deliverables**: Agent-generated content (MD + PDF)

**Example:**
```bash
curl -X POST http://localhost:8000/deliverables \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "project_id": 1,
    "title": "Cloud Migration Plan",
    "description": "Generate migration strategy"
  }'
```

### 3. Invoice Management
- Generate invoices with VAT calculation
- Ledger entries (double-entry bookkeeping)
- Invoice numbering scheme from manifest
- Export to DATEV-like CSV

**Example:**
```bash
curl -X POST http://localhost:8000/billing/invoices/generate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "org_id": 1,
    "customer_country": "DE",
    "customer_vat_id": "DE123456789",
    "is_business": true,
    "items": [
      {"description": "Consulting Service", "quantity": 1, "unit_price": 500}
    ]
  }'
```

### 4. Subscription Management
- Plans defined in manifest
- Seat limits and entitlement checks
- Renewal workflows (simulated)

### 5. Autonomous Agents

| Agent | Role | Capabilities |
|-------|------|--------------|
| **IntakeAgent** | Request Monitor | Monitors deliverable requests, triages tickets |
| **FulfillmentAgent** | Content Generator | RAG retrieval, content generation, PDF export |
| **BillingAgent** | Invoice Manager | Invoice generation, VAT application, ledger entries |
| **TaxAgent** | Tax Compliance | VAT reports, jurisdiction checks |
| **PolicyAgent** | Guardrail Enforcer | Policy evaluation, HITL request creation |
| **SupportAgent** | Customer Support | Ticket triage, response drafting |
| **SREAgent** | Reliability Monitor | Metrics monitoring, incident detection |

### 6. Workflows

| Workflow | Steps | Trigger |
|----------|-------|---------|
| **deliverable_fulfillment_pipeline** | Retrieve request → KB context → Generate → Export PDF → Billing | New deliverable request |
| **subscription_renewal_pipeline** | Check renewals → Invoice → VAT → Send (gated) → Dunning | Daily cron |
| **vat_reporting_pipeline** | Collect invoices → Validate → Compute summary → Export | End of month |
| **incident_pipeline** | Detect anomaly → Create ticket → Escalate (gated) | Metric threshold |

---

## Tax/VAT Implementation

OpsPilotOS implements **simplified EU VAT rules** with jurisdiction-specific handling.

### VAT Rules

1. **EU B2B with valid VAT ID**: Reverse charge (0% VAT, customer pays VAT)
2. **EU B2C or B2B without VAT ID**: Apply VAT rate of customer country
3. **Non-EU**: No VAT (0%)

### VAT Rates (from manifest)

```json
"vat_rates": {
  "DE": 0.19,  // Germany: 19%
  "FR": 0.20,  // France: 20%
  "GB": 0.20,  // UK: 20%
  "NL": 0.21,  // Netherlands: 21%
  "US": 0.0    // No VAT
}
```

### Example Calculations

**Case 1: EU B2B with VAT ID (Reverse Charge)**
```
Subtotal: €100
Customer: DE, VAT ID: DE123456789
→ VAT: €0 (reverse charge)
→ Total: €100
→ Invoice note: "Reverse charge applies"
```

**Case 2: EU B2C (VAT Applied)**
```
Subtotal: €100
Customer: DE, no VAT ID
→ VAT: €19 (19% German VAT)
→ Total: €119
```

**Case 3: Non-EU (No VAT)**
```
Subtotal: €100
Customer: US
→ VAT: €0
→ Total: €100
```

### VAT Reporting

```bash
# Generate VAT report for period
curl -X GET "http://localhost:8000/billing/reports/vat?org_id=1&period_start=2024-01-01&period_end=2024-12-31" \
  -H "Authorization: Bearer $TOKEN"
```

**Output:**
```json
{
  "period": {"start": "2024-01-01", "end": "2024-12-31"},
  "summary": {
    "totalSales": 5000.0,
    "totalVATCollected": 950.0,
    "reverseChargeTransactions": 2000.0
  },
  "salesByCountry": {
    "DE": 3000.0,
    "FR": 1000.0,
    "GB": 1000.0
  },
  "vatByRate": {
    "19%": 570.0,
    "20%": 380.0
  }
}
```

---

## Policy Guardrails & Governance

### Policy Engine

The **PolicyEngine** enforces 5 types of checks:

1. **Tool Permissions**: Agents can only use allowed tools
2. **Deny Rules**: Blacklist of forbidden actions
3. **Rate Limits**: Sliding window (100 actions/minute by default)
4. **Live Action Gates**: Require approval in `dry_run` mode
5. **Execution Mode**: Additional constraints in dry_run

### Live Action Gates

Actions that require approval in `dry_run` mode:

- `mint_nft`
- `send_invoice_email`
- `mark_invoice_paid`
- `send_customer_email`
- `charge_payment_method`

### Example: Policy Evaluation

```python
from uapk.policy import check_policy

result = check_policy(
    agent_id="FulfillmentAgent",
    action="generate_content",
    tool="generate_content"
)

# result.decision → "ALLOW" | "DENY" | "ESCALATE"
# result.reasons → ["All policy checks passed"]
# result.requires_approval → False
```

### Human-in-the-Loop (HITL)

When an action requires approval:

```bash
# 1. List pending HITL requests
curl -X GET http://localhost:8000/hitl/requests?status=pending \
  -H "Authorization: Bearer $TOKEN"

# 2. Approve request
curl -X POST http://localhost:8000/hitl/requests/1/approve \
  -H "Authorization: Bearer $TOKEN"

# 3. Agent retries with approval
```

---

## NFT Business Instance

OpsPilotOS allows minting the **entire business instance as an NFT**, creating an immutable record of the business configuration and audit trail.

### What Gets Minted

The NFT metadata includes:

```json
{
  "name": "OpsPilotOS Business Instance",
  "description": "Autonomous SaaS Business-in-a-Box",
  "attributes": [
    {"trait_type": "Manifest Hash", "value": "abc123..."},
    {"trait_type": "Plan Hash", "value": "def456..."},
    {"trait_type": "Audit Merkle Root", "value": "ghi789..."},
    {"trait_type": "Execution Mode", "value": "dry_run"}
  ],
  "properties": {
    "manifestCAS": "abc123...",  // CAS hash of manifest
    "planCAS": "def456...",      // CAS hash of plan.lock.json
    "uapkVersion": "0.1"
  }
}
```

### Minting Process

```bash
# 1. Verify manifest (computes hashes)
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld

# 2. Run application (generates audit events)
python -m uapk.cli run manifests/opspilotos.uapk.jsonld

# 3. Mint NFT (computes merkle root)
python -m uapk.cli mint manifests/opspilotos.uapk.jsonld --force
```

**Outputs:**
- `runtime/cas/<hash>`: Content-addressed metadata
- `runtime/nft_mint_receipt.json`: Mint receipt

### Blockchain Integration

OpsPilotOS supports local Anvil (Foundry) blockchain:

```bash
# Start Anvil (in separate terminal)
docker run -p 8545:8545 ghcr.io/foundry-rs/foundry:latest anvil --host 0.0.0.0

# Or with docker-compose
docker-compose -f docker-compose.opspilotos.yml up anvil
```

**Solidity Contract** (reference):
```solidity
contract OpsPilotOSBusinessInstance is ERC721URIStorage {
    struct BusinessMetadata {
        string manifestHash;
        string planHash;
        string auditMerkleRoot;
        uint256 mintedAt;
    }
    mapping(uint256 => BusinessMetadata) public businessMetadata;
}
```

---

## Observability & Audit

### Tamper-Evident Audit Log

Every action emits an audit event with:

- **eventId**: Unique identifier
- **timestamp**: ISO 8601 UTC
- **eventType**: `agent_action`, `policy_check`, `system`, `nft`, etc.
- **action**: Specific action taken
- **params**: Input parameters
- **result**: Output (if applicable)
- **decision**: ALLOW/DENY/ESCALATE (for policy checks)
- **previousHash**: SHA-256 of previous event (hash chain)
- **eventHash**: SHA-256 of this event

### Hash Chain Verification

```bash
# Verify audit log integrity
python -c "from uapk.audit import get_audit_log; print(get_audit_log().verify_chain())"

# Output:
# {'valid': True, 'eventCount': 42, 'message': 'Hash chain verified successfully'}
```

### Merkle Root

```bash
# Compute merkle root
python -c "from uapk.audit import get_audit_log; print(get_audit_log().compute_merkle_root())"

# Output:
# e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

### Metrics

```bash
# Prometheus-style metrics
curl http://localhost:8000/metrics

# Output:
# opspilotos_events_total{type="agent_action"} 15
# opspilotos_events_total{type="policy_check"} 20
# opspilotos_events_total{type="system"} 2
# opspilotos_events_total{type="all"} 37
```

---

## Development

### Project Structure

```
uapk-gateway/
├── manifests/
│   └── opspilotos.uapk.jsonld       # UAPK manifest (source of truth)
├── uapk/
│   ├── cli.py                       # CLI (verify, run, mint, info)
│   ├── manifest_schema.py           # Pydantic schemas
│   ├── interpreter.py               # Manifest loader & plan resolver
│   ├── policy.py                    # Policy engine
│   ├── audit.py                     # Tamper-evident audit log
│   ├── tax.py                       # VAT calculator
│   ├── cas.py                       # Content-addressed storage
│   ├── api/
│   │   ├── main.py                  # FastAPI app
│   │   ├── auth.py                  # Auth endpoints
│   │   ├── organizations.py         # Org endpoints
│   │   ├── projects.py              # Project endpoints
│   │   ├── deliverables.py          # Deliverable endpoints
│   │   ├── billing.py               # Billing endpoints
│   │   ├── hitl.py                  # HITL endpoints
│   │   ├── nft_routes.py            # NFT endpoints
│   │   └── metrics.py               # Metrics endpoints
│   ├── db/
│   │   ├── models.py                # SQLModel ORM models
│   │   └── __init__.py              # DB initialization
│   ├── agents/
│   │   ├── base.py                  # BaseAgent class
│   │   ├── fulfillment.py           # FulfillmentAgent
│   │   └── billing.py               # BillingAgent
│   ├── workflows/
│   │   └── engine.py                # Workflow engine
│   └── nft/
│       └── minter.py                # NFT minting logic
├── fixtures/
│   ├── kb/                          # Knowledge base docs
│   └── deliverable_requests/        # Example requests
├── scripts/
│   ├── bootstrap_demo.sh            # Bootstrap script
│   └── run_e2e_demo.sh              # E2E demo script
├── runtime/                         # Generated at runtime
│   ├── opspilotos.db                # SQLite DB
│   ├── audit.jsonl                  # Audit log
│   ├── plan.json                    # Resolved plan
│   ├── plan.lock.json               # Deterministic plan
│   ├── manifest_resolved.jsonld     # Manifest with hashes
│   ├── nft_mint_receipt.json        # NFT receipt
│   └── cas/                         # Content-addressed storage
├── artifacts/                       # Deliverables, exports
│   ├── deliverables/                # Generated PDFs
│   └── exports/                     # Ledger CSVs
├── logs/                            # Simulated logs
│   ├── emails.jsonl                 # Simulated emails
│   └── payments.jsonl               # Simulated payments
├── docker-compose.opspilotos.yml    # Docker Compose
├── Dockerfile.opspilotos            # Dockerfile
├── requirements.opspilotos.txt      # Python dependencies
└── test_opspilotos.py               # Test suite
```

### CLI Commands

```bash
# Verify manifest and resolve plan
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld

# Run application
python -m uapk.cli run manifests/opspilotos.uapk.jsonld

# Mint NFT
python -m uapk.cli mint manifests/opspilotos.uapk.jsonld [--force]

# Show manifest info
python -m uapk.cli info manifests/opspilotos.uapk.jsonld
```

---

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest test_opspilotos.py -v

# Run specific test class
pytest test_opspilotos.py::TestVATCalculation -v

# Run with coverage
pytest test_opspilotos.py --cov=uapk --cov-report=html
```

### Test Coverage

- ✅ Manifest verification & deterministic plan resolution
- ✅ VAT calculation (EU B2B reverse charge, EU B2C, non-EU)
- ✅ Audit log hash chain integrity
- ✅ Merkle root computation
- ✅ Content-addressed storage (CAS)
- ✅ Policy engine (tool permissions, deny rules, live action gates)

---

## Production Deployment

### Security Checklist

⚠️ **IMPORTANT: OpsPilotOS ships in `dry_run` mode for safety. Before deploying to production:**

1. **Change executionMode**: Set `"executionMode": "live"` in manifest
2. **Secure Secrets**: Use environment variables for:
   - JWT secret key
   - Database encryption keys
   - API keys for external services
3. **HTTPS Only**: Use Caddy or nginx for TLS termination
4. **Database**: Migrate from SQLite to PostgreSQL/MySQL
5. **Blockchain**: Use real testnet or mainnet (not Anvil)
6. **VAT Validation**: Integrate VIES API for real VAT ID validation
7. **Email/Payments**: Replace simulators with real providers (SendGrid, Stripe)
8. **Rate Limiting**: Tune per your workload
9. **Backup**: Regular DB backups + audit log exports to S3 Object Lock
10. **Monitoring**: Deploy Prometheus + Grafana

### Environment Variables

```bash
export UAPK_EXECUTION_MODE=live
export UAPK_JWT_SECRET=<random-256-bit-key>
export UAPK_DB_URL=postgresql://user:pass@host/db
export UAPK_STRIPE_KEY=sk_live_...
export UAPK_SENDGRID_KEY=SG.abc...
export UAPK_NFT_CHAIN_RPC=https://mainnet.infura.io/v3/...
```

### Docker Compose (Production)

```yaml
version: '3.8'
services:
  app:
    image: opspilotos:latest
    environment:
      - UAPK_EXECUTION_MODE=live
      - UAPK_JWT_SECRET=${UAPK_JWT_SECRET}
      - UAPK_DB_URL=${UAPK_DB_URL}
    ports:
      - "8000:8000"
    restart: unless-stopped
```

---

## FAQ

### Q: Is this production-ready?

**A:** OpsPilotOS is a **reference implementation** demonstrating the UAPK vision. It includes:

✅ Core features (user mgmt, content, billing, tax)
✅ Real VAT calculation logic
✅ Tamper-evident audit logs
✅ Policy enforcement
✅ NFT minting capability

⚠️ Production hardening required:
- Replace SQLite with PostgreSQL
- Use real payment/email providers
- VIES API for VAT validation
- Comprehensive error handling
- Load testing & optimization

### Q: What LLM does FulfillmentAgent use?

**A:** By default, a **deterministic stub** (template filling) for reproducibility. To use real LLMs:

1. Update `modelRegistry` in manifest:
   ```json
   "modelRegistry": {
     "default": {
       "provider": "openai",
       "modelId": "gpt-4",
       "apiKey": "sk-..."
     }
   }
   ```

2. Implement LLM integration in `FulfillmentAgent.generate_content()`

3. Supported: OpenAI, Anthropic, local Ollama

### Q: How does the NFT prove authenticity?

**A:** The NFT's `tokenURI` points to content-addressed metadata containing:

- `manifestHash`: Immutable hash of business configuration
- `planHash`: Deterministic runtime plan
- `auditMerkleRoot`: Merkle root of all audit events

**Anyone can verify:**
1. Retrieve metadata from tokenURI (CAS)
2. Recompute hashes from manifest & plan
3. Verify audit log hash chain
4. Confirm merkle root matches

This creates **cryptographic proof** of the business instance's configuration and operational history.

### Q: Can I switch from dry_run to live mode?

**A:** Yes, but be careful:

1. Update manifest: `"executionMode": "live"`
2. Run `uapk verify` (recomputes planHash)
3. Review all "live action gates" in your policies
4. Test thoroughly in staging environment
5. Enable real connectors (Stripe, SendGrid, etc.)

**Warning:** In `live` mode, actions execute without approval. Ensure policies are correct!

### Q: How do I add a new agent?

```json
// 1. Add to manifest
{
  "agentId": "my-custom-agent",
  "role": "custom-task",
  "capabilities": ["do_thing"],
  "allowedTools": ["tool1", "tool2"],
  "promptTemplates": ["my_template"]
}

// 2. Implement agent class
class MyCustomAgent(BaseAgent):
    async def execute(self, context):
        # Your logic here
        return result

// 3. Register in workflow
{
  "workflowId": "my_workflow",
  "steps": [
    {"action": "do_thing", "agent": "my-custom-agent"}
  ]
}
```

### Q: What's the difference between UAPK and LangChain/AutoGPT?

| Aspect | UAPK (OpsPilotOS) | LangChain/AutoGPT |
|--------|-------------------|-------------------|
| **Philosophy** | Manifest-first, governance-first | Code-first, capability-first |
| **Source of Truth** | Signed JSON-LD manifest | Python code |
| **Policy** | Non-bypassable, declarative | Optional, imperative |
| **Audit** | Tamper-evident (hash chain + signatures) | Logs (mutable) |
| **Compliance** | Built-in (VAT, GDPR, DPA flags) | DIY |
| **Reproducibility** | Deterministic (manifestHash → planHash) | Non-deterministic |
| **Business Instance** | Mintable as NFT | Not applicable |

---

## License

Apache 2.0 (same as parent UAPK Gateway project)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/anthropics/uapk-gateway/issues)
- **Docs**: See `docs-mkdocs-archive/` for full UAPK documentation
- **Examples**: See `examples/` for more manifest templates

---

**Built with UAPK Gateway** | [Learn More About UAPK](../README.md)
