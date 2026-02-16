# Statement of Work - UAPK Gateway Pilot Implementation

**UAPK Agent Governance Pilot Program**

---

## Agreement Details

**Service Provider:**
[Your Name / Your Law Firm Name]
[Address]
[Email: mail@uapk.info]

**Client:**
[Client Company Name]
[Address]
[Primary Contact: Name, Title]
[Email]

**Effective Date:** [Date]

**Project Name:** UAPK Gateway Pilot Implementation for [Client Name]

**Total Fee:** $[15,000 - 25,000] (Fixed Fee)

**Timeline:** [Start Date] to [End Date] (2-4 weeks)

---

## 1. Project Overview

### 1.1 Background

Client operates [describe client's business] and seeks to deploy AI agents for [describe workflow/use case]. Client requires governance controls, policy enforcement, human approval workflows, and tamper-evident audit trails to meet compliance requirements and manage risk.

### 1.2 Objective

Service Provider will implement and configure UAPK Gateway (an open-source agent governance platform) for Client's specific use case, delivering a production-ready deployment with policies, approval workflows, and operator training.

### 1.3 Target Workflow

**Agent Type:** [e.g., Settlement Negotiation Agent]

**Use Case:** [e.g., Automated negotiation of IP infringement settlements for cases valued under $50,000]

**Key Requirements:**
- Policy enforcement (automatic approval ≤$10K, human approval $10K-$50K, deny >$50K)
- Tamper-evident audit trail for regulatory compliance
- Human-in-the-loop approval workflow
- Integration with existing systems: [list systems]

---

## 2. Scope of Work

### 2.1 In Scope

Service Provider will deliver the following:

#### **Phase 1: Discovery & Design (Week 1)**

**Activities:**
- Requirements workshop (2-3 hours total)
- Map agent roles, actions, and tools
- Define policy rules and approval thresholds
- Document compliance requirements (SOC2, GDPR, industry-specific)
- Design approval workflows
- Identify integration points with Client's systems

**Deliverables:**
- [ ] UAPK Manifest (draft) defining agent governance rules
- [ ] Integration Architecture Document
- [ ] Success Criteria and Acceptance Tests

#### **Phase 2: Deployment (Week 2)**

**Activities:**
- Deploy UAPK Gateway to Client's infrastructure (or provision new VM)
- Configure PostgreSQL database and security settings
- Set up authentication (API keys, JWT)
- Configure HTTPS/SSL (if domain provided)
- Deploy operator dashboard (web UI)
- Set up monitoring and logging

**Deliverables:**
- [ ] UAPK Gateway service deployed and operational
- [ ] Operator dashboard accessible at [URL]
- [ ] Database initialized and secured
- [ ] API endpoints functional and documented
- [ ] Health checks and monitoring configured

#### **Phase 3: Integration (Week 2-3)**

**Activities:**
- Configure UAPK Manifest for Client's use case
- Upload manifest to gateway
- Implement connectors for Client's tools (email, webhooks, APIs)
- Provide agent integration code examples (SDK or REST API)
- Support Client's developers in modifying agent code
- Configure approval workflows in web UI
- Set up tamper-evident logging with hash chaining

**Deliverables:**
- [ ] UAPK Manifest uploaded and active
- [ ] Connectors configured for Client's tools
- [ ] Agent integration code examples (Python/JavaScript)
- [ ] Approval workflows configured
- [ ] Interaction logging active with hash verification

#### **Phase 4: Testing & Validation (Week 3-4)**

**Activities:**
- End-to-end testing (happy paths and edge cases)
- Security review (secrets management, API keys, connector allowlists)
- Performance validation (latency, throughput)
- Approval workflow testing (escalation paths)
- Audit log verification (hash chain, signatures)
- Production readiness review

**Deliverables:**
- [ ] Test Results Report
- [ ] Performance benchmarks
- [ ] Security validation checklist
- [ ] Sample compliance export bundle

#### **Phase 5: Production Go-Live & Training (Week 4)**

**Activities:**
- Production deployment (if separate from staging)
- Operator training session (2 hours, recorded)
- Documentation review and handoff
- Go-live monitoring (first 24 hours)

**Deliverables:**
- [ ] Production UAPK Gateway operational
- [ ] Operator training completed (2-hour session, recorded)
- [ ] Operator Runbook (deployment, troubleshooting, compliance)
- [ ] Production Deployment Checklist
- [ ] Compliance export template

#### **Phase 6: Post-Pilot Support (30 Days After Go-Live)**

**Activities:**
- Bug fixes (code defects, not scope changes)
- Configuration adjustments
- Questions answered (email/Slack)
- Monitoring assistance

**Deliverables:**
- [ ] Bug fixes as needed
- [ ] Email/Slack support
- [ ] Configuration assistance

### 2.2 Out of Scope

The following are explicitly **excluded** from this engagement:

- ❌ Development of Client's AI agents (Client provides agents)
- ❌ Custom agent logic or model training
- ❌ Integration with more than [3] third-party tools/systems
- ❌ Custom UI development beyond standard operator dashboard
- ❌ Ongoing hosting or infrastructure costs (Client responsible)
- ❌ Additional workflows beyond the single use case defined above
- ❌ Support beyond 30 days post-go-live (Enterprise Support available separately)
- ❌ Modifications to Client's existing systems (beyond agent code integration)
- ❌ Training for more than [5] operators (additional training available)
- ❌ Regulatory filings or legal compliance reviews (advisory only)

### 2.3 Change Requests

Changes to scope require written approval and may result in additional fees calculated at $[300-500]/hour or via separate change order.

---

## 3. Client Responsibilities

Client agrees to provide the following:

### 3.1 Infrastructure Access

- [ ] VM or server with sudo access (or approval to provision new VM)
- [ ] PostgreSQL database (v13+) or approval to provision
- [ ] Firewall rules allowing port 8000 (or custom port)
- [ ] Domain name for SSL (optional but recommended)
- [ ] Backup and disaster recovery plan (or acceptance of Provider's recommendations)

### 3.2 Technical Resources

- [ ] Developer(s) with 15-20 hours availability for agent integration
- [ ] DevOps engineer with 5-10 hours availability for deployment support
- [ ] Access to systems/APIs that agents will interact with
- [ ] API keys and credentials for third-party tools (SendGrid, etc.)

### 3.3 Business Resources

- [ ] Stakeholder availability for policy decisions (2-3 hours total)
- [ ] Operator(s) designated for approval workflows (attend 2-hour training)
- [ ] Compliance/legal review (if required by Client's policies)
- [ ] Timely feedback on deliverables (within 2 business days)

### 3.4 Information Provided

- [ ] Detailed use case description
- [ ] List of actions agents will take
- [ ] Risk tolerance and approval thresholds
- [ ] Compliance requirements (SOC2, GDPR, HIPAA, etc.)
- [ ] Existing system architecture diagrams

---

## 4. Timeline & Milestones

### 4.1 Project Schedule

| Phase | Duration | Milestone | Payment |
|-------|----------|-----------|---------|
| **Phase 1: Discovery** | Week 1 | Manifest draft + Architecture doc | $[5,000] (33%) |
| **Phase 2-3: Deploy & Integrate** | Week 2-3 | Gateway deployed, agents integrated | $[5,000] (33%) |
| **Phase 4-5: Test & Go-Live** | Week 3-4 | Production deployment + training | $[5,000] (34%) |
| **Phase 6: Post-Support** | 30 days | Support period | Included |

**Alternative Payment Schedule:**
- 50% upfront upon SOW execution
- 50% upon production go-live

### 4.2 Key Milestones

- [ ] **M1 (Day 5):** Kickoff complete, manifest draft delivered
- [ ] **M2 (Day 10):** Gateway deployed to staging
- [ ] **M3 (Day 15):** Agent integrated and calling gateway
- [ ] **M4 (Day 20):** Testing complete, training delivered
- [ ] **M5 (Day 21):** Production go-live
- [ ] **M6 (Day 51):** 30-day support period ends

### 4.3 Dependencies

Timeline assumes:
- Client provides timely access and information
- No security review delays
- Standard deployment (no custom requirements)
- Client developers available for integration work

Delays in Client responsibilities may extend timeline proportionally.

---

## 5. Deliverables & Acceptance Criteria

### 5.1 Acceptance Criteria

Each deliverable will be considered accepted when:

1. **Deployment:** Gateway accessible at specified URL with health check returning 200 OK
2. **Manifest:** Uploaded to gateway and validated (no errors)
3. **Integration:** Client's agent successfully calls gateway and receives ALLOW/DENY/ESCALATE decisions
4. **Approvals:** Test approval workflow completes successfully (escalate → approve → execute)
5. **Audit Logs:** Export bundle generated and hash chain verified
6. **Training:** Operators demonstrate ability to approve/deny and export logs

### 5.2 Acceptance Process

- Service Provider notifies Client of deliverable completion
- Client has 3 business days to review and accept or provide specific rejection reasons
- Silence after 3 days constitutes acceptance
- Rejected deliverables will be corrected within 2 business days

---

## 6. Fees & Payment Terms

### 6.1 Total Fee

**Fixed Fee:** $[Amount] USD

**Includes:** All labor, deliverables, and 30-day post-pilot support

**Excludes:**
- Infrastructure costs (VM, hosting) - Client responsibility or billed separately at cost
- Third-party API fees (SendGrid, etc.) - Client responsibility
- Additional workflows beyond scope - Requires new SOW

### 6.2 Payment Schedule

**Option A (Milestone-Based):**
- Invoice 1: $[X] upon SOW execution (33%)
- Invoice 2: $[X] upon M2 completion (33%)
- Invoice 3: $[X] upon M5 completion (34%)

**Option B (Simplified):**
- Invoice 1: $[X] upon SOW execution (50%)
- Invoice 2: $[X] upon production go-live (50%)

### 6.3 Payment Terms

- Payment due within 30 days of invoice date
- Payment methods: ACH, wire transfer, credit card
- Late payments subject to 1.5% monthly interest

### 6.4 Expenses

Infrastructure costs (if Provider provisions):
- VM hosting: $50-150/month (billed at cost)
- Domain/SSL: $10-50/year (billed at cost)
- Client may elect to provide own infrastructure (no additional cost)

---

## 7. Intellectual Property

### 7.1 Open Source

UAPK Gateway is licensed under Apache License 2.0 (open source). Client receives no proprietary rights to the core software, but has full rights to use, modify, and distribute per the Apache 2.0 license.

### 7.2 Custom Deliverables

**Client owns:**
- UAPK Manifest(s) created for Client's use case
- Integration code specific to Client's systems
- Documentation and runbooks

**Provider retains:**
- Right to use de-identified examples in future work
- Right to improve UAPK Gateway core based on learnings
- Right to publish anonymized case studies (with Client approval)

### 7.3 Confidentiality

Both parties agree to keep confidential:
- Client's business information and use cases
- Technical architecture and integration details
- Pricing and commercial terms

Exception: Provider may disclose that Client is a customer for reference purposes (with approval).

---

## 8. Warranties & Limitations

### 8.1 Warranties

**Service Provider warrants:**
- UAPK Gateway will perform substantially as documented
- Deployment will be conducted in professional manner
- Deliverables will meet acceptance criteria

**Service Provider does NOT warrant:**
- That UAPK Gateway will meet Client's compliance requirements (advisory only)
- Specific uptime or performance metrics (Client operates post-deployment)
- That Client's agents will function correctly (Client's responsibility)

### 8.2 Limitation of Liability

**Provider's total liability limited to fees paid by Client under this SOW.**

Provider not liable for:
- Client's agent behavior or decisions
- Regulatory penalties or compliance violations
- Data loss (Client responsible for backups)
- Third-party service failures (SendGrid, AWS, etc.)

### 8.3 Disclaimer

UAPK Gateway is governance infrastructure, not legal advice. Client remains responsible for:
- Compliance with applicable laws and regulations
- Agent behavior and decisions
- Security of their systems and data
- Proper operation of gateway post-deployment

---

## 9. Support Terms

### 9.1 Pilot Support (Included)

**30 days from production go-live:**
- Email/Slack support (business hours, 24-hour response)
- Bug fixes (code defects in delivered components)
- Configuration assistance
- Documentation clarifications

**Excluded from support:**
- New features or scope additions
- Training additional operators
- Client's infrastructure issues
- Client's agent code bugs

### 9.2 Post-Pilot Support (Optional)

**Enterprise Support available:**
- $3,000-$10,000/month (based on scope)
- 4-hour response SLA
- Priority bug fixes
- Version upgrades
- Additional connectors
- Dedicated support channel

Contact sales@uapk.info for Enterprise Support quote.

---

## 10. Dependencies & Assumptions

### 10.1 Assumptions

This SOW assumes:
- Single agent workflow (additional agents require scope change)
- Standard deployment (Docker Compose or direct install)
- Up to 3 third-party connectors (email, webhooks, HTTP APIs)
- Client provides infrastructure or approves $50-150/month VM cost
- Client developers available for integration work
- English language deliverables and communication
- No custom UI development required
- Standard approval workflow (operators via web dashboard)

### 10.2 Dependencies

**Client provides:**
- Infrastructure access within 2 business days of SOW execution
- Developer availability for integration (Week 2-3)
- Stakeholder decisions on policies (within 2 business days when requested)
- Testing resources and test cases
- Operator designation for training

**Provider depends on:**
- UAPK Gateway GitHub repository availability
- Third-party services (GitHub, Docker Hub) operational
- Internet connectivity for remote implementation

---

## 11. Terms & Conditions

### 11.1 Term & Termination

**Term:** This SOW is effective from execution date through completion of 30-day support period.

**Termination:**
- Either party may terminate with 7 days written notice
- If Client terminates: Payment due for completed milestones
- If Provider terminates: Refund of fees for incomplete milestones
- Termination does not affect Client's rights to use UAPK Gateway (Apache 2.0 license continues)

### 11.2 Independent Contractor

Service Provider is an independent contractor, not an employee. Provider responsible for own taxes, insurance, and business expenses.

### 11.3 Governing Law

This SOW is governed by the laws of [Your Jurisdiction], without regard to conflict of law provisions.

### 11.4 Entire Agreement

This SOW constitutes the entire agreement between parties regarding this pilot implementation. Any modifications must be in writing and signed by both parties.

### 11.5 Severability

If any provision is found unenforceable, the remainder of this SOW remains in effect.

---

## 12. Success Criteria

### 12.1 Technical Acceptance

Pilot is considered successful when:

- [ ] UAPK Gateway deployed and accessible (health check returns 200 OK)
- [ ] Client's agent successfully integrated (can send action requests)
- [ ] Policy enforcement works (ALLOW/DENY/ESCALATE decisions correct)
- [ ] Approval workflow functional (escalate → human review → approve/deny → execute)
- [ ] Audit logs exportable and hash chain verifiable
- [ ] At least 3 end-to-end test scenarios pass successfully
- [ ] Operators trained and can demonstrate competency

### 12.2 Documentation Acceptance

Required documentation delivered and approved:

- [ ] Architecture diagram showing integration
- [ ] Operator runbook (min 10 pages)
- [ ] API reference for agent integration
- [ ] Compliance export procedures
- [ ] Troubleshooting guide

### 12.3 Training Acceptance

Training is considered complete when:

- [ ] 2-hour session delivered (recorded)
- [ ] Operators demonstrate ability to approve/deny actions
- [ ] Operators demonstrate ability to export audit logs
- [ ] Operators demonstrate hash chain verification

---

## 13. Risk Allocation

### 13.1 Provider Responsibilities

Provider is responsible for:
- Quality of UAPK Gateway deployment
- Correctness of manifest configuration
- Functionality of delivered components
- Professional service delivery

### 13.2 Client Responsibilities

Client is responsible for:
- Their agent code and logic
- Their business rules and policies
- Compliance with applicable laws
- Security of their infrastructure
- Operation of gateway post-handoff
- Backups and disaster recovery

### 13.3 Third-Party Services

Neither party responsible for:
- Third-party service failures (AWS, SendGrid, etc.)
- Open-source software bugs in dependencies
- Internet or network outages

---

## 14. Change Order Process

### 14.1 Scope Changes

If Client requests changes beyond this SOW:

1. Client submits change request in writing
2. Provider provides estimate (time and cost)
3. Both parties approve in writing
4. Timeline and fees adjusted accordingly

**Example changes requiring change order:**
- Additional agent workflows
- Custom connector development
- Extended training or additional operators
- Custom dashboard modifications
- More than 3 third-party integrations

### 14.2 Change Order Rates

**Hourly rate for out-of-scope work:** $[300-500]/hour

**Or:** Fixed-fee change orders negotiated case-by-case

---

## 15. Approval & Signatures

By signing below, both parties agree to the terms of this Statement of Work.

---

**SERVICE PROVIDER:**

Signature: ________________________________

Name: [Your Name]

Title: [Principal / Attorney / Founder]

Date: ________________________________

---

**CLIENT:**

Signature: ________________________________

Name: [Client Name]

Title: [Client Title]

Date: ________________________________

---

## Appendix A: Detailed Deliverables List

### Technical Deliverables

**Deployment:**
- [ ] UAPK Gateway service (Docker container or direct install)
- [ ] PostgreSQL database (configured and initialized)
- [ ] Operator dashboard (web UI at https://[client-url]:8000)
- [ ] API endpoint (https://[client-url]:8000/api)
- [ ] Health monitoring endpoint
- [ ] SSL certificate (if domain provided)

**Configuration:**
- [ ] .env.production (Client's settings)
- [ ] UAPK Manifest JSON/YAML
- [ ] Policy rules configured
- [ ] Approval workflows configured
- [ ] Connector configurations (up to 3)
- [ ] API keys generated

**Integration:**
- [ ] Python SDK examples
- [ ] JavaScript SDK examples (if needed)
- [ ] REST API integration guide
- [ ] Sample agent code (modified to use gateway)
- [ ] Error handling patterns
- [ ] Testing scripts

**Documentation:**
- [ ] Architecture diagram (PDF)
- [ ] Operator runbook (PDF, min 10 pages)
- [ ] API reference documentation
- [ ] Compliance export guide
- [ ] Troubleshooting guide
- [ ] FAQ document

**Training:**
- [ ] 2-hour operator training (recorded)
- [ ] Training slides (PDF)
- [ ] Quick reference card
- [ ] Demo video (optional)

---

## Appendix B: Technology Stack

**UAPK Gateway Components:**
- FastAPI (Python web framework)
- PostgreSQL (database)
- Uvicorn (ASGI server)
- SQLAlchemy (ORM)
- Alembic (migrations)

**Client Integration:**
- Python SDK (provided)
- JavaScript SDK (provided)
- REST API (documented)

**Infrastructure:**
- Linux (Ubuntu 22.04 LTS recommended)
- Docker (optional but recommended)
- Nginx/Caddy (reverse proxy, optional)

**Security:**
- Ed25519 signatures
- Fernet encryption (secrets)
- JWT authentication
- API key authentication
- HTTPS/TLS (recommended)

---

## Appendix C: Sample Timeline (3-Week Pilot)

### Week 1
- **Mon:** Kickoff call, requirements gathering
- **Wed:** Architecture review, manifest draft
- **Fri:** Manifest approved, deployment planning complete

### Week 2
- **Mon:** Gateway deployment begins
- **Wed:** Gateway deployed, manifest uploaded
- **Fri:** Agent integration started

### Week 3
- **Mon-Wed:** Integration complete, testing
- **Thu:** Operator training session
- **Fri:** Production go-live

### Week 4-7 (30 days)
- **Ongoing:** Post-pilot support

---

## Appendix D: Contact Information

**Project Manager (Provider):**
- Name: [Your Name]
- Email: [Your Email]
- Phone: [Your Phone]
- Availability: [Business Hours, Timezone]

**Primary Contact (Client):**
- Name: [Client Contact]
- Email: [Client Email]
- Phone: [Client Phone]

**Emergency Contact:**
- For production issues: [Email/Phone]
- Response time: 4 hours (business days)

---

## Appendix E: Success Metrics

**Pilot is successful if:**

1. **Technical Functionality:**
   - Gateway responds to agent requests in <500ms (p95)
   - 99%+ uptime during pilot period
   - Zero data loss or corruption
   - Audit log hash chain 100% valid

2. **Business Outcomes:**
   - Client's agent can execute workflow end-to-end
   - Approval workflow reduces manual review time by >50%
   - Compliance team approves deployment
   - At least 10 successful agent actions logged

3. **Stakeholder Satisfaction:**
   - Operators feel confident using system
   - Developers find integration straightforward
   - Compliance team has needed audit evidence
   - Business sponsors approve production deployment

---

**END OF STATEMENT OF WORK**

---

## 📝 Notes for Customization

**When creating SOW for specific client:**

1. **Replace all [bracketed] placeholders** with client-specific information
2. **Adjust fee** based on complexity ($15K simple, $25K complex)
3. **Modify timeline** if needed (2 weeks for simple, 4 weeks for complex)
4. **Add client-specific requirements** to scope
5. **Update success criteria** for their use case
6. **Specify exact deliverable URLs** (their gateway URL)
7. **Include any special terms** they require (MSA, insurance, etc.)

**Red Flags (Require Scope Change):**
- More than 1 agent workflow (each additional = +$5K-$10K)
- More than 3 connectors (each additional = +$2K-$5K)
- Custom UI beyond standard dashboard (+$5K-$15K)
- Complex compliance requirements (SOC2 audit support = +$10K-$20K)
- More than 5 operators to train (each additional 5 = +$2K)

---

**This SOW protects both you and the client while clearly defining what's included in the $15K-$25K pilot.**

Save this template and customize for each client engagement!
