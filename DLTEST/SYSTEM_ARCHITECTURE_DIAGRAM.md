# OpsPilotOS - System Architecture Diagram

**Visual representation of the complete UAPK business instance**

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL EVALUATOR VIEW                             │
│                                                                               │
│  "What is this business instance? How does it work? Can I trust it?"        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UAPK MANIFEST (JSON-LD)                               │
│                      manifests/opspilotos.uapk.jsonld                        │
│                                                                               │
│  Single Source of Truth - Defines:                                           │
│  ┌──────────────────┬──────────────────┬──────────────────┬───────────────┐ │
│  │ Corporate Modules│ AI/OS Modules    │ SaaS Modules     │ Connectors    │ │
│  ├──────────────────┼──────────────────┼──────────────────┼───────────────┤ │
│  │ • Governance     │ • 7 Agents       │ • User Mgmt      │ • Database    │ │
│  │ • Policy Rules   │ • 4 Workflows    │ • Content Mgmt   │ • API Server  │ │
│  │ • Finance/Tax    │ • RAG Config     │ • Billing        │ • Object Store│ │
│  │ • Legal/DPA      │ • Prompts        │ • Support        │ • NFT Chain   │ │
│  └──────────────────┴──────────────────┴──────────────────┴───────────────┘ │
│                                                                               │
│  Cryptographic Header:                                                        │
│  • manifestHash: SHA-256 fingerprint of configuration                        │
│  • planHash: SHA-256 of resolved runtime plan                               │
│  • merkleRoot: Merkle root of all audit events                              │
│  • signature: Ed25519 signature (dev mode)                                  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ uapk verify
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DETERMINISTIC PLAN RESOLUTION                           │
│                                                                               │
│  Input: Manifest → Output: runtime/plan.lock.json                           │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Load manifest                                                      │   │
│  │ 2. Validate schema (Pydantic)                                         │   │
│  │ 3. Resolve agents, workflows, connectors, policies                    │   │
│  │ 4. Compute manifestHash (SHA-256 of canonical JSON)                   │   │
│  │ 5. Compute planHash (SHA-256 of resolved plan)                        │   │
│  │ 6. Write plan.json (human-readable)                                   │   │
│  │ 7. Write plan.lock.json (deterministic: sorted keys, no whitespace)   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  Guarantees:                                                                  │
│  ✓ Same manifest → Same planHash (reproducible)                             │
│  ✓ Plan changes → planHash changes (tamper-evident)                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ uapk run
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RUNTIME ENVIRONMENT                                 │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Application                           │  │
│  │                       http://localhost:8000                           │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │   Auth     │  │   Orgs     │  │  Projects  │  │Deliverables│    │  │
│  │  │  Endpoints │  │  Endpoints │  │  Endpoints │  │  Endpoints │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │  Billing   │  │    HITL    │  │    NFT     │  │  Metrics   │    │  │
│  │  │  Endpoints │  │  Endpoints │  │  Endpoints │  │  Endpoints │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Middleware & Security Layer                      │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │  │
│  │  │ JWT Auth       │  │ Rate Limiting  │  │ CORS          │         │  │
│  │  │ (HS256)        │  │ (100/min)      │  │ (restrictable)│         │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       Policy Enforcement Layer                        │  │
│  │                                                                        │  │
│  │  Every request passes through PolicyEngine:                           │  │
│  │  ┌────────────────────────────────────────────────────────────┐      │  │
│  │  │ 1. Check tool permissions (agent → tool mapping)            │      │  │
│  │  │ 2. Check deny rules (blacklist)                             │      │  │
│  │  │ 3. Check rate limits (sliding window)                       │      │  │
│  │  │ 4. Check live action gates (HITL for dry_run)               │      │  │
│  │  │ 5. Check execution mode constraints                         │      │  │
│  │  │                                                              │      │  │
│  │  │ → Decision: ALLOW | DENY | ESCALATE                         │      │  │
│  │  └────────────────────────────────────────────────────────────┘      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Database    │  │   Agents     │  │  Workflows   │
    │  (SQLite)    │  │   Engine     │  │   Engine     │
    └──────────────┘  └──────────────┘  └──────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AUTONOMOUS AGENTS                                   │
│                                                                               │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐             │
│  │IntakeAgent   │FulfillmentAgt│BillingAgent  │TaxAgent      │             │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤             │
│  │• Monitor     │• RAG retrieve│• Generate    │• Compute VAT │             │
│  │  requests    │• Generate    │  invoices    │• Generate    │             │
│  │• Triage      │  content     │• Apply VAT   │  reports     │             │
│  │  tickets     │• Export PDF  │• Create      │• Validate    │             │
│  │              │              │  ledger      │  compliance  │             │
│  └──────────────┴──────────────┴──────────────┴──────────────┘             │
│                                                                               │
│  ┌──────────────┬──────────────┬──────────────┐                             │
│  │PolicyAgent   │SupportAgent  │SREAgent      │                             │
│  ├──────────────┼──────────────┼──────────────┤                             │
│  │• Evaluate    │• Triage      │• Monitor     │                             │
│  │  policy      │  tickets     │  metrics     │                             │
│  │• Create HITL │• Draft       │• Detect      │                             │
│  │  requests    │  responses   │  incidents   │                             │
│  └──────────────┴──────────────┴──────────────┘                             │
│                                                                               │
│  Every agent action → Audit Event → Hash Chain                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TAMPER-EVIDENT AUDIT SYSTEM                            │
│                          runtime/audit.jsonl                                 │
│                                                                               │
│  Hash Chain Structure:                                                       │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │ Event 1    │───▶│ Event 2    │───▶│ Event 3    │───▶│ Event N    │     │
│  │ hash: abc  │    │ hash: def  │    │ hash: ghi  │    │ hash: xyz  │     │
│  │ prev: ""   │    │ prev: abc  │    │ prev: def  │    │ prev: ...  │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
│                                                                               │
│  Each event contains:                                                        │
│  • eventId: unique identifier                                                │
│  • timestamp: ISO 8601 UTC                                                   │
│  • eventType: agent_action | policy_check | system | nft                    │
│  • action: specific action taken                                             │
│  • params: input parameters                                                  │
│  • result: output (if applicable)                                            │
│  • decision: ALLOW | DENY | ESCALATE (for policy)                           │
│  • previousHash: SHA-256 of previous event (links chain)                    │
│  • eventHash: SHA-256 of this event (current link)                          │
│                                                                               │
│  Merkle Root = SHA-256(sorted([hash1, hash2, ..., hashN]))                  │
│                                                                               │
│  Guarantees:                                                                  │
│  ✓ Cannot delete events (breaks chain)                                      │
│  ✓ Cannot modify events (hash mismatch)                                     │
│  ✓ Cannot reorder events (chain order enforced)                             │
│  ✓ Cannot forge events (cryptographic hash)                                 │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTENT-ADDRESSED STORAGE (CAS)                           │
│                          runtime/cas/<hash>                                  │
│                                                                               │
│  Stores immutable artifacts addressed by SHA-256 hash:                      │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ <manifestHash>      ← Full manifest copy                            │    │
│  │ <planHash>          ← Plan lock file                                │    │
│  │ <metadataHash>      ← NFT metadata JSON                             │    │
│  │ <deliverable1Hash>  ← Generated deliverable (markdown)              │    │
│  │ <deliverable1Hash>  ← Generated deliverable (PDF)                   │    │
│  │ ...                                                                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  Properties:                                                                  │
│  ✓ Content → Hash (deterministic)                                           │
│  ✓ Hash → Content (retrievable)                                             │
│  ✓ Same content → Same hash (idempotent)                                    │
│  ✓ Different content → Different hash (tamper-evident)                      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NFT BUSINESS INSTANCE                                │
│                    ERC-721 Token on Blockchain                               │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                       NFT Metadata                                  │    │
│  │                                                                      │    │
│  │  {                                                                   │    │
│  │    "name": "OpsPilotOS Business Instance",                          │    │
│  │    "description": "Autonomous SaaS Business-in-a-Box",              │    │
│  │    "attributes": [                                                   │    │
│  │      {"trait_type": "Manifest Hash", "value": "<manifestHash>"},    │    │
│  │      {"trait_type": "Plan Hash", "value": "<planHash>"},            │    │
│  │      {"trait_type": "Audit Merkle Root", "value": "<merkleRoot>"}   │    │
│  │    ],                                                                │    │
│  │    "properties": {                                                   │    │
│  │      "manifestCAS": "<cas-hash-of-manifest>",                       │    │
│  │      "planCAS": "<cas-hash-of-plan>",                               │    │
│  │      "uapkVersion": "0.1"                                            │    │
│  │    }                                                                 │    │
│  │  }                                                                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  Stored at: runtime/cas/<metadataHash>                                      │
│  Referenced by: tokenURI = "cas://<metadataHash>"                           │
│                                                                               │
│  Blockchain:                                                                  │
│  • Development: Anvil (local testnet)                                        │
│  • Production: Ethereum mainnet/testnet                                      │
│  • Chain ID: 31337 (dev) / 1 (mainnet)                                      │
│  • Contract: OpsPilotOSBusinessInstance (ERC-721)                           │
│                                                                               │
│  Mint Command: python -m uapk.cli mint manifests/opspilotos.uapk.jsonld    │
│  Receipt: runtime/nft_mint_receipt.json                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagram

```
┌──────────────┐
│    User      │
│   (Browser   │
│  or API Key) │
└──────┬───────┘
       │
       │ POST /deliverables
       │ {title: "Cloud Architecture Report", ...}
       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Endpoint: POST /deliverables            │
│                                                               │
│  1. Extract JWT token from Authorization header              │
│  2. Validate JWT → Get current_user                          │
│  3. Check RBAC: user has "Operator" role or higher          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Policy Engine Check                        │
│                                                               │
│  PolicyEngine.evaluate(                                      │
│    agent_id="fulfillment-agent",                            │
│    action="create_deliverable",                             │
│    tool="generate_content"                                  │
│  )                                                           │
│                                                               │
│  Checks:                                                     │
│  ✓ Tool permission (fulfillment-agent → generate_content)   │
│  ✓ Deny rules (no matches)                                  │
│  ✓ Rate limits (< 100/min)                                  │
│  ✓ Live action gates (not a live action)                    │
│  ✓ Execution mode (dry_run allows this)                     │
│                                                               │
│  → Decision: ALLOW                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Create Deliverable in Database                  │
│                                                               │
│  deliverable = Deliverable(                                  │
│    project_id=1,                                            │
│    title="Cloud Architecture Report",                       │
│    status="requested",                                      │
│    created_by=user.id                                       │
│  )                                                           │
│  db.add(deliverable)                                        │
│  db.commit()                                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Trigger FulfillmentAgent (Background)              │
│                                                               │
│  background_tasks.add_task(fulfill)                          │
│                                                               │
│  async def fulfill():                                        │
│    agent = FulfillmentAgent("fulfillment-agent", manifest)  │
│    context = {                                               │
│      "deliverable_id": deliverable.id,                      │
│      "project_id": project.id,                              │
│      "title": deliverable.title,                            │
│      ...                                                     │
│    }                                                         │
│    result = await agent.execute(context)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FulfillmentAgent.execute()                      │
│                                                               │
│  Step 1: Retrieve KB context                                │
│    • Query vector store for relevant KB docs                │
│    • Get top 5 chunks related to title                       │
│                                                               │
│  Step 2: Generate content                                   │
│    • Load prompt template from manifest                      │
│    • Fill template with KB context + request details         │
│    • Generate markdown content (LLM or template)             │
│                                                               │
│  Step 3: Export to PDF                                      │
│    • Convert markdown to PDF (reportlab or simple)           │
│    • Save to artifacts/deliverables/{id}.pdf                │
│                                                               │
│  Step 4: Store in CAS                                       │
│    • Compute SHA-256 of markdown                             │
│    • Store in runtime/cas/<hash>                             │
│    • Compute SHA-256 of PDF                                  │
│    • Store in runtime/cas/<hash>                             │
│                                                               │
│  Step 5: Update database                                    │
│    • Set deliverable.status = "completed"                    │
│    • Set deliverable.content_md_hash = <hash>                │
│    • Set deliverable.content_pdf_hash = <hash>               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Audit Event Logged                         │
│                                                               │
│  audit_log.append_event(                                     │
│    event_type="agent_action",                               │
│    action="complete_fulfillment",                           │
│    agent_id="fulfillment-agent",                            │
│    params={"deliverable_id": 1},                            │
│    result={                                                  │
│      "markdown_hash": "abc123...",                          │
│      "pdf_hash": "def456...",                               │
│      "status": "completed"                                  │
│    }                                                         │
│  )                                                           │
│                                                               │
│  → Event written to runtime/audit.jsonl                     │
│  → Hash chain updated                                        │
│  → Merkle root updated                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Response to User                            │
│                                                               │
│  {                                                           │
│    "id": 1,                                                  │
│    "title": "Cloud Architecture Report",                    │
│    "status": "completed",                                   │
│    "content_md_hash": "abc123...",                          │
│    "content_pdf_hash": "def456..."                          │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Tax/VAT Calculation Flow

```
┌──────────────┐
│  User        │
│              │
└──────┬───────┘
       │
       │ POST /billing/invoices/generate
       │ {
       │   customer_country: "DE",
       │   customer_vat_id: "DE123456789",
       │   is_business: true,
       │   items: [{description: "Service", quantity: 1, unit_price: 100}]
       │ }
       ▼
┌─────────────────────────────────────────────────────────────┐
│               BillingAgent.execute()                         │
│                                                               │
│  1. Calculate subtotal                                       │
│     subtotal = Σ(item.quantity * item.unit_price)           │
│     subtotal = 100                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              TaxCalculator.calculate_vat()                   │
│                                                               │
│  Input:                                                      │
│    amount: 100                                               │
│    customer_country: "DE"                                    │
│    customer_vat_id: "DE123456789"                           │
│    is_business: true                                         │
│                                                               │
│  Decision Tree:                                              │
│  ┌─────────────────────────────────────────────────┐        │
│  │ Is country in EU? (DE is in EU)                  │        │
│  │   YES → Is business with valid VAT ID?           │        │
│  │           YES → REVERSE CHARGE                    │        │
│  │                 VAT rate: 0%                      │        │
│  │                 VAT amount: 0                     │        │
│  │                 Total: 100                        │        │
│  │                 reverse_charge: true              │        │
│  │                 reason: "EU B2B reverse charge"   │        │
│  └─────────────────────────────────────────────────┘        │
│                                                               │
│  Output:                                                     │
│    VATCalculation(                                           │
│      subtotal=100,                                           │
│      vat_rate=0.0,                                           │
│      vat_amount=0.0,                                         │
│      total=100,                                              │
│      reverse_charge=True,                                    │
│      reason="EU B2B reverse charge (DE)"                     │
│    )                                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                Create Invoice in Database                    │
│                                                               │
│  invoice = Invoice(                                          │
│    invoice_number="INV-2026-00001",                         │
│    org_id=1,                                                │
│    subtotal=100,                                            │
│    vat_rate=0.0,                                            │
│    vat_amount=0.0,                                          │
│    total=100,                                               │
│    customer_country="DE",                                   │
│    customer_vat_id="DE123456789",                          │
│    reverse_charge=True,                                     │
│    status="draft"                                           │
│  )                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Create Ledger Entries (Double-Entry)            │
│                                                               │
│  Debit:  1000 Accounts Receivable    100                    │
│  Credit: 4000 Revenue - Services     100                    │
│          (No VAT entry since reverse charge)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Response to User                            │
│                                                               │
│  {                                                           │
│    "invoice_id": 1,                                          │
│    "invoice_number": "INV-2026-00001",                      │
│    "subtotal": 100.0,                                        │
│    "vat_rate": 0.0,                                          │
│    "vat_amount": 0.0,                                        │
│    "total": 100.0,                                           │
│    "reverse_charge": true,                                   │
│    "vat_reason": "EU B2B reverse charge (DE)"               │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

**Alternative Scenarios**:

```
Scenario 2: EU B2C (or B2B without VAT ID)
  customer_country: "DE", customer_vat_id: null, is_business: false
  → VAT rate: 19% (Germany)
  → VAT amount: 19.0
  → Total: 119.0
  → reverse_charge: false

Scenario 3: Non-EU
  customer_country: "US"
  → VAT rate: 0%
  → VAT amount: 0.0
  → Total: 100.0
  → reverse_charge: false
```

---

## NFT Minting Flow

```
┌──────────────┐
│  Admin User  │
│              │
└──────┬───────┘
       │
       │ POST /nft/mint
       │ {force: false}
       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Policy Check                                │
│                                                               │
│  Execution mode: dry_run                                     │
│  Action: mint_nft                                            │
│  Is "mint_nft" in liveActionGates? YES                      │
│                                                               │
│  → Decision: ESCALATE                                        │
│  → Requires HITL approval                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Create HITL Approval Request                      │
│                                                               │
│  hitl = HITLRequest(                                         │
│    action="mint_nft",                                        │
│    reason="NFT minting requires approval in dry_run mode",  │
│    params={...},                                             │
│    status="pending"                                          │
│  )                                                           │
│                                                               │
│  Response: {                                                 │
│    "error": "NFT minting requires approval",                │
│    "approval_id": 1                                          │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Admin Approves via HITL                         │
│                                                               │
│  POST /hitl/requests/1/approve                               │
│                                                               │
│  → HITLRequest.status = "approved"                          │
│  → HITLRequest.approved_by = admin.id                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          Retry Mint with --force or Approval                 │
│                                                               │
│  python -m uapk.cli mint manifests/opspilotos.uapk.jsonld \ │
│    --force                                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                Compute Cryptographic Hashes                  │
│                                                               │
│  1. Load manifest → compute manifestHash                     │
│  2. Load plan.lock.json → compute planHash                  │
│  3. Load audit.jsonl → compute merkleRoot                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Create NFT Metadata                             │
│                                                               │
│  metadata = {                                                │
│    "name": "OpsPilotOS Business Instance",                  │
│    "attributes": [                                           │
│      {"trait_type": "Manifest Hash", "value": "<hash>"},    │
│      {"trait_type": "Plan Hash", "value": "<hash>"},        │
│      {"trait_type": "Audit Merkle Root", "value": "<hash>"}│
│    ],                                                        │
│    ...                                                       │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Store Metadata in CAS                           │
│                                                               │
│  metadata_hash = cas.put_json(metadata)                      │
│  → Stored at: runtime/cas/<metadata_hash>                   │
│  → tokenURI: "cas://<metadata_hash>"                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Mint NFT on Blockchain (Anvil/Ethereum)            │
│                                                               │
│  If Anvil running:                                           │
│    • Connect to http://localhost:8545                        │
│    • Deploy or use existing ERC-721 contract                 │
│    • Call contract.mint(to, tokenURI)                        │
│    • Get transaction receipt                                 │
│                                                               │
│  Else (simulated):                                           │
│    • Create simulated receipt                                │
│    • tokenId: 1                                              │
│    • transactionHash: 0x0000...                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Write Mint Receipt                              │
│                                                               │
│  receipt = {                                                 │
│    "contract": "0x5FbDB2315678afecb367f032d93F642f64180aa3",│
│    "tokenId": 1,                                             │
│    "chainId": 31337,                                         │
│    "metadataURI": "cas://<metadata_hash>",                  │
│    "manifestHash": "<hash>",                                │
│    "planHash": "<hash>",                                    │
│    "merkleRoot": "<hash>",                                  │
│    "transactionHash": "0x...",                              │
│    "mintedAt": "2026-02-08T12:00:00Z"                       │
│  }                                                           │
│                                                               │
│  Write to: runtime/nft_mint_receipt.json                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Audit Event Logged                             │
│                                                               │
│  audit_log.append_event(                                     │
│    event_type="nft",                                         │
│    action="mint_business_instance",                         │
│    params=metadata,                                          │
│    result=receipt                                            │
│  )                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              NFT Successfully Minted!                        │
│                                                               │
│  Business instance is now:                                   │
│  • Cryptographically identified (hashes)                     │
│  • Immutably recorded (blockchain)                           │
│  • Verifiable by anyone (public metadata)                    │
│  • Tradeable (ERC-721 standard)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

```
                        ┌────────────────┐
                        │    Manifest    │
                        │   (JSON-LD)    │
                        └────────┬───────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Agents   │ │Workflows │ │ Policy   │
              └──────┬───┘ └────┬─────┘ └────┬─────┘
                     │          │            │
                     └──────────┼────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │   Database    │
                        │   (SQLite)    │
                        └───────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Audit   │ │   CAS    │ │   NFT    │
              │   Log    │ │ Storage  │ │  Chain   │
              └──────────┘ └──────────┘ └──────────┘
```

---

**For complete technical details, refer to:**
- `UAPK_BUSINESS_INSTANCE_CERTIFICATE.md` (detailed specification)
- `BUSINESS_INSTANCE_SUMMARY.md` (executive summary)
- `README_OPSPILOTOS.md` (comprehensive guide)

---

*This architecture demonstrates the UAPK vision: a manifest-first, deterministic, tamper-evident, policy-enforced autonomous business that can be cryptographically verified and traded as an NFT.*
