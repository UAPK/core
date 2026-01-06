import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <p className="hero__subtitle" style={{marginTop: '1rem', fontSize: '1.1rem'}}>
          Deploy autonomous AI agents with <strong>hard guardrails</strong>, <strong>human approvals</strong>,
          and <strong>tamper-evident audit logs</strong> — on one VM, self-hosted.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro"
            style={{marginRight: '1rem'}}>
            Get Started
          </Link>
          <Link
            className="button button--primary button--lg"
            to="/docs/quickstart">
            Quickstart Guide
          </Link>
        </div>
        <div style={{marginTop: '2rem'}}>
          <Link
            className="button button--outline button--lg"
            to="/docs/business/pilot">
            Enterprise Pilot Program
          </Link>
        </div>
      </div>
    </header>
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
      </main>
    </Layout>
  );
}
