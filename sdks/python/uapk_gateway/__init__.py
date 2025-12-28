"""UAPK Gateway Python SDK.

Official Python SDK for UAPK Gateway - the compliance and audit control plane for AI agents.

Example:
    >>> from uapk_gateway import UAPKGatewayClient
    >>> from uapk_gateway.models import ActionInfo
    >>>
    >>> client = UAPKGatewayClient(
    ...     base_url="https://gateway.yourcompany.com",
    ...     api_key="your-api-key"
    ... )
    >>>
    >>> response = client.execute(
    ...     uapk_id="refund-bot-v1",
    ...     agent_id="agent-123",
    ...     action=ActionInfo(
    ...         type="refund",
    ...         tool="stripe_api",
    ...         params={"charge_id": "ch_123", "amount": 1000}
    ...     )
    ... )
    >>>
    >>> print(response.decision)  # ALLOW, DENY, or ESCALATE
"""

from uapk_gateway.client import UAPKGatewayClient
from uapk_gateway.async_client import AsyncUAPKGatewayClient
from uapk_gateway.models import (
    ActionInfo,
    CounterpartyInfo,
    GatewayActionRequest,
    GatewayDecision,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
    ReasonCode,
    ReasonDetail,
    ToolResult,
)
from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ToolExecutionError,
    UAPKGatewayError,
    ValidationError,
)

__version__ = "1.0.0"

__all__ = [
    # Clients
    "UAPKGatewayClient",
    "AsyncUAPKGatewayClient",
    # Models
    "ActionInfo",
    "CounterpartyInfo",
    "GatewayActionRequest",
    "GatewayDecision",
    "GatewayDecisionResponse",
    "GatewayExecuteResponse",
    "ReasonCode",
    "ReasonDetail",
    "ToolResult",
    # Exceptions
    "UAPKGatewayError",
    "AuthenticationError",
    "ActionDeniedError",
    "ActionEscalatedError",
    "ToolExecutionError",
    "NetworkError",
    "ValidationError",
    "RateLimitError",
]
