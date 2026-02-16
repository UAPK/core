# ✅ Client Onboarding Checklist

**Quick reference for pilot implementation**

---

## 📋 PRE-PILOT (Before SOW Signature)

### Discovery Call Checklist

- [ ] **Understand use case**
  - What agents are they building?
  - What actions will agents take?
  - What tools/APIs will agents use?

- [ ] **Assess complexity**
  - Single workflow or multiple?
  - How many different action types?
  - How many third-party integrations?

- [ ] **Identify stakeholders**
  - Who approves agent actions?
  - Who operates the gateway?
  - Who needs training?

- [ ] **Confirm requirements**
  - Compliance needs (SOC2, GDPR, etc.)?
  - Approval thresholds?
  - Risk tolerance?

- [ ] **Technical readiness**
  - Do they have infrastructure?
  - Do they have developers available?
  - What's their tech stack?

### Quote & Scope

- [ ] **Determine pricing**
  - Simple (1 agent, 3 actions): $15K
  - Medium (1 agent, 5-10 actions): $20K
  - Complex (multiple agents, integrations): $25K

- [ ] **Create custom SOW**
  - Use template
  - Fill in client details
  - Specify exact deliverables
  - Set timeline

- [ ] **Send proposal**
  - SOW via email
  - Answer questions
  - Negotiate if needed

- [ ] **SOW signed**
  - Both parties sign
  - Invoice sent (50% upfront)

---

## 📦 PILOT EXECUTION

### Week 1: Discovery & Design

- [ ] **Kickoff call** (2 hours)
  - Introductions
  - Review use case in detail
  - Walk through agent workflow
  - Identify decision points

- [ ] **Technical discovery** (4 hours)
  - Map agent architecture
  - List all actions agent can take
  - Document tools/APIs used
  - Security and auth review

- [ ] **Policy design** (3 hours)
  - Define ALLOW rules
  - Define ESCALATE triggers
  - Define DENY conditions
  - Set budget caps

- [ ] **Create manifest** (3 hours)
  - Draft UAPK Manifest YAML
  - Define agent roles
  - Configure policies
  - Set up connectors

- [ ] **Review & approve** (1 hour)
  - Client reviews manifest
  - Adjustments if needed
  - Final approval

**Deliverable:** ✅ Manifest draft + Architecture doc

---

### Week 2: Deployment

- [ ] **Infrastructure setup** (2 hours)
  - Provision VM (or use client's)
  - Install dependencies
  - Configure PostgreSQL
  - Set up firewall

- [ ] **Deploy gateway** (2 hours)
  - Clone repository
  - Configure .env
  - Deploy service
  - Verify health checks

- [ ] **Upload manifest** (1 hour)
  - Create organization
  - Upload manifest via API
  - Validate configuration
  - Test policies

- [ ] **Configure connectors** (3 hours)
  - Set up email connector
  - Configure webhooks
  - Add API credentials
  - Test connectivity

- [ ] **Set up dashboard** (1 hour)
  - Create admin accounts
  - Configure approval workflows
  - Test operator UI

**Deliverable:** ✅ Gateway deployed and configured

---

### Week 3: Integration & Testing

- [ ] **Agent integration** (8 hours client devs, 4 hours your support)
  - Provide SDK examples
  - Client modifies agent code
  - Replace direct calls with gateway calls
  - Add error handling

- [ ] **Testing** (4 hours)
  - Test ALLOW scenarios
  - Test ESCALATE scenarios
  - Test DENY scenarios
  - Verify audit logs

- [ ] **Approval workflow test** (2 hours)
  - Trigger escalation
  - Operator reviews in dashboard
  - Approve action
  - Verify execution

- [ ] **Audit verification** (2 hours)
  - Export audit logs
  - Verify hash chain
  - Check signatures
  - Test compliance bundle

**Deliverable:** ✅ Integrated and tested

---

### Week 4: Production & Training

- [ ] **Production deployment** (2 hours)
  - Fresh production keys
  - Production database
  - SSL certificate
  - Final security review

- [ ] **Operator training** (2 hours)
  - Live session (recorded)
  - Dashboard walkthrough
  - Approval scenarios
  - Audit export demo
  - Q&A

- [ ] **Go-live** (2 hours)
  - Switch agents to production gateway
  - Monitor first interactions
  - Verify logs
  - Confirm everything working

- [ ] **Handoff** (1 hour)
  - Deliver all documentation
  - Review runbooks
  - Set up support channel
  - Schedule 1-week check-in

**Deliverable:** ✅ Production ready + operators trained

---

### Weeks 5-8: Post-Pilot Support

- [ ] **Week 1 check-in**
  - How's it going?
  - Any issues?
  - Questions?

- [ ] **Ongoing support** (as needed)
  - Answer questions
  - Fix bugs
  - Configuration help

- [ ] **End of support period**
  - Final check-in
  - Offer enterprise support
  - Close out pilot

---

## 🎯 CLIENT COMMUNICATION TEMPLATES

### Email 1: Welcome (After SOW Signed)

```
Subject: Welcome to UAPK Gateway Pilot - Next Steps

Hi [Name],

Excited to get started with your UAPK Gateway pilot!

Attached: Statement of Work (signed)

Next Steps:
1. Invoice #[NUMBER] sent separately ($[X] - 50% upfront)
2. Kickoff call scheduled: [Date/Time] [Calendar Link]
3. Pre-work: Please prepare list of agent actions and tools

What to bring to kickoff:
- Your agent architecture diagram (if available)
- List of tools/APIs agents will use
- Names of stakeholders for approvals
- Any compliance requirements

Looking forward to building this with you!

[Your Name]
```

### Email 2: Milestone Complete

```
Subject: UAPK Gateway Pilot - Milestone [X] Complete

Hi [Name],

Great progress! Milestone [X] is complete:

✅ [Deliverable 1]
✅ [Deliverable 2]
✅ [Deliverable 3]

Access:
- Gateway: https://[client-gateway]:8000
- Dashboard: https://[client-gateway]:8000/admin
- Credentials: [Sent separately]

Next Steps:
- Your team: [Action required from client]
- My team: [What you'll work on next]
- Timeline: [When next milestone due]

Next sync: [Date/Time]

Invoice #[NUMBER] for milestone payment sent separately ($[X]).

Questions? Reply to this email or Slack me.

[Your Name]
```

### Email 3: Pilot Complete

```
Subject: UAPK Gateway Pilot Complete - Congratulations!

Hi [Name],

🎉 Your UAPK Gateway pilot is complete!

What we accomplished:
✅ Gateway deployed and operational
✅ [Agent name] integrated with governance
✅ Policies enforcing (ALLOW/DENY/ESCALATE)
✅ Approval workflows active
✅ Audit logs tamper-evident
✅ Operators trained
✅ Production ready

Your System:
- Gateway: https://[url]:8000
- Dashboard: https://[url]:8000/admin
- Documentation: [Link to docs]

Final deliverables attached:
- Architecture diagram
- Operator runbook
- Compliance export guide
- Training recording

30-Day Support:
I'm available for questions, bugs, and configuration help for the
next 30 days (until [date]).

After that, you have options:
1. Self-manage (open source, $0/month)
2. Enterprise support ($3K-$10K/month)
3. Additional pilots for other workflows

Would you like to schedule a check-in call for next week?

Congratulations on shipping agents safely!

[Your Name]
```

---

## 🚀 POST-PILOT UPSELLS

### When Pilot Succeeds:

**Option 1: Enterprise Support**
"Now that you're in production, want peace of mind with dedicated support?"
- $3K-$10K/month
- 4-hour SLA
- Priority fixes
- Upgrades included

**Option 2: Additional Workflows**
"Have other agent workflows that need governance?"
- $10K-$15K per additional agent
- Reuse existing gateway
- Faster (1-2 weeks)

**Option 3: Custom Development**
"Need features not in open source?"
- Custom connectors
- Custom dashboards
- Advanced analytics
- Hourly or fixed-fee

---

## ✅ PILOT SUCCESS CHECKLIST

### Before Marking Pilot Complete:

- [ ] All technical acceptance criteria met
- [ ] Client confirms satisfaction
- [ ] All invoices paid
- [ ] Documentation delivered
- [ ] Training recorded and sent
- [ ] Handoff meeting complete
- [ ] Support channel established
- [ ] 1-week check-in scheduled

### Pilot Outcomes:

**Success (70% typical):**
- Client is happy
- System in production
- Offer enterprise support
- Ask for referrals/testimonial

**Partial Success (20%):**
- Works but needs tweaks
- Extend support if needed
- Additional change orders
- Still salvageable

**Failure (10%):**
- Doesn't meet objectives
- Client dissatisfied
- Partial refund if appropriate
- Learn from experience

---

**Use this checklist for every pilot to ensure consistent, high-quality delivery!**
