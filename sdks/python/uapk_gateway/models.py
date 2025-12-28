"""Pydantic models for UAPK Gateway SDK."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GatewayDecision(str, Enum):
    """Gateway decision result."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class ReasonCode(str, Enum):
    """Reason codes for gateway decisions."""

    MANIFEST_NOT_FOUND = "MANIFEST_NOT_FOUND"
    MANIFEST_INACTIVE = "MANIFEST_INACTIVE"
    ACTION_TYPE_DENIED = "ACTION_TYPE_DENIED"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    AMOUNT_CAP_EXCEEDED = "AMOUNT_CAP_EXCEEDED"
    JURISDICTION_DENIED = "JURISDICTION_DENIED"
    COUNTERPARTY_DENIED = "COUNTERPARTY_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CAPABILITY_TOKEN_INVALID = "CAPABILITY_TOKEN_INVALID"
    CAPABILITY_TOKEN_EXPIRED = "CAPABILITY_TOKEN_EXPIRED"
    OVERRIDE_TOKEN_ALREADY_USED = "OVERRIDE_TOKEN_ALREADY_USED"
    POLICY_ALLOWS = "POLICY_ALLOWS"


class ActionInfo(BaseModel):
    """Information about the action being requested."""

    type: str = Field(..., description="Action type (e.g., 'refund', 'send_email')")
    tool: str = Field(..., description="Tool/connector to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    amount: float | None = Field(None, description="Transaction amount (if applicable)")
    currency: str | None = Field(None, description="Currency code (if applicable)")
    description: str | None = Field(None, description="Human-readable description")


class CounterpartyInfo(BaseModel):
    """Information about the counterparty (recipient/target)."""

    id: str | None = Field(None, description="Counterparty identifier")
    name: str | None = Field(None, description="Counterparty name")
    email: str | None = Field(None, description="Email address")
    domain: str | None = Field(None, description="Domain name")
    jurisdiction: str | None = Field(None, description="Jurisdiction/country code")


class ReasonDetail(BaseModel):
    """Detailed reason for a decision."""

    code: ReasonCode
    message: str
    details: dict[str, Any] | None = None


class GatewayActionRequest(BaseModel):
    """Request to evaluate or execute an action."""

    uapk_id: str = Field(..., description="UAPK manifest ID")
    agent_id: str = Field(..., description="Agent instance identifier")
    action: ActionInfo = Field(..., description="Action to perform")
    counterparty: CounterpartyInfo | None = Field(None, description="Counterparty information")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    capability_token: str | None = Field(None, description="Capability token (if delegated)")
    override_token: str | None = Field(None, description="Override token from approval")


class GatewayDecisionResponse(BaseModel):
    """Response from evaluate endpoint."""

    interaction_id: str
    decision: GatewayDecision
    reasons: list[ReasonDetail]
    approval_id: str | None = None
    timestamp: datetime
    policy_version: str


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    result_hash: str | None = None
    duration_ms: int | None = None


class GatewayExecuteResponse(BaseModel):
    """Response from execute endpoint."""

    interaction_id: str
    decision: GatewayDecision
    reasons: list[ReasonDetail]
    approval_id: str | None = None
    timestamp: datetime
    policy_version: str
    executed: bool
    result: ToolResult | None = None
