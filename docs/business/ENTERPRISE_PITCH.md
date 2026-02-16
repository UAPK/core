# UAPK Gateway: Enterprise Pitch (One-Page)

**Ship autonomous AI agents without creating a compliance nightmare.**

---

## The Problem

Your team built an AI agent that could:
- Onboard customers (KYC/AML checks)
- Triage insurance claims
- Execute trades or approve transactions
- Send customer communications
- Update CRMs and case systems

**But compliance won't sign off.**

Why? Because they're asking questions you can't answer:
- "Who authorized this action?"
- "Can we stop it at runtime if something goes wrong?"
- "Can we prove exactly what happened in court?"
- "How do we audit this six months from now?"

---

## The Solution: UAPK Gateway

**A non-bypassable control plane for AI agent actions.**

Think of it as:
- **Firewall** - Policy enforcement at the action boundary
- **Black box recorder** - Tamper-evident audit logs for every decision
- **Kill switch** - Human approvals for high-risk actions
- **Budget control** - Rate limits and spend caps per agent

**Deploys on one VM. Self-hosted. No vendor lock-in.**

---

## How It Works (30 seconds)

```
┌─────────────┐
│  AI Agent   │ "Send this contract to the client"
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│      UAPK Gateway (policy layer)      │
│                                       │
│  ✓ Check: Is agent authorized?       │
│  ✓ Check: Within budget limits?      │
│  ✓ Check: Matches policy rules?      │
│  ✓ Decision: ALLOW / DENY / ESCALATE │
│  ✓ Log: Tamper-evident record        │
└──────┬───────────────────────────────┘
       │
       ▼ (if ALLOWED or APPROVED)
┌──────────────┐
│  Email API   │ Action executes
└──────────────┘
```

**Key principle:** Agents **propose** actions. Gateway **enforces** policy. Tools run with **gateway credentials**, not agent credentials.

---

## What You Get

### 1. Policy Enforcement
- Define what agents can/can't do (UAPK Manifest)
- Hard limits on budgets, rates, and scopes
- Risk hooks for external review (fraud detection, compliance engines)

### 2. Human Approvals
- Escalate high-risk actions to operators
- Web UI + API for approval workflows
- Audit trail of every approval/denial

### 3. Tamper-Evident Logs
- Every action produces an immutable interaction record
- Hash-chained log with gateway signatures
- Export bundles for auditors and regulators
- Verification scripts included

### 4. Capability Tokens
- Scoped delegation (time-limited, action-limited)
- Prevents "agent drift" and unauthorized expansion
- Cryptographically signed and verifiable

### 5. Production-Ready
- FastAPI + PostgreSQL (proven stack)
- Docker Compose deployment (one VM)
- Health checks, metrics, backups
- Self-hosted (you own the data)

---

## Who This Is For

### ✅ You should care if:
- You're shipping agents in **finance, legal, or compliance** environments
- You need a **governance story** to close enterprise deals
- Compliance keeps blocking your agent deployments
- You need **evidence-grade audit trails** for regulators or courts

### ❌ You probably don't need this if:
- Your agents only do research/summarization (no actions)
- You're in early prototyping (not production yet)
- You're fine with vendor-hosted logs and no auditability

---

## Pricing & Engagement

### Option 1: Agent Governance Pilot (2-4 weeks)
**$15K-$25K** - We implement UAPK Gateway for **one high-value workflow**

**Deliverables:**
- Production-ready manifest + guardrails
- Self-hosted gateway on your infrastructure
- Approvals flow + evidence-grade logs
- Compliance export bundle
- Rollout plan + operator training

**Timeline:** 2-4 weeks from kickoff to production

---

### Option 2: UAPK Blueprint Package
**$5K-$10K** - Design-first approach (no code yet)

**Deliverables:**
- Agent roles, actions, tools mapped
- Policy manifest + escalation thresholds
- Budget and risk hook design
- Integration architecture document

**Use case:** Get the governance design right before building

---

### Option 3: Enterprise Support
**Recurring** - After pilot or self-deployment

- Custom connectors (Salesforce, M365, internal APIs)
- Compliance export tuning (SOC2, GDPR, etc.)
- SLA + on-call support
- Version upgrades and security patches

---

## Why Now?

**Agentic AI is moving from demos to production.**

- OpenAI Swarm, Anthropic MCP, LangChain agents are shipping to customers
- Enterprise buyers want agents but need **governance, audit, and control**
- Compliance teams are the new gatekeepers
- UAPK Gateway gives you the "yes, but safely" answer

**Model vendors will improve tool-calling.** But they won't solve:
- Non-bypassable enforcement at your boundary
- Organization-owned evidence (not vendor retention logs)
- Cross-model, cross-vendor governance standards

---

## Risk Mitigation

### "What if agents just bypass the gateway?"
**Answer:** In production, tools run with credentials **controlled by the gateway**. Agents don't have direct access. This is enforced at the infrastructure level.

### "What if the gateway becomes a bottleneck?"
**Answer:** Designed for < 100ms p99 latency. Horizontal scaling supported (multi-instance + shared Postgres). Most actions are async (approval flows don't block the agent).

### "What if we need custom connectors?"
**Answer:** Open connector framework. We provide HTTP, webhook, and mock out of the box. Custom connectors are part of the pilot or support engagement.

### "What if compliance requirements change?"
**Answer:** Policies are versioned and stored in manifests. Update the manifest, re-activate, and the new rules apply immediately. Full history is logged.

---

## Next Steps

### 1. Schedule a 30-minute discovery call
We'll discuss:
- Your agent use cases
- Compliance requirements
- Integration points
- Pilot scope and timeline

### 2. Technical review (optional)
Our solutions team reviews your architecture and provides:
- Integration feasibility assessment
- Security and compliance notes
- Recommended pilot approach

### 3. Pilot proposal
We deliver:
- Custom pilot plan
- Timeline and deliverables
- Pricing (fixed-fee, no surprises)

### 4. Kickoff in < 1 week
Pilots start fast. Most customers go live in 2-4 weeks.

---

## Contact

**Commercial inquiries:**
- GitHub: Open an issue labeled `commercial` at https://github.com/UAPK/core/issues
- Email: See `SECURITY.md` for contact details

**Open source:**
- Repo: https://github.com/UAPK/core
- Docs: See `docs/` directory
- License: Apache-2.0 (self-hostable, no strings attached)

---

## The Pitch in One Sentence

**UAPK Gateway lets you deploy autonomous AI agents with the guardrails, audit trails, and kill switches that compliance teams demand — self-hosted, on one VM, in production in 2-4 weeks.**

---

*This is a commercial offering built on open-source foundations. The code is Apache-2.0. The support, connectors, and blueprints are how we make money. Transparent by design.*
