"""
Policy Engine
Enforces guardrails, tool permissions, rate limits, and approval gates.
"""
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timedelta
from collections import defaultdict

from uapk.manifest_schema import UAPKManifest
from uapk.audit import audit_event

# M1.1: Override token validation
from uapk.core.ed25519_token import verify_override_token, hash_override_token


PolicyDecision = Literal["ALLOW", "DENY", "ESCALATE"]


class PolicyResult:
    """Result of policy evaluation"""

    def __init__(
        self,
        decision: PolicyDecision,
        reasons: List[str],
        requires_approval: bool = False
    ):
        self.decision = decision
        self.reasons = reasons
        self.requires_approval = requires_approval


class PolicyEngine:
    """
    Enforces policy guardrails from the UAPK manifest.
    Checks:
    1. Tool permissions (agent allowed to use tool)
    2. Deny rules
    3. Rate limits
    4. Live action gates (requires approval in dry_run mode)
    5. Execution mode constraints
    """

    def __init__(self, manifest: UAPKManifest):
        self.manifest = manifest
        self.guardrails = manifest.corporateModules.policyGuardrails

        # Rate limiting state (in-memory; would use Redis in production)
        self.rate_limit_counters: Dict[str, List[datetime]] = defaultdict(list)

    def evaluate(
        self,
        agent_id: Optional[str],
        action: str,
        tool: Optional[str] = None,
        user_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        override_token: Optional[str] = None,  # M1.1: Override token support
        session: Optional[Any] = None  # M1.1: Database session for consumption tracking
    ) -> PolicyResult:
        """
        Evaluate whether an action should be allowed.
        Returns PolicyResult with decision and reasons.

        M1.1: If override_token provided, validates it and grants ALLOW if valid.
        Override tokens are Ed25519-signed, short-lived (5min), single-use tokens
        issued by HITL approval flow.
        """
        reasons: List[str] = []

        # M1.1: Step 1 - Override Token Validation (bypasses other checks if valid)
        if override_token:
            from uapk.db.models import HITLRequest
            from sqlmodel import select

            valid, reason, payload = verify_override_token(override_token, action, params or {})

            if not valid:
                audit_event(
                    event_type="policy_check",
                    action=action,
                    params=params,
                    decision="DENY",
                    agent_id=agent_id,
                    user_id=user_id
                )
                return PolicyResult(
                    decision="DENY",
                    reasons=[f"Override token invalid: {reason}"]
                )

            # Token signature and expiry valid, now check consumption
            approval_id = payload['approval_id']

            # Atomic consumption check (requires database session)
            if session:
                # Load HITLRequest with SELECT FOR UPDATE (lock row)
                statement = select(HITLRequest).where(HITLRequest.id == approval_id).with_for_update()
                hitl = session.exec(statement).first()

                if not hitl:
                    return PolicyResult(
                        decision="DENY",
                        reasons=[f"Override token approval_id {approval_id} not found"]
                    )

                if hitl.consumed_at is not None:
                    return PolicyResult(
                        decision="DENY",
                        reasons=[f"Override token already consumed at {hitl.consumed_at.isoformat()}Z"]
                    )

                # Mark as consumed (one-time-use enforcement)
                hitl.consumed_at = datetime.utcnow()
                session.add(hitl)
                session.commit()

            # Override token valid and consumed → ALLOW
            reasons.append(f"Override token valid (approval_id={approval_id})")
            audit_event(
                event_type="policy_check",
                action=action,
                params=params,
                decision="ALLOW",
                agent_id=agent_id,
                user_id=user_id
            )
            return PolicyResult(decision="ALLOW", reasons=reasons)

        # Check 1: Tool permissions
        if agent_id and tool:
            allowed_tools = self.guardrails.toolPermissions.get(agent_id, [])
            if tool not in allowed_tools:
                audit_event(
                    event_type="policy_check",
                    action=action,
                    params=params,
                    decision="DENY",
                    agent_id=agent_id,
                    user_id=user_id
                )
                return PolicyResult(
                    decision="DENY",
                    reasons=[f"Agent {agent_id} not permitted to use tool {tool}"]
                )

        # Check 2: Deny rules
        for deny_rule in self.guardrails.denyRules:
            if deny_rule in action:
                audit_event(
                    event_type="policy_check",
                    action=action,
                    params=params,
                    decision="DENY",
                    agent_id=agent_id,
                    user_id=user_id
                )
                return PolicyResult(
                    decision="DENY",
                    reasons=[f"Action matches deny rule: {deny_rule}"]
                )

        # Check 3: Rate limits
        rate_limit_key = agent_id or user_id or "global"
        if not self._check_rate_limit(rate_limit_key):
            audit_event(
                event_type="policy_check",
                action=action,
                params=params,
                decision="DENY",
                agent_id=agent_id,
                user_id=user_id
            )
            return PolicyResult(
                decision="DENY",
                reasons=["Rate limit exceeded"]
            )

        # Check 4: Live action gates
        if action in self.guardrails.liveActionGates:
            if self.manifest.executionMode == "dry_run":
                # In dry_run, live actions require approval
                audit_event(
                    event_type="policy_check",
                    action=action,
                    params=params,
                    decision="ESCALATE",
                    agent_id=agent_id,
                    user_id=user_id
                )
                return PolicyResult(
                    decision="ESCALATE",
                    reasons=[f"Action '{action}' requires approval in dry_run mode"],
                    requires_approval=True
                )

        # Check 5: Execution mode
        if self.manifest.executionMode == "dry_run":
            # Additional checks for dry_run mode
            if action.startswith("charge_") or action.startswith("send_email_"):
                audit_event(
                    event_type="policy_check",
                    action=action,
                    params=params,
                    decision="ESCALATE",
                    agent_id=agent_id,
                    user_id=user_id
                )
                return PolicyResult(
                    decision="ESCALATE",
                    reasons=[f"Potentially destructive action in dry_run mode"],
                    requires_approval=True
                )

        # ALLOW
        reasons.append("All policy checks passed")
        audit_event(
            event_type="policy_check",
            action=action,
            params=params,
            decision="ALLOW",
            agent_id=agent_id,
            user_id=user_id
        )

        return PolicyResult(decision="ALLOW", reasons=reasons)

    def _check_rate_limit(self, key: str) -> bool:
        """
        Check if rate limit is exceeded for this key.
        Uses sliding window of 1 minute.
        """
        limit = self.guardrails.rateLimits.get("actionsPerMinute", 100)
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)

        # Clean old entries
        self.rate_limit_counters[key] = [
            ts for ts in self.rate_limit_counters[key]
            if ts > window_start
        ]

        # Check limit
        if len(self.rate_limit_counters[key]) >= limit:
            return False

        # Add current request
        self.rate_limit_counters[key].append(now)
        return True


# Global policy engine instance
_policy_engine: Optional[PolicyEngine] = None


def init_policy_engine(manifest: UAPKManifest):
    """Initialize the global policy engine"""
    global _policy_engine
    _policy_engine = PolicyEngine(manifest)


def get_policy_engine() -> PolicyEngine:
    """Get the global policy engine instance"""
    if _policy_engine is None:
        raise RuntimeError("Policy engine not initialized. Call init_policy_engine first.")
    return _policy_engine


def check_policy(
    agent_id: Optional[str],
    action: str,
    tool: Optional[str] = None,
    user_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    override_token: Optional[str] = None,  # M1.1
    session: Optional[Any] = None  # M1.1
) -> PolicyResult:
    """Convenience function to check policy"""
    return get_policy_engine().evaluate(
        agent_id=agent_id,
        action=action,
        tool=tool,
        user_id=user_id,
        params=params,
        override_token=override_token,
        session=session
    )
