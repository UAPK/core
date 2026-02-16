"""Email service for notifications and auto-responses."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "noreply@uapk.info")
        self.admin_email = os.getenv("ADMIN_EMAIL", "mail@uapk.info")
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """Send an email."""
        if not self.enabled:
            logger.info(
                "email_not_sent_disabled",
                to=to,
                subject=subject,
                reason="EMAIL_ENABLED=false",
            )
            return False

        if not self.smtp_user or not self.smtp_password:
            logger.warning(
                "email_not_sent_no_config",
                to=to,
                subject=subject,
                reason="SMTP credentials not configured",
            )
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_from
            msg['To'] = to
            msg['Subject'] = subject

            # Add text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info("email_sent", to=to, subject=subject)
            return True

        except Exception as e:
            logger.error("email_send_failed", to=to, subject=subject, error=str(e))
            return False

    def send_lead_auto_response(self, lead: Any) -> bool:
        """Send auto-response to new lead."""
        subject = "We've received your UAPK Gateway inquiry"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2563eb;">Thank you for your interest in UAPK Gateway!</h2>

            <p>Hi {lead.name},</p>

            <p>We've received your inquiry about deploying AI agents safely with UAPK Gateway.</p>

            <p><strong>What happens next:</strong></p>
            <ol>
                <li>We'll review your use case within 24 hours</li>
                <li>Schedule a discovery call to understand your requirements</li>
                <li>Provide a custom proposal for your specific needs</li>
            </ol>

            <p><strong>Your submission:</strong></p>
            <ul>
                <li>Company: {lead.company}</li>
                <li>Use Case: {lead.use_case[:200]}{"..." if len(lead.use_case) > 200 else ""}</li>
                <li>Timeline: {lead.timeline or 'Not specified'}</li>
                <li>Budget: {lead.budget or 'Not specified'}</li>
            </ul>

            <p>In the meantime, feel free to:</p>
            <ul>
                <li><a href="https://uapk.info/docs">Read our documentation</a></li>
                <li><a href="https://github.com/UAPK/gateway">Try the open-source version</a></li>
                <li><a href="https://uapk.info/docs/business/pilot">Learn about our pilot program</a></li>
            </ul>

            <p>Best regards,<br>
            <strong>UAPK Gateway Team</strong></p>

            <hr style="margin: 2rem 0; border: none; border-top: 1px solid #e2e8f0;">

            <p style="font-size: 0.9rem; color: #64748b;">
                <strong>About UAPK Gateway:</strong><br>
                Built by a practicing lawyer-developer, UAPK Gateway provides the guardrails,
                approvals, and evidence-grade audit trails needed to deploy AI agents in
                legal, financial, and regulated environments.
            </p>
        </body>
        </html>
        """

        text_body = f"""
Thank you for your interest in UAPK Gateway!

Hi {lead.name},

We've received your inquiry about deploying AI agents safely.

What happens next:
1. We'll review your use case within 24 hours
2. Schedule a discovery call
3. Provide a custom proposal

Your submission:
- Company: {lead.company}
- Use Case: {lead.use_case[:200]}
- Timeline: {lead.timeline or 'Not specified'}
- Budget: {lead.budget or 'Not specified'}

Best regards,
UAPK Gateway Team
https://uapk.info
        """

        return self.send_email(lead.email, subject, html_body, text_body)

    def send_admin_notification(self, lead: Any) -> bool:
        """Send notification to admin about new lead."""
        subject = f"🎯 New Lead: {lead.company} ({lead.budget or 'budget TBD'})"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #10b981;">New Lead Submitted!</h2>

            <table style="border-collapse: collapse; width: 100%; margin: 1rem 0;">
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Name:</td>
                    <td style="padding: 0.5rem;">{lead.name}</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Email:</td>
                    <td style="padding: 0.5rem;"><a href="mailto:{lead.email}">{lead.email}</a></td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Company:</td>
                    <td style="padding: 0.5rem;">{lead.company}</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Role:</td>
                    <td style="padding: 0.5rem;">{lead.role or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Timeline:</td>
                    <td style="padding: 0.5rem;"><strong>{lead.timeline or 'Not specified'}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem; font-weight: bold; background: #f3f4f6;">Budget:</td>
                    <td style="padding: 0.5rem;"><strong>{lead.budget or 'Not specified'}</strong></td>
                </tr>
            </table>

            <p><strong>Use Case:</strong></p>
            <p style="padding: 1rem; background: #f3f4f6; border-left: 4px solid #2563eb;">
                {lead.use_case}
            </p>

            <p><strong>Quick Actions:</strong></p>
            <p>
                <a href="http://34.171.83.82:8000/admin"
                   style="display: inline-block; padding: 0.75rem 1.5rem; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin-right: 1rem;">
                    View in Dashboard
                </a>
                <a href="mailto:{lead.email}?subject=Re: UAPK Gateway Pilot Program"
                   style="display: inline-block; padding: 0.75rem 1.5rem; background: #10b981; color: white; text-decoration: none; border-radius: 6px;">
                    Reply to Lead
                </a>
            </p>

            <hr style="margin: 2rem 0; border: none; border-top: 1px solid #e2e8f0;">

            <p style="font-size: 0.9rem; color: #64748b;">
                Lead submitted: {lead.created_at}<br>
                Lead ID: {lead.id}
            </p>
        </body>
        </html>
        """

        return self.send_email(self.admin_email, subject, html_body)


# Singleton instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get the email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
