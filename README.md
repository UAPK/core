# UAPK Gateway
**The agent firewall + black box recorder for high‑stakes AI.**
Deploy autonomous AI agents with **hard guardrails**, **human approvals**, and **tamper‑evident audit logs** — on **one VM**, self‑hosted.

> Agents don't "do" things directly. They **propose actions**.
> UAPK Gateway enforces **policy, permissions, budgets, risk hooks**, and produces **evidence‑grade interaction records** for auditors, regulators, and courts.

---

## Why this exists

Agentic AI is moving from "chat" to "action":

- sending emails and messages
- writing into CRMs and case systems
- onboarding customers (KYC)
- underwriting and claims triage
- proposing trades / executing workflows

The moment agents touch **money, legal outcomes, privileged systems, or regulated data**, organizations hit the same wall:

- **"Who authorized this?"**
- **"Can we stop it at runtime?"**
- **"Can we prove exactly what happened later?"**
- **"How do we deploy this without creating a compliance nightmare?"**

UAPK Gateway is a **control plane** for agent actions — designed for **legal, finance, and compliance** environments.

---

## What UAPK Gateway is

UAPK Gateway is a **single deployable service** (FastAPI + Postgres) that sits between agents and the outside world.

It provides:

- **Policy enforcement** (ALLOW / DENY / ESCALATE)
- **Capability tokens** (scoped delegation)
- **Budgets & rate caps** (per day/per entity)
- **Human‑in‑the‑loop approvals**
- **Tamper‑evident logging** (hash chaining + signatures)
- **Compliance exports** (audit bundles)
- **Connector framework** (webhooks, HTTP, and custom tools)
- Optional **AI-assisted helpers** (manifest scaffolding, log summaries) with safe defaults

### What it is not (v0.1)
- Not a "do everything business compiler" yet
- Not tied to one model vendor or one agent framework
- Not a crypto/NFT-first pitch (tokenization can be layered later as provenance)

---

## Who it's for

### Teams shipping "agentic" workflows
- Law firms and litigation boutiques (IP enforcement, claims, settlements)
- Banks, fintechs, and insurers (KYC/onboarding, underwriting, internal copilots)
- Compliance and risk teams trying to approve agent deployments
- AI product teams who need a **governance story** to close enterprise deals

### If you're in any of these situations, you're the target
- "Our agent can do X, but compliance won't sign off."
- "We need approvals for certain actions."
- "We need audit trails that survive scrutiny."
- "We want to deploy agents, but safely and repeatably."

---

## Architecture

```mermaid
flowchart LR
  A[Agent / Tool-Using Workflow] -->|Action Request| G[UAPK Gateway]
  G -->|ALLOW| T[Tool Connector: Webhook/HTTP/Custom]
  G -->|DENY| A
  G -->|ESCALATE| H[Human Approver UI/API]
  H -->|Approve/Deny| G
  G --> L[(Tamper-Evident Interaction Log)]
  G --> M[(Manifests + Policies + Keys)]
  G --> R[Risk Hook (QIRE-lite / external)]
```

**Key design principle:** the gateway is the **non-bypassable enforcement point**.
In production, tools run with credentials controlled by the gateway — not by the agent.

---

## Core concepts (the "UAPK" model)

### 1) UAPK Manifest

A versioned JSON/YAML document defining an "autonomous entity" boundary:

* identity (`uapk_id`, org scope)
* agent roles
* allowed actions/tools
* caps and escalation thresholds
* budgets
* tool registry (connectors)
* logging requirements
* optional risk hook configuration

### 2) Capability Tokens

Signed tokens that delegate scoped authority:

* allowlists for actions/tools
* max amounts
* jurisdictions / counterparties constraints
* expiry, delegation depth
* used to prevent agent drift

### 3) Interaction Records

Every attempted action produces an immutable record:

* request/result hashes
* decision and reasons
* policy evaluation trace (structured)
* approvals (if any)
* hash-chain + gateway signature

This is your "black box recorder."

---

## Quickstart (one VM)

> You can run this locally or on a single VM using Docker Compose.

### 1) Configure environment

```bash
cp .env.example .env
# Edit .env if needed (dev-safe defaults)
```

### 2) Start services

```bash
make dev
# or:
docker compose up -d --build
```

### 3) Migrate database

```bash
make migrate
# or:
docker compose exec backend alembic upgrade head
```

### 4) Create admin user and organization

```bash
make bootstrap
# or:
docker compose run --rm bootstrap
```

This creates:
- **Admin user**: `admin@example.com` / `changeme123`
- **Organization**: "Default Organization" (slug: `default`)

### 5) Check health

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
```

### 6) Access the gateway

- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login**: Use the admin credentials from step 4

---

## VM Transformator MVP

Transform your VM into a **UAPK Compiler/Transformator node** for compiling business templates, packaging instances, and minting NFTs.

### 7-Command Workflow

#### 1. Compile - Convert templates to instances

```bash
python3 -m uapk.cli compile templates/minimal_business.template.jsonld \
  --params templates/example_vars.yaml \
  --out /var/lib/uapk/instances/my-business
```

#### 2. Plan - Generate deterministic execution plan

```bash
python3 -m uapk.cli plan /var/lib/uapk/instances/my-business/manifest.jsonld \
  --lock plan.lock.json
```

#### 3. Package - Create CAS-indexed bundle

```bash
python3 -m uapk.cli package /var/lib/uapk/instances/my-business --format zip
```

#### 4. Chain - Start local blockchain

```bash
python3 -m uapk.cli chain up
```

#### 5. Deploy - Deploy NFT contract

```bash
python3 -m uapk.cli nft deploy --network local
```

#### 6. Mint - Mint business instance NFT (with approval)

```bash
# Request mint
python3 -m uapk.cli mint /var/lib/uapk/instances/my-business \
  --network local --require-approval

# Approve request
python3 -m uapk.cli hitl approve <request-id>

# Mint with override token
python3 -m uapk.cli mint /var/lib/uapk/instances/my-business \
  --network local --override-token <token>
```

#### 7. Run - Execute the instance

```bash
python3 -m uapk.cli run --instance my-business
```

### Quick Start

Run the complete E2E demo:

```bash
./scripts/e2e_vm_transformator_demo.sh
```

### Full Documentation

See [VM Transformator MVP Deployment Guide](docs/deployment/vm_transformator_mvp.md) for:
- Prerequisites and installation
- Environment configuration
- Systemd service setup
- Troubleshooting
- Architecture details

---

## Demo in 60 seconds

Load example manifests ("47ers") and run a simulated tool call.

```bash
make demo
# or:
python scripts/load_example_manifests.py
```

Then follow the printed `curl` commands to:

* create API keys
* validate and activate a manifest
* call `/v1/gateway/evaluate`
* call `/v1/gateway/execute`
* trigger approval flows
* export logs and verify the chain

---

## API overview

### Human auth

* `POST /api/v1/auth/login` - Login with email/password
* `GET  /api/v1/auth/me` - Get current user info

### Organizations & API keys

* `POST /api/v1/orgs` - Create organization
* `GET  /api/v1/orgs` - List user's organizations
* `POST /api/v1/users` - Create user
* `POST /api/v1/orgs/{org_id}/memberships` - Add user to org
* `POST /api/v1/api-keys` - Create API key (machine auth)
* `GET  /api/v1/api-keys` - List API keys
* `POST /api/v1/api-keys/{id}/revoke` - Revoke API key

### Manifests

* `POST /api/v1/manifests/validate` - Validate manifest
* `POST /api/v1/manifests` - Store manifest
* `GET  /api/v1/manifests` - List manifests
* `GET  /api/v1/manifests/{id}` - Get manifest details
* `POST /api/v1/manifests/{id}/activate` - Activate manifest
* `POST /api/v1/manifests/{id}/archive` - Archive manifest

### Gateway

* `POST /api/v1/gateway/evaluate` - Evaluate action (dry run, API key)
* `POST /api/v1/gateway/execute` - Execute action (real run, API key)

### Approvals

* `GET  /api/v1/approvals` - List pending approvals
* `POST /api/v1/approvals/{id}/approve` - Approve action
* `POST /api/v1/approvals/{id}/deny` - Deny action

### Audit logs

* `GET  /api/v1/logs` - List interaction records
* `POST /api/v1/logs/export` - Export audit bundle
* `GET  /api/v1/logs/{id}/verify` - Verify chain integrity

### Health

* `GET  /healthz` - Liveness probe
* `GET  /readyz` - Readiness probe

Full reference: see `docs/` and `/docs` OpenAPI in the running service.

---

## Operator UI

A minimal operator UI is included (FastAPI + Jinja2 + HTMX):

* view manifests
* manage API keys
* approve escalations
* browse logs

This keeps v0.1 **one-service** and **one-VM**.

---

## The "47ers" library (micro‑SaaS starter kits)

This repo includes small, focused templates that are ready to deploy as micro‑services:

* **legal**: settlement gate, takedown gate
* **compliance**: KYC onboarding gate, vendor due diligence gate
* **finance**: trading execution gate
* **general**: outbound email guard

See: `examples/47ers/` and the docs page "47ers Library".

**Strategy:** each 47er is a sellable unit (a practical UAPK manifest) that runs on the same gateway.

---

## Why this won't be obsolete with the next model update

UAPK Gateway is **model‑agnostic** and **vendor‑agnostic**:

* It governs **actions** at the boundary to real systems
* It integrates with your existing IAM, secrets, logging, and approvals
* It produces **organization‑owned evidence** (not vendor-retention logs)

Model vendors can improve tracing and tool primitives — but regulated orgs still need:

* non-bypassable enforcement
* consistent cross-model governance
* audit and retention under their own policies

---

## Commercial offering (how to buy this)

This repo is open and self‑hostable.

If you want fast results in a real environment, the preferred engagement is:

### 1) Agent Governance Pilot (2–4 weeks)

We implement UAPK Gateway for **one** high-value workflow and deliver:

* a production-ready manifest + guardrails
* a running self-hosted gateway on your infra
* an approvals flow and evidence-grade logs
* a compliance export bundle and rollout plan

**Pricing**: Contact for details (see `docs/business/pilot.md`)

### 2) UAPK Blueprint Package

For teams that want the "manifest + policy pack" first:

* map roles, actions, tools, escalation thresholds, budgets
* deliver a validated manifest + templates + integration notes

### 3) Support / connectors / policy packs

* connectors to your internal systems
* compliance exports tuned to your audit requirements
* SLA and operational support

**Contact:** open a GitHub issue labeled `commercial` or email the maintainer (see `SECURITY.md`).

---

## Sales & marketing strategy (transparent, by design)

This project grows by:

* **Open standards + reference implementation** (trust and adoption)
* **Templates ("47ers")** that demonstrate immediate value
* **Productized pilots** (fast time-to-value, low procurement friction)
* **Enterprise hardening + support** (where recurring revenue lives)

---

## Security & compliance

UAPK Gateway is designed for high-stakes environments:

* capability-scoped authorization
* secrets stored encrypted (Fernet key from env)
* strict connector allowlists (for HTTP tools)
* tamper-evident logs (hash chain + signatures)
* safe AI defaults (mock provider, sensitive data disabled)

See:

* `SECURITY.md` for reporting and threat model notes
* `docs/security/` for deployment and hardening guidance

**Disclaimer:** This software is not legal advice. You are responsible for ensuring compliance with applicable laws and regulations.

---

## Development

### Local dev

```bash
make dev
```

### Tests

```bash
make test        # Run in Docker
make test-local  # Run locally (requires Python deps)
```

### Lint & format

```bash
make lint
make format
make typecheck
```

### Full self-check

```bash
bash scripts/self_check.sh
# Optional E2E:
RUN_E2E=1 bash scripts/e2e_smoke.sh
```

### Documentation

```bash
make docs        # Serve docs locally
make docs-build  # Build static docs
```

---

## Roadmap (high-level)

* More connectors (M365, Slack, Salesforce, S3/GCS, case systems)
* Stronger policy language (still deterministic & auditable)
* Risk providers (QIRE-lite → QIRE module)
* Better export bundles (PDF packs + evidence timelines)
* Standardization of agent-to-agent interaction formats
* Multi-gateway federation (cross-org workflows)

See `docs/roadmap.md`.

---

## Contributing

Contributions are welcome:

* improvements to schemas/specs
* connectors and 47er templates
* hardening and testing
* docs and examples

Start with `docs/development/contributing.md`.

---

## License

Apache-2.0 — see `LICENSE`.

---

## Technology Stack

- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **UI**: Jinja2 + HTMX (server-rendered)
- **Auth**: JWT for humans, API keys for machines
- **Deployment**: Docker Compose (dev & production)
- **Testing**: pytest with async support
- **Code Quality**: ruff, mypy, pre-commit hooks

---

## Support

- **Documentation**: See `docs/` or http://localhost:8000/docs when running
- **Issues**: https://github.com/UAPK/core/issues
- **Commercial inquiries**: Label issues with `commercial`
- **Security reports**: See `SECURITY.md`
