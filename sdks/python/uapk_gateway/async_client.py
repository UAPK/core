"""Asynchronous UAPK Gateway client."""

import asyncio
from typing import Any
from urllib.parse import urljoin

import httpx

from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ToolExecutionError,
    ValidationError,
)
from uapk_gateway.models import (
    ActionInfo,
    CounterpartyInfo,
    GatewayActionRequest,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
)


class AsyncUAPKGatewayClient:
    """Asynchronous client for UAPK Gateway.

    Example:
        >>> async with AsyncUAPKGatewayClient(
        ...     base_url="https://gateway.yourcompany.com",
        ...     api_key="your-api-key"
        ... ) as client:
        ...     result = await client.execute(
        ...         uapk_id="refund-bot-v1",
        ...         agent_id="agent-123",
        ...         action=ActionInfo(
        ...             type="refund",
        ...             tool="stripe_api",
        ...             params={"charge_id": "ch_123", "amount": 1000}
        ...         )
        ...     )
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        """Initialize the async UAPK Gateway client.

        Args:
            base_url: Base URL of the gateway
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff multiplier for retries
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "X-API-Key": api_key,
                "User-Agent": "uapk-gateway-python-sdk/1.0.0",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        retry_count: int = 0,
    ) -> dict:
        """Make async HTTP request with retry logic and error handling."""
        url = urljoin(self.base_url, endpoint)

        try:
            response = await self._client.request(method, url, json=json_data)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    retry_after=retry_after,
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or authentication failed")

            # Handle validation errors
            if response.status_code == 422:
                error_detail = response.json().get("detail", "Validation error")
                raise ValidationError(f"Request validation failed: {error_detail}")

            # Handle server errors with retry
            if response.status_code >= 500:
                if retry_count < self.max_retries:
                    wait_time = self.retry_backoff * (2**retry_count)
                    await asyncio.sleep(wait_time)
                    return await self._make_request(method, endpoint, json_data, retry_count + 1)

                raise NetworkError(
                    f"Gateway server error: {response.status_code} - {response.text}"
                )

            if response.status_code >= 400:
                error_detail = response.json().get("detail", response.text)
                raise NetworkError(f"Gateway error: {response.status_code} - {error_detail}")

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_backoff * (2**retry_count)
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, json_data, retry_count + 1)

            raise NetworkError(f"Request timeout after {self.timeout}s") from e

        except httpx.RequestError as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_backoff * (2**retry_count)
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, json_data, retry_count + 1)

            raise NetworkError(f"Network error: {str(e)}") from e

    async def evaluate(
        self,
        uapk_id: str,
        agent_id: str,
        action: ActionInfo,
        counterparty: CounterpartyInfo | None = None,
        context: dict[str, Any] | None = None,
        capability_token: str | None = None,
    ) -> GatewayDecisionResponse:
        """Evaluate an action without executing (dry-run).

        Args:
            uapk_id: UAPK manifest ID
            agent_id: Agent instance identifier
            action: Action to evaluate
            counterparty: Counterparty information (optional)
            context: Additional context (optional)
            capability_token: Capability token (optional)

        Returns:
            GatewayDecisionResponse with decision and reasons
        """
        request = GatewayActionRequest(
            uapk_id=uapk_id,
            agent_id=agent_id,
            action=action,
            counterparty=counterparty,
            context=context or {},
            capability_token=capability_token,
        )

        response_data = await self._make_request(
            "POST",
            "/api/v1/gateway/evaluate",
            json_data=request.model_dump(exclude_none=True),
        )

        return GatewayDecisionResponse(**response_data)

    async def execute(
        self,
        uapk_id: str,
        agent_id: str,
        action: ActionInfo,
        counterparty: CounterpartyInfo | None = None,
        context: dict[str, Any] | None = None,
        capability_token: str | None = None,
        override_token: str | None = None,
        raise_on_deny: bool = True,
        raise_on_escalate: bool = False,
        raise_on_tool_error: bool = True,
    ) -> GatewayExecuteResponse:
        """Execute an action through the gateway.

        Args:
            uapk_id: UAPK manifest ID
            agent_id: Agent instance identifier
            action: Action to execute
            counterparty: Counterparty information (optional)
            context: Additional context (optional)
            capability_token: Capability token (optional)
            override_token: Override token from approval (optional)
            raise_on_deny: Raise ActionDeniedError if denied
            raise_on_escalate: Raise ActionEscalatedError if escalated
            raise_on_tool_error: Raise ToolExecutionError if tool fails

        Returns:
            GatewayExecuteResponse with decision and result
        """
        request = GatewayActionRequest(
            uapk_id=uapk_id,
            agent_id=agent_id,
            action=action,
            counterparty=counterparty,
            context=context or {},
            capability_token=capability_token,
            override_token=override_token,
        )

        response_data = await self._make_request(
            "POST",
            "/api/v1/gateway/execute",
            json_data=request.model_dump(exclude_none=True),
        )

        response = GatewayExecuteResponse(**response_data)

        # Handle DENY
        if response.decision == "DENY" and raise_on_deny:
            reasons_str = ", ".join([r.message for r in response.reasons])
            raise ActionDeniedError(
                f"Action denied by gateway: {reasons_str}",
                decision_response=response_data,
            )

        # Handle ESCALATE
        if response.decision == "ESCALATE" and raise_on_escalate:
            reasons_str = ", ".join([r.message for r in response.reasons])
            raise ActionEscalatedError(
                f"Action requires approval: {reasons_str} (approval_id: {response.approval_id})",
                decision_response=response_data,
            )

        # Handle tool execution errors
        if (
            response.executed
            and response.result
            and not response.result.success
            and raise_on_tool_error
        ):
            error_msg = response.result.error.get("message", "Unknown error") if response.result.error else "Unknown error"
            raise ToolExecutionError(
                f"Tool execution failed: {error_msg}",
                tool_result=response.result.model_dump(),
            )

        return response

    async def execute_with_retry_on_escalate(
        self,
        uapk_id: str,
        agent_id: str,
        action: ActionInfo,
        counterparty: CounterpartyInfo | None = None,
        context: dict[str, Any] | None = None,
        capability_token: str | None = None,
        poll_interval: int = 5,
        max_wait: int = 300,
    ) -> GatewayExecuteResponse:
        """Execute an action and wait for approval if escalated.

        Args:
            uapk_id: UAPK manifest ID
            agent_id: Agent instance identifier
            action: Action to execute
            counterparty: Counterparty information (optional)
            context: Additional context (optional)
            capability_token: Capability token (optional)
            poll_interval: How often to check approval status (seconds)
            max_wait: Maximum time to wait for approval (seconds)

        Returns:
            GatewayExecuteResponse after approval
        """
        # First attempt
        try:
            return await self.execute(
                uapk_id=uapk_id,
                agent_id=agent_id,
                action=action,
                counterparty=counterparty,
                context=context,
                capability_token=capability_token,
                raise_on_escalate=True,
            )
        except ActionEscalatedError as e:
            approval_id = e.approval_id

        # Wait for approval
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < max_wait:
            # Check approval status
            approval_data = await self._make_request("GET", f"/api/v1/approvals/{approval_id}")

            status = approval_data.get("status")
            if status == "APPROVED":
                override_token = approval_data.get("override_token")
                # Retry with override token
                return await self.execute(
                    uapk_id=uapk_id,
                    agent_id=agent_id,
                    action=action,
                    counterparty=counterparty,
                    context=context,
                    override_token=override_token,
                )

            if status == "DENIED":
                raise ActionDeniedError(
                    "Approval was denied",
                    decision_response={"approval_id": approval_id},
                )

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Approval not granted within {max_wait} seconds")

    async def get_approval_status(self, approval_id: str) -> dict:
        """Get the status of an approval.

        Args:
            approval_id: Approval ID from ESCALATE response

        Returns:
            Approval details
        """
        return await self._make_request("GET", f"/api/v1/approvals/{approval_id}")
