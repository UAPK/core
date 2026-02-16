import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import ContactForm from '@site/src/components/ContactForm';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          The Agent Firewall for High-Stakes AI
        </Heading>
        <p className="hero__subtitle" style={{fontSize: '1.3rem', fontWeight: 500}}>
          Deploy autonomous AI agents in <strong>legal, finance, and compliance</strong> — with the
          guardrails, approvals, and audit trails that regulators demand.
        </p>
        <div className={styles.buttons} style={{marginTop: '2rem'}}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/quickstart"
            style={{marginRight: '1rem'}}>
            Try Free (5 min setup)
          </Link>
          <Link
            className="button button--primary button--lg"
            to="/docs/business/pilot">
            Book Pilot ($15K-$25K)
          </Link>
        </div>
        <div style={{marginTop: '1.5rem', opacity: 0.9}}>
          <small>
            ✓ Self-hosted (your infrastructure) • ✓ Apache 2.0 open source • ✓ Production-ready in 2-4 weeks
          </small>
        </div>
      </div>
    </header>
  );
}

function QuickDemo() {
  return (
    <section style={{padding: '4rem 0', backgroundColor: 'var(--ifm-color-emphasis-100)'}}>
      <div className="container">
        <div className="row">
          <div className="col col--6">
            <Heading as="h2">See It In Action</Heading>
            <p style={{fontSize: '1.1rem', marginBottom: '2rem'}}>
              Every agent action flows through the gateway for policy enforcement and audit logging.
            </p>
            <pre style={{
              backgroundColor: '#1e1e1e',
              color: '#d4d4d4',
              padding: '1.5rem',
              borderRadius: '8px',
              fontSize: '0.9rem',
              overflow: 'auto'
            }}>
{`# Agent proposes action
curl -X POST /gateway/execute \\
  -H "X-API-Key: $KEY" \\
  -d '{
    "uapk_id": "settlement-bot",
    "action": {
      "type": "legal",
      "tool": "send_settlement_offer",
      "params": {"amount": 5000}
    }
  }'

# Gateway response
{
  "decision": "ALLOW",
  "executed": true,
  "interaction_id": "int-abc123"
}`}
            </pre>
          </div>
          <div className="col col--6">
            <Heading as="h3">What Just Happened?</Heading>
            <ul style={{fontSize: '1.05rem', lineHeight: '1.8'}}>
              <li>✓ <strong>Manifest check:</strong> Is settlement-bot registered?</li>
              <li>✓ <strong>Capability check:</strong> Can it send settlements?</li>
              <li>✓ <strong>Budget check:</strong> $5K under $50K threshold</li>
              <li>✓ <strong>Policy check:</strong> Passed all rules</li>
              <li>→ <strong>Executed</strong> via connector</li>
              <li>📝 <strong>Logged</strong> with hash chain + signature</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function BeforeAfter() {
  return (
    <section style={{padding: '4rem 0'}}>
      <div className="container">
        <Heading as="h2" style={{textAlign: 'center', marginBottom: '3rem'}}>
          Before vs After UAPK Gateway
        </Heading>
        <div className="row">
          <div className="col col--6">
            <div style={{padding: '2rem', border: '2px solid #ff6b6b', borderRadius: '8px', height: '100%'}}>
              <h3 style={{color: '#ff6b6b'}}>❌ Without UAPK</h3>
              <ul>
                <li>Compliance blocks every agent deployment</li>
                <li>"Who authorized this?" (no attribution)</li>
                <li>"Can we prove it in court?" (no audit trail)</li>
                <li>"How do we stop it?" (no kill switch)</li>
                <li>Months of back-and-forth with legal/compliance</li>
                <li>Vendor logs (90-day retention, not court-admissible)</li>
              </ul>
            </div>
          </div>
          <div className="col col--6">
            <div style={{padding: '2rem', border: '2px solid #51cf66', borderRadius: '8px', height: '100%'}}>
              <h3 style={{color: '#51cf66'}}>✓ With UAPK</h3>
              <ul>
                <li><strong>Policy enforcement:</strong> ALLOW/DENY/ESCALATE</li>
                <li><strong>Attribution:</strong> Every action traced to agent + manifest</li>
                <li><strong>Court-ready logs:</strong> Hash-chained, Ed25519 signed</li>
                <li><strong>Human approvals:</strong> High-risk actions reviewed</li>
                <li><strong>Production in 2-4 weeks:</strong> Fixed-fee pilot</li>
                <li><strong>Your evidence:</strong> Self-hosted, indefinite retention</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function FortySevenersShowcase() {
  return (
    <section style={{padding: '4rem 0', backgroundColor: 'var(--ifm-color-emphasis-100)'}}>
      <div className="container">
        <Heading as="h2" style={{textAlign: 'center', marginBottom: '1rem'}}>
          The "47ers" Library
        </Heading>
        <p style={{textAlign: 'center', fontSize: '1.1rem', marginBottom: '3rem'}}>
          Pre-built governance templates for common workflows
        </p>
        <div className="row">
          <div className="col col--4">
            <div style={{padding: '1.5rem', backgroundColor: 'white', borderRadius: '8px', height: '100%'}}>
              <h3>⚖️ Legal</h3>
              <ul>
                <li><strong>IP Settlement Gate:</strong> Auto-negotiate up to $50K, escalate above</li>
                <li><strong>DMCA Takedown:</strong> 200 notices/day with compliance tracking</li>
              </ul>
              <Link to="/docs/47ers">View templates →</Link>
            </div>
          </div>
          <div className="col col--4">
            <div style={{padding: '1.5rem', backgroundColor: 'white', borderRadius: '8px', height: '100%'}}>
              <h3>💰 Finance</h3>
              <ul>
                <li><strong>Trading Gate:</strong> $10K auto-execute, $100K daily cap</li>
                <li><strong>KYC Onboarding:</strong> Risk-based routing + sanctions screening</li>
              </ul>
              <Link to="/docs/47ers">View templates →</Link>
            </div>
          </div>
          <div className="col col--4">
            <div style={{padding: '1.5rem', backgroundColor: 'white', borderRadius: '8px', height: '100%'}}>
              <h3>🔒 Compliance</h3>
              <ul>
                <li><strong>Vendor Due Diligence:</strong> Automated risk assessment</li>
                <li><strong>Email Guard:</strong> Rate limits + recipient validation</li>
              </ul>
              <Link to="/docs/47ers">View templates →</Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function WhyNotObsolete() {
  return (
    <section style={{padding: '4rem 0', backgroundColor: '#f8f9fa'}}>
      <div className="container">
        <Heading as="h2" style={{textAlign: 'center', marginBottom: '2rem'}}>
          Why UAPK Won't Be Obsolete
        </Heading>
        <div style={{maxWidth: '800px', margin: '0 auto', fontSize: '1.05rem'}}>
          <p style={{textAlign: 'center', fontSize: '1.2rem', fontWeight: 500, marginBottom: '2rem'}}>
            Model vendors will improve. Your governance requirements won't change.
          </p>
          <div className="row" style={{marginTop: '2rem'}}>
            <div className="col col--6">
              <h4>🎯 Model-Agnostic by Design</h4>
              <p>
                UAPK governs <strong>actions at the boundary</strong> to real systems.
                It doesn't care which model you use (GPT-4, Claude, Llama, Gemini).
              </p>
            </div>
            <div className="col col--6">
              <h4>🏛️ Regulation Requires It</h4>
              <p>
                SOC2, GDPR, SEC audits require <strong>organization-owned evidence</strong>.
                "Check the OpenAI logs" doesn't work in court.
              </p>
            </div>
          </div>
          <div style={{textAlign: 'center', marginTop: '2rem'}}>
            <Link to="/docs/concepts/future-proof" className="button button--primary">
              Read the full argument →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section style={{padding: '4rem 0', backgroundColor: 'var(--ifm-color-emphasis-100)'}}>
      <div className="container">
        <div style={{textAlign: 'center', marginBottom: '3rem'}}>
          <Heading as="h2">Ready to Deploy Agents Safely?</Heading>
          <p style={{fontSize: '1.2rem', color: 'var(--ifm-color-emphasis-700)'}}>
            Get expert help from a lawyer-developer who built this for real-world compliance needs
          </p>
        </div>

        <ContactForm />

        <div style={{textAlign: 'center', marginTop: '3rem'}}>
          <p style={{fontSize: '1.1rem', marginBottom: '1rem'}}>
            <strong>Or explore on your own:</strong>
          </p>
          <p>
            <Link to="/docs/quickstart">Self-Host (Free)</Link>
            {' • '}
            <Link to="/docs/business/pricing">View Pricing</Link>
            {' • '}
            <Link to="https://github.com/UAPK/core">View on GitHub</Link>
          </p>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description="Policy enforcement and audit logging for AI agents. Deploy autonomous agents with hard guardrails, human approvals, and tamper-evident audit logs.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <QuickDemo />
        <BeforeAfter />
        <FortySevenersShowcase />
        <WhyNotObsolete />
        <FinalCTA />
      </main>
    </Layout>
  );
}
