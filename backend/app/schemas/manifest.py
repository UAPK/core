"""Pydantic schemas for UAPK manifests."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.uapk_manifest import ManifestStatus


class AgentInfo(BaseModel):
    """Agent identification from manifest."""

    id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+")
    description: str | None = Field(None, max_length=500)
    organization: str | None = Field(None, pattern=r"^org-[a-z0-9-]+$")
    team: str | None = Field(None, pattern=r"^team-[a-z0-9-]+$")


class CapabilityDeclaration(BaseModel):
    """Capability declarations from manifest."""

    requested: list[str] = Field(..., min_length=1)


class ManifestConstraints(BaseModel):
    """Self-imposed constraints from manifest."""

    max_actions_per_hour: int | None = Field(None, ge=1)
    max_actions_per_day: int | None = Field(None, ge=1)
    require_human_approval: list[str] | None = None
    allowed_hours: dict[str, Any] | None = None


class ManifestMetadata(BaseModel):
    """Additional manifest metadata."""

    contact: str | None = None
    documentation: str | None = None
    source: str | None = None


# NEW: Policy configuration for gateway decisions
class BudgetConfig(BaseModel):
    """Budget configuration for an action type."""

    daily_limit: int | None = Field(None, ge=0, description="Maximum actions per day")
    hourly_limit: int | None = Field(None, ge=0, description="Maximum actions per hour")
    total_limit: int | None = Field(None, ge=0, description="Total lifetime actions")


class ApprovalThreshold(BaseModel):
    """Configuration for when to require human approval."""

    amount: float | None = Field(None, ge=0, description="Require approval for amounts above this")
    currency: str | None = Field(None, description="Currency for amount threshold (e.g., 'USD')")
    action_types: list[str] | None = Field(
        None, description="Require approval for these action types"
    )
    tools: list[str] | None = Field(None, description="Require approval for these tools")


class PolicyConfig(BaseModel):
    """Policy configuration for gateway enforcement.

    Defines rules that the gateway's PolicyEngine uses to make
    ALLOW/DENY/ESCALATE decisions.
    """

    # Budget limits (e.g., {"send_email": {"daily_limit": 50}})
    budgets: dict[str, BudgetConfig] | None = Field(
        None, description="Budget limits per action type"
    )

    # Counterparty rules
    counterparty_allowlist: list[str] | None = Field(
        None, description="Only allow these counterparties (domain suffixes)"
    )
    counterparty_denylist: list[str] | None = Field(
        None, description="Block these counterparties (domain suffixes)"
    )

    # Jurisdiction rules
    jurisdiction_allowlist: list[str] | None = Field(
        None, description="Only allow these jurisdictions (ISO country codes)"
    )

    # Tool rules
    tool_allowlist: list[str] | None = Field(None, description="Only allow these tools")
    tool_denylist: list[str] | None = Field(None, description="Block these tools")

    # Amount caps (e.g., {"USD": 10000.0})
    amount_caps: dict[str, float] | None = Field(
        None, description="Maximum amounts per currency/unit"
    )

    # Approval thresholds - actions that require human approval
    approval_thresholds: ApprovalThreshold | None = Field(
        None, description="Configuration for actions that require human approval"
    )

    # Capability token enforcement
    require_capability_token: bool = Field(
        False, description="Require valid capability token for all actions"
    )

    model_config = ConfigDict(extra="forbid")


# NEW: Tool connector configuration
class ToolConfig(BaseModel):
    """Configuration for a tool connector.

    Defines how the gateway executes actions using external systems.
    """

    type: str = Field(
        ...,
        description="Connector type: 'http_request', 'webhook', 'mock'",
        pattern=r"^(http_request|webhook|mock)$",
    )

    # Connector-specific configuration
    config: dict[str, Any] = Field(..., description="Connector-specific configuration")

    # Examples:
    # - http_request: {"method": "POST", "url": "...", "allowed_domains": [...]}
    # - webhook: {"url": "...", "method": "POST", "allowed_domains": [...]}
    # - mock: {"response_data": {...}}

    model_config = ConfigDict(extra="forbid")


class ManifestContent(BaseModel):
    """The actual UAPK manifest content.

    Extended schema that includes policy rules and tool configurations
    for gateway execution.
    """

    version: str = Field("1.0", pattern=r"^1\.0$")
    agent: AgentInfo
    capabilities: CapabilityDeclaration
    constraints: ManifestConstraints | None = None
    metadata: ManifestMetadata | None = None

    # NEW: Policy and tools for gateway execution
    policy: PolicyConfig | None = Field(
        None, description="Policy rules for gateway enforcement"
    )
    tools: dict[str, ToolConfig] | None = Field(
        None, description="Tool connector configurations (tool_name -> config)"
    )

    model_config = ConfigDict(extra="forbid")  # Strict validation


class ManifestCreate(BaseModel):
    """Request body for registering a manifest."""

    org_id: UUID
    manifest: ManifestContent
    description: str | None = Field(None, max_length=500)


class ManifestUpdate(BaseModel):
    """Request body for updating a manifest status."""

    status: ManifestStatus | None = None
    description: str | None = Field(None, max_length=500)


class ManifestResponse(BaseModel):
    """Response containing manifest information."""

    id: UUID
    org_id: UUID
    uapk_id: str
    version: str
    manifest_json: dict[str, Any]
    manifest_hash: str
    status: ManifestStatus
    description: str | None
    created_at: datetime
    created_by_user_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class ManifestList(BaseModel):
    """Response containing list of manifests."""

    items: list[ManifestResponse]
    total: int
