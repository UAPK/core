# 🚀 Client Implementation Guide - UAPK Gateway

**How clients deploy UAPK Gateway for their AI agent workflows**

---

## 📋 Client Scenario

**Client Profile:**
- Has existing software/business
- Wants to add AI agents to their workflow
- Needs governance/compliance for agent actions
- Wants to deploy UAPK Gateway

**Example:** Law firm with case management system wants to add settlement negotiation agents

---

## 🎯 IMPLEMENTATION OPTIONS

### **Option 1: Pilot Program ($15K-$25K)**
**You implement everything for them**

**What you deliver:**
- UAPK Gateway deployed on their infrastructure
- Manifests configured for their use case
- Agents integrated with gateway
- Policies and approval workflows set up
- Training for their operators
- 30 days support

**Timeline:** 2-4 weeks

### **Option 2: Self-Hosted (Free)**
**They do it themselves using open source**

**What they get:**
- GitHub repository access
- Documentation and guides
- Community support
- They handle all implementation

**Timeline:** Varies (weeks to months)

### **Option 3: Hybrid**
**Blueprint ($5K-$10K) + they implement**

**What you deliver:**
- Governance design document
- UAPK Manifests drafted
- Integration architecture
- Implementation roadmap

**They handle:**
- Actual deployment
- Technical integration
- Testing and operations

---

## 🏗️ TECHNICAL ARCHITECTURE

### **How UAPK Gateway Fits In Their System**

```
┌─────────────────────────────────────────────┐
│ CLIENT'S EXISTING SYSTEM                     │
│                                              │
│ ┌──────────────┐      ┌──────────────┐     │
│ │ Their Web App│      │ Their Database│     │
│ └──────────────┘      └──────────────┘     │
│         │                      │            │
│         └──────┬───────────────┘            │
│                │                            │
│         ┌──────▼──────────┐                │
│         │  AI Agent       │                │
│         │  (Their Code)   │                │
│         └──────┬──────────┘                │
└────────────────┼─────────────────────────────┘
                 │
                 │ Action Request
                 │ (HTTP POST)
                 ▼
        ┌────────────────────┐
        │  UAPK GATEWAY      │◄─── YOU DEPLOY THIS
        │  (Enforcement)     │
        └────────┬───────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    ┌─────────┐     ┌──────────┐
    │ ALLOW?  │     │ Audit Log│
    │ DENY?   │     │ (Tamper- │
    │ ESCALATE│     │ Evident) │
    └────┬────┘     └──────────┘
         │
         │ If ALLOW
         ▼
    ┌────────────────┐
    │ Execute Action │
    │ (Connector)    │
    └────────────────┘
```

**Key Point:** Client's agents send action requests to UAPK Gateway, NOT directly to tools/APIs

---

## 📖 IMPLEMENTATION STEPS (Pilot Program)

### **Phase 1: Discovery & Design (Week 1)**

**You work with client to:**

1. **Map their workflow:**
   - What agents are they building?
   - What actions will agents take?
   - What tools/APIs will agents use?

**Example (Settlement Agent):**
   ```
   Agent: settlement-negotiator
   Actions:
   - send_settlement_offer (low risk)
   - accept_counteroffer (medium risk)
   - sign_settlement (high risk - needs approval)
   Tools:
   - Email API
   - DocuSign connector
   - Case management system API
   ```

2. **Define policies:**
   - What's automatically allowed?
   - What needs approval?
   - What's denied?

**Example:**
   ```
   ALLOW: Settlements ≤ $10K
   ESCALATE: Settlements $10K-$50K (partner approval)
   DENY: Settlements > $50K (too risky for agent)
   ```

3. **Design manifest:**
   - Create UAPK Manifest YAML/JSON
   - Define agent roles and capabilities
   - Set budgets and rate limits

**Deliverable:** UAPK Manifest (draft) + Architecture doc

---

### **Phase 2: Deployment (Week 2)**

**You deploy UAPK Gateway to client's infrastructure:**

#### **Step 1: Choose Deployment Location**

**Option A: Client's Existing VM/Server**
```bash
# On their server:
git clone https://github.com/UAPK/core.git
cd core
make prod-deploy
```

**Option B: New VM (GCP/AWS/Azure)**
```bash
# Provision VM
# Install Docker + PostgreSQL
# Deploy UAPK Gateway
# Configure firewall
```

**Option C: Docker Compose (Simplest)**
```bash
# On their infrastructure:
docker-compose up -d
# Gateway + PostgreSQL bundled
```

#### **Step 2: Configure for Client**

**Create `.env` file:**
```bash
# Database
DATABASE_URL=postgresql://...their-db...

# Security keys (generate fresh)
SECRET_KEY=$(openssl rand -hex 32)
GATEWAY_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Their settings
ENVIRONMENT=production
GATEWAY_DEFAULT_DAILY_BUDGET=1000
GATEWAY_ALLOWED_WEBHOOK_DOMAINS=["their-domain.com"]
```

#### **Step 3: Upload Manifest**

**Via API:**
```bash
# Create organization
curl -X POST http://gateway:8000/api/v1/orgs \
  -d '{"name": "Acme Law", "slug": "acme"}'

# Upload manifest
curl -X POST http://gateway:8000/api/v1/manifests \
  -H "X-API-Key: $ADMIN_KEY" \
  -d @settlement-agent-manifest.json
```

**Manifest Example:**
```json
{
  "uapk_id": "settlement-negotiator",
  "version": "1.0.0",
  "organization_id": "...",
  "agent": {
    "name": "Settlement Negotiation Agent",
    "roles": ["negotiator", "settlement_drafter"]
  },
  "capabilities": {
    "allowed_actions": [
      "send_settlement_offer",
      "review_counteroffer",
      "draft_settlement_terms"
    ]
  },
  "policies": {
    "settlement_value_cap": 50000,
    "daily_settlement_cap": 100000,
    "require_approval_above": 10000
  },
  "connectors": {
    "email": {
      "type": "http",
      "endpoint": "https://api.sendgrid.com/v3/mail/send"
    },
    "docusign": {
      "type": "http",
      "endpoint": "https://docusign.com/api/sign"
    }
  }
}
```

**Deliverable:** Gateway deployed, manifest active

---

### **Phase 3: Agent Integration (Week 2-3)**

**Client modifies their agent code to use UAPK Gateway:**

#### **Before (Without UAPK):**

```python
# Client's old code - agent directly calls tools
async def negotiate_settlement(case_id, amount):
    # Direct call - NO GOVERNANCE!
    result = await sendgrid.send_email(
        to=opposing_counsel,
        subject="Settlement Offer",
        body=f"We offer ${amount}"
    )
    return result
```

**Problems:**
- ❌ No policy enforcement
- ❌ No audit trail
- ❌ No approval workflow
- ❌ Compliance can't approve

#### **After (With UAPK):**

```python
# Client's new code - agent proposes to gateway
async def negotiate_settlement(case_id, amount):
    # 1. Agent proposes action to gateway
    action_request = {
        "uapk_id": "settlement-negotiator",
        "action": {
            "type": "settlement_offer",
            "tool": "send_email",
            "params": {
                "case_id": case_id,
                "amount": amount,
                "recipient": opposing_counsel
            }
        },
        "context": {
            "case_type": "ip_infringement",
            "settlement_value": amount
        }
    }

    # 2. POST to gateway
    response = await http_client.post(
        "http://uapk-gateway:8000/api/v1/gateway/evaluate",
        headers={"X-API-Key": GATEWAY_API_KEY},
        json=action_request
    )

    # 3. Gateway responds with decision
    if response.json()["decision"] == "ALLOW":
        # Gateway executed it via connector
        return response.json()["result"]
    elif response.json()["decision"] == "DENY":
        raise Exception(f"Gateway denied: {response.json()['reason']}")
    elif response.json()["decision"] == "ESCALATE":
        # Wait for human approval
        approval_id = response.json()["approval_id"]
        return await wait_for_approval(approval_id)
```

**Benefits:**
- ✅ Policy enforcement (Gateway checks amount vs cap)
- ✅ Audit trail (Interaction record created)
- ✅ Approval workflow (if amount > $10K)
- ✅ Compliance-ready

#### **Integration Points:**

**Client needs to modify:**
1. **Agent code** - POST to gateway instead of direct tool calls
2. **API keys** - Store gateway API key securely
3. **Error handling** - Handle DENY and ESCALATE responses
4. **Approvals UI** - Link to gateway approval dashboard (or use yours)

**You provide:**
- SDK examples (Python, JavaScript)
- Integration templates
- Testing tools
- Sample code

**Deliverable:** Agent integrated and calling gateway

---

### **Phase 4: Testing & Validation (Week 3)**

**You work with client to test:**

1. **Happy Path:**
   ```
   Agent proposes: Settlement offer $5K
   Gateway: ALLOW (under $10K cap)
   Result: Email sent via connector
   Audit log: Created with hash chain
   ```

2. **Approval Flow:**
   ```
   Agent proposes: Settlement offer $15K
   Gateway: ESCALATE (over $10K cap)
   Partner: Reviews in dashboard
   Partner: Approves
   Gateway: Executes action
   Audit log: Records approval + action
   ```

3. **Denial:**
   ```
   Agent proposes: Settlement $60K
   Gateway: DENY (over $50K hard cap)
   Agent: Receives denial
   Audit log: Records attempted action + denial
   ```

4. **Audit Verification:**
   ```
   Export audit log
   Verify hash chain
   Confirm signatures
   Check tamper-evidence
   ```

**Deliverable:** All test cases passing

---

### **Phase 5: Production Deployment (Week 4)**

**Move from staging to production:**

1. **Production checklist:**
   - [ ] Fresh security keys generated
   - [ ] Production database configured
   - [ ] Backups automated
   - [ ] Monitoring set up
   - [ ] SSL certificates installed
   - [ ] Firewall rules configured
   - [ ] Approval workflows tested
   - [ ] Operator training complete

2. **Go-live:**
   - Deploy to production environment
   - Update agent code to production gateway URL
   - Monitor first few interactions
   - Verify audit logs

3. **Training:**
   - 2-hour operator training session
   - How to approve/deny actions
   - How to export audit logs
   - How to troubleshoot

**Deliverable:** Production deployment + trained operators

---

## 🎯 WHAT CLIENT GETS

### **Infrastructure (Self-Hosted on Their Systems)**

**Deployed Components:**
- UAPK Gateway service (FastAPI)
- PostgreSQL database
- Operator dashboard (web UI)
- API endpoints

**They own and control:**
- All data
- All audit logs
- All infrastructure
- All credentials

### **Configuration**

**UAPK Manifest:**
- Their agent definitions
- Policy rules
- Approval workflows
- Budget caps
- Connector configurations

**Policies:**
- What actions are allowed
- When to require approval
- Risk thresholds
- Rate limits

### **Integration**

**Agent Code:**
- Modified to call gateway
- Error handling
- Approval waiting logic

**Connectors:**
- Email (SendGrid, etc.)
- APIs (their internal systems)
- Webhooks
- Custom tools

### **Operations**

**Operator Dashboard:**
- Approve/deny pending actions
- View audit trail
- Export compliance reports
- Monitor agent activity

**Runbooks:**
- How to operate the gateway
- Troubleshooting guide
- Incident response
- Compliance export procedures

---

## 💼 TYPICAL IMPLEMENTATION TIMELINE

### **Week 1: Discovery**
- **Your time:** 10-15 hours
- **Client time:** 5-8 hours
- **Meetings:** 2-3 sessions
- **Deliverables:** Manifest draft, architecture doc

### **Week 2: Deployment**
- **Your time:** 15-20 hours
- **Client time:** 5-10 hours (DevOps support)
- **Meetings:** 2-3 check-ins
- **Deliverables:** Gateway deployed, manifest uploaded

### **Week 3: Integration**
- **Your time:** 10-15 hours
- **Client time:** 15-20 hours (their devs modify agent code)
- **Meetings:** Daily standups (15 min)
- **Deliverables:** Agent integrated, tests passing

### **Week 4: Production**
- **Your time:** 5-10 hours
- **Client time:** 5 hours
- **Meetings:** Go-live review, training session
- **Deliverables:** Production deployment, trained operators

**Total Your Time:** 40-60 hours
**Total Client Time:** 30-40 hours
**Cost to Client:** $15K-$25K (fixed fee)
**Value to Client:** $150K+ (vs building themselves)

---

## 🔧 CLIENT'S DEPLOYMENT OPTIONS

### **Option A: Their Existing Infrastructure**

**If client has:**
- VM or server (Linux)
- PostgreSQL database
- Docker (optional)

**You deploy:**
```bash
# On their server
ssh client-server

# Install UAPK Gateway
git clone https://github.com/UAPK/core.git uapk-gateway
cd uapk-gateway

# Configure
cp .env.example .env.production
# Edit with their settings

# Deploy
make prod-deploy

# Verify
curl http://localhost:8000/healthz
```

**Pros:**
- Uses their existing infrastructure
- No new costs
- They control everything

**Cons:**
- Requires their DevOps support
- May need security reviews

---

### **Option B: New Dedicated VM**

**You provision:**
- GCP/AWS/Azure VM ($50-100/month)
- Ubuntu 22.04 LTS
- 4 CPU, 16GB RAM
- PostgreSQL installed

**You deploy:**
```bash
# Automated script
./scripts/deploy/deploy-to-production.sh

# Or manual
docker-compose -f docker-compose.prod.yml up -d
```

**Pros:**
- Clean, dedicated environment
- Full control over configuration
- Easy to manage

**Cons:**
- Additional $50-100/month cost
- Client needs to manage VM

---

### **Option C: Containerized (Docker Compose)**

**Simplest deployment:**

```yaml
# docker-compose.yml
version: '3.8'
services:
  gateway:
    image: uapk/gateway:latest
    environment:
      - DATABASE_URL=postgresql://...
      - SECRET_KEY=...
    ports:
      - "8000:8000"

  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Command:**
```bash
docker-compose up -d
```

**Pros:**
- Fastest deployment (5 minutes)
- Easy updates (pull new image)
- Portable across clouds

**Cons:**
- Requires Docker knowledge
- Container overhead

---

## 🔌 AGENT INTEGRATION PATTERNS

### **Pattern 1: SDK Integration (Easiest)**

**Python SDK:**
```python
from uapk_gateway import GatewayClient

# Client's agent code
client = GatewayClient(
    base_url="http://uapk-gateway:8000",
    api_key="client-api-key-here",
    uapk_id="settlement-negotiator"
)

# Agent proposes action
async def negotiate_settlement(case_id, amount):
    result = await client.execute_action(
        action_type="settlement_offer",
        tool="send_email",
        params={
            "case_id": case_id,
            "amount": amount,
            "template": "settlement_offer"
        }
    )

    if result.decision == "ALLOW":
        return result.data
    elif result.decision == "ESCALATE":
        # Wait for approval
        return await client.wait_for_approval(result.approval_id)
    else:
        raise Exception(f"Denied: {result.reason}")
```

**You provide:**
- Python SDK (already exists in `/sdks/python/`)
- JavaScript SDK
- Integration examples

---

### **Pattern 2: Direct API Integration**

**Client calls REST API directly:**

```typescript
// Client's TypeScript agent code
async function proposeSettlement(caseId: string, amount: number) {
  const response = await fetch('http://uapk-gateway:8000/api/v1/gateway/evaluate', {
    method: 'POST',
    headers: {
      'X-API-Key': 'client-api-key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      uapk_id: 'settlement-negotiator',
      action: {
        type: 'settlement_offer',
        tool: 'send_email',
        params: { caseId, amount }
      }
    })
  });

  const decision = await response.json();

  if (decision.decision === 'ALLOW') {
    return decision.result;
  } else if (decision.decision === 'ESCALATE') {
    // Poll for approval
    return await waitForApproval(decision.approval_id);
  } else {
    throw new Error(`Denied: ${decision.reason}`);
  }
}
```

---

### **Pattern 3: Webhook Connectors**

**For tools client's agents use:**

```yaml
# In manifest
connectors:
  sendgrid:
    type: http
    endpoint: https://api.sendgrid.com/v3/mail/send
    auth:
      type: bearer
      secret_ref: sendgrid_api_key

  docusign:
    type: http
    endpoint: https://docusign.com/api/sign
    auth:
      type: oauth
      secret_ref: docusign_oauth_token
```

**Gateway acts as proxy:**
- Stores secrets securely
- Enforces policies before calling tools
- Logs all interactions
- Returns results to agent

---

## 📚 WHAT YOU DELIVER TO CLIENT

### **Technical Deliverables:**

1. **Deployed Gateway**
   - Running on their infrastructure
   - Health checks passing
   - API accessible

2. **UAPK Manifest**
   - Agent definitions
   - Policy rules
   - Connectors configured
   - Validated and uploaded

3. **Integration Code**
   - Agent code modifications
   - SDK usage examples
   - Error handling patterns
   - Testing scripts

4. **Operator Dashboard**
   - Web UI deployed
   - Approval workflows configured
   - Audit log viewer
   - Export functionality

5. **Documentation**
   - Architecture diagram
   - API reference
   - Operator runbook
   - Troubleshooting guide
   - Compliance export procedures

### **Training Deliverables:**

6. **Operator Training** (2 hours)
   - How to review approval requests
   - How to approve/deny actions
   - How to export audit logs
   - How to verify hash chains
   - Emergency procedures

7. **Developer Handoff**
   - Integration patterns explained
   - Testing procedures
   - Deployment playbook
   - Monitoring setup

### **Post-Pilot:**

8. **30 Days Support**
   - Bug fixes
   - Configuration adjustments
   - Questions answered
   - Monitoring assistance

---

## 💰 COST BREAKDOWN (For Your Pricing)

**Your Time Investment:**
- Discovery & design: 12 hours
- Deployment & config: 18 hours
- Integration support: 12 hours
- Testing & validation: 8 hours
- Production go-live: 5 hours
- Training & docs: 5 hours
**Total: 60 hours**

**Your Pricing:**
- $15K-$25K fixed fee
- = $250-$417/hour
- Premium rate justified by expertise

**Client's Savings vs Alternatives:**
- Big 4 consulting: $150K-$300K
- Build themselves: $120K-$170K + 6 months
- Your pilot: $20K + 3 weeks
- **Savings: $100K-$280K**

---

## 🎯 ONGOING CLIENT RELATIONSHIP

### **After Pilot Completes:**

**Option 1: Self-Managed (Open Source)**
- Client operates gateway themselves
- You provide no ongoing support
- They can modify as needed
- Cost: $0/month

**Option 2: Enterprise Support Contract**
- $3K-$10K/month recurring
- Priority bug fixes
- Security updates
- Additional connectors
- SLA (4-hour response)
- Dedicated support channel

**Option 3: Additional Pilots**
- Client has more workflows
- $15K-$25K per additional agent
- Reuse existing gateway
- Add new manifests

---

## 📋 CLIENT REQUIREMENTS CHECKLIST

**What client needs to provide:**

### **Infrastructure Access:**
- [ ] VM or server (SSH access)
- [ ] PostgreSQL database (or provision new)
- [ ] Domain name (optional, for SSL)
- [ ] Firewall rules (allow port 8000)

### **Technical Support:**
- [ ] DevOps engineer (5-10 hours for deployment)
- [ ] Developer(s) (15-20 hours for agent integration)
- [ ] Security review (if required by their policies)

### **Business Information:**
- [ ] Use case details (what agents do)
- [ ] Compliance requirements (SOC2, GDPR, etc.)
- [ ] Risk tolerance (approval thresholds)
- [ ] Existing tools/APIs agents will use

### **Approval:**
- [ ] Budget approved ($15K-$25K)
- [ ] Timeline agreed (2-4 weeks)
- [ ] Stakeholders identified (who approves agents?)
- [ ] Success criteria defined

---

## 🚀 QUICK START FOR CLIENT

**If client wants to evaluate before pilot:**

```bash
# 1. Try open source locally (5 minutes)
git clone https://github.com/UAPK/core.git
cd core
make dev

# 2. Open dashboard
open http://localhost:8000

# 3. Try demo
make demo

# 4. Read docs
open http://localhost:8000/docs
```

**Then decide:**
- Self-implement (free, takes months)
- Pilot program (fast, expert help)
- Blueprint (design first)

---

## 📧 SAMPLE CLIENT EMAIL

**When client asks "What do we need to do?"**

---

**Subject:** UAPK Gateway Implementation - Next Steps

Hi [Client Name],

Great to hear you're moving forward with the pilot! Here's what happens next:

**What I'll Do:**
1. Deploy UAPK Gateway on your infrastructure (or new VM)
2. Create governance manifest for your [settlement agent]
3. Configure policies and approval workflows
4. Integrate with your agent code
5. Test end-to-end
6. Train your operators
7. Support for 30 days after go-live

**What You'll Need:**
1. Access to a VM/server (or I can provision one - $50/month)
2. ~20 hours from one of your developers (for agent integration)
3. ~5 hours from your DevOps (for deployment support)
4. Stakeholder availability (for policy decisions)

**Timeline:**
- Week 1: Discovery calls + manifest design
- Week 2: Gateway deployment
- Week 3: Agent integration
- Week 4: Testing + production go-live

**Kickoff:** [Proposed date]

**Next Step:** 30-minute kickoff call to review your specific use case and finalize architecture.

[Calendar link]

Best regards,
[Your Name]
Lawyer & Developer, UAPK Gateway

---

**Does this answer your question about client delivery?**

The key insight: **Clients don't "use" UAPK Gateway directly - you deploy and configure it FOR them as a service.**

Would you like me to create templates for:
- Client onboarding questionnaire?
- Pilot Statement of Work (SOW)?
- Technical handoff documentation?