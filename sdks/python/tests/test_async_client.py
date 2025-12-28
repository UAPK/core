"""Tests for asynchronous AsyncUAPKGatewayClient."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx

from uapk_gateway import AsyncUAPKGatewayClient
from uapk_gateway.models import ActionInfo
from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ToolExecutionError,
    ValidationError,
)


pytestmark = pytest.mark.asyncio


class TestAsyncClientInitialization:
    """Test async client initialization."""

    async def test_client_init(self):
        """Test basic async client initialization."""
        client = AsyncUAPKGatewayClient(
            base_url="http://localhost:8000",
            api_key="test-key",
        )
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test-key"
        assert client.timeout == 30
        await client.close()

    async def test_context_manager(self):
        """Test async client as context manager."""
        async with AsyncUAPKGatewayClient(
            base_url="http://localhost:8000", api_key="test"
        ) as client:
            assert client is not None
        # Client should be closed after context exit


class TestAsyncEvaluate:
    """Test async evaluate method."""

    async def test_evaluate_success(self, async_client, mock_gateway, sample_action):
        """Test successful async action evaluation."""
        response = await async_client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        assert response.interaction_id == "int_test_123"
        assert len(response.reasons) > 0

    async def test_evaluate_with_all_params(
        self, async_client, mock_gateway, sample_action, sample_counterparty
    ):
        """Test evaluation with all parameters."""
        response = await async_client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            counterparty=sample_counterparty,
            context={"key": "value"},
            capability_token="cap_xyz",
        )

        assert response.decision == "ALLOW"

        # Check all params were sent
        call = mock_gateway.call_history[0]
        assert "counterparty" in call["data"]
        assert "context" in call["data"]
        assert "capability_token" in call["data"]

    async def test_concurrent_evaluations(self, async_client, mock_gateway, sample_action):
        """Test concurrent action evaluations."""
        # Create multiple actions
        tasks = [
            async_client.evaluate(
                uapk_id="test-uapk-v1",
                agent_id=f"agent-{i}",
                action=sample_action,
            )
            for i in range(5)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r.decision == "ALLOW" for r in results)
        assert len(mock_gateway.call_history) == 5


class TestAsyncExecute:
    """Test async execute method."""

    async def test_execute_success(self, async_client, mock_gateway, sample_action):
        """Test successful async action execution."""
        response = await async_client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        assert response.executed is True
        assert response.result is not None
        assert response.result.success is True

    async def test_execute_deny_raises(
        self, async_client, mock_gateway, sample_action, execute_deny_response
    ):
        """Test execute raises ActionDeniedError on DENY."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        with pytest.raises(ActionDeniedError) as exc_info:
            await async_client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_deny=True,
            )

        error = exc_info.value
        assert "denied" in str(error).lower()

    async def test_execute_deny_no_raise(
        self, async_client, mock_gateway, sample_action, execute_deny_response
    ):
        """Test execute returns response on DENY when raise_on_deny=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        response = await async_client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_deny=False,
        )

        assert response.decision == "DENY"
        assert response.executed is False

    async def test_execute_escalate_raises(
        self, async_client, mock_gateway, sample_action, execute_escalate_response
    ):
        """Test execute raises ActionEscalatedError on ESCALATE."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        with pytest.raises(ActionEscalatedError) as exc_info:
            await async_client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_escalate=True,
            )

        error = exc_info.value
        assert error.approval_id == "appr_123"

    async def test_execute_escalate_no_raise(
        self, async_client, mock_gateway, sample_action, execute_escalate_response
    ):
        """Test execute returns response on ESCALATE when raise_on_escalate=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        response = await async_client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_escalate=False,
        )

        assert response.decision == "ESCALATE"
        assert response.approval_id == "appr_123"

    async def test_execute_tool_error_raises(
        self, async_client, mock_gateway, sample_action, tool_error_response
    ):
        """Test execute raises ToolExecutionError on tool failure."""
        mock_gateway.set_response("/api/v1/gateway/execute", tool_error_response)

        with pytest.raises(ToolExecutionError):
            await async_client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_tool_error=True,
            )

    async def test_execute_tool_error_no_raise(
        self, async_client, mock_gateway, sample_action, tool_error_response
    ):
        """Test execute returns response on tool error when raise_on_tool_error=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", tool_error_response)

        response = await async_client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_tool_error=False,
        )

        assert response.result.success is False
        assert response.result.error is not None


class TestAsyncApprovalWorkflow:
    """Test async approval workflow methods."""

    async def test_get_approval_status(self, async_client, mock_gateway):
        """Test getting approval status asynchronously."""
        approval_response = {
            "id": "appr_123",
            "status": "APPROVED",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "override_token": "override_xyz",
        }
        mock_gateway.set_response("/api/v1/approvals/appr_123", approval_response)

        approval = await async_client.get_approval_status("appr_123")

        assert approval["id"] == "appr_123"
        assert approval["status"] == "APPROVED"

    async def test_execute_with_retry_on_escalate_immediate_allow(
        self, async_client, mock_gateway, sample_action
    ):
        """Test execute_with_retry_on_escalate when action is immediately allowed."""
        response = await async_client.execute_with_retry_on_escalate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        # Should only call execute once
        assert len(mock_gateway.call_history) == 1

    async def test_execute_with_retry_on_escalate_approval_flow(
        self, async_client, mock_gateway, sample_action, execute_escalate_response
    ):
        """Test execute_with_retry_on_escalate with approval workflow."""
        # First call: ESCALATE
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        # Approval status: APPROVED
        approval_response = {
            "id": "appr_123",
            "status": "APPROVED",
            "override_token": "override_xyz",
        }
        mock_gateway.set_response("/api/v1/approvals/appr_123", approval_response)

        # Second execute call: ALLOW (with override token)
        def get_execute_response(method, endpoint, data):
            if data and "override_token" in data:
                return {
                    "interaction_id": "int_approved_123",
                    "decision": "ALLOW",
                    "reasons": [{"code": "POLICY_ALLOWS", "message": "Approved", "details": None}],
                    "timestamp": "2024-01-01T00:00:00Z",
                    "policy_version": "v1.0.0",
                    "executed": True,
                    "result": {"success": True, "data": {"output": "Success"}},
                }
            return execute_escalate_response

        original_get_response = mock_gateway.get_response

        def custom_get_response(method, endpoint, data):
            if endpoint == "/api/v1/gateway/execute":
                return get_execute_response(method, endpoint, data)
            return original_get_response(method, endpoint, data)

        mock_gateway.get_response = custom_get_response

        response = await async_client.execute_with_retry_on_escalate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            poll_interval=0.1,
            max_wait=10,
        )

        assert response.decision == "ALLOW"
        assert response.executed is True

    async def test_execute_with_retry_on_escalate_denied(
        self, async_client, mock_gateway, sample_action, execute_escalate_response
    ):
        """Test execute_with_retry_on_escalate when approval is denied."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        # Approval status: DENIED
        approval_response = {"id": "appr_123", "status": "DENIED"}
        mock_gateway.set_response("/api/v1/approvals/appr_123", approval_response)

        with pytest.raises(ActionDeniedError):
            await async_client.execute_with_retry_on_escalate(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                poll_interval=0.1,
                max_wait=10,
            )


class TestAsyncErrorHandling:
    """Test async error handling."""

    async def test_authentication_error(self):
        """Test handling of 401 authentication error."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock 401 response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.request.return_value = mock_response

            client = AsyncUAPKGatewayClient(base_url="http://localhost:8000", api_key="invalid")

            with pytest.raises(AuthenticationError):
                await client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            await client.close()

    async def test_validation_error(self):
        """Test handling of 422 validation error."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock 422 response
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {"detail": "Invalid request"}
            mock_client.request.return_value = mock_response

            client = AsyncUAPKGatewayClient(base_url="http://localhost:8000", api_key="test")

            with pytest.raises(ValidationError):
                await client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            await client.close()

    async def test_rate_limit_error(self):
        """Test handling of 429 rate limit error."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock 429 response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_client.request.return_value = mock_response

            client = AsyncUAPKGatewayClient(base_url="http://localhost:8000", api_key="test")

            with pytest.raises(RateLimitError) as exc_info:
                await client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            assert exc_info.value.retry_after == 60
            await client.close()

    async def test_server_error_with_retry(self):
        """Test server error handling with retry."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            call_count = [0]

            async def mock_request(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] < 3:
                    mock_response = Mock()
                    mock_response.status_code = 500
                    mock_response.text = "Internal Server Error"
                    return mock_response
                else:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "interaction_id": "int_123",
                        "decision": "ALLOW",
                        "reasons": [{"code": "POLICY_ALLOWS", "message": "OK", "details": None}],
                        "timestamp": "2024-01-01T00:00:00Z",
                        "policy_version": "v1.0.0",
                    }
                    return mock_response

            mock_client.request.side_effect = mock_request

            client = AsyncUAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=3,
                retry_backoff=0.01,
            )

            response = await client.evaluate(
                uapk_id="test",
                agent_id="test",
                action=ActionInfo(type="test", tool="test", params={}),
            )

            assert response.decision == "ALLOW"
            assert call_count[0] == 3

            await client.close()

    async def test_network_error(self):
        """Test network error handling."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_client.request.side_effect = httpx.RequestError("Connection failed")

            client = AsyncUAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=1,
            )

            with pytest.raises(NetworkError):
                await client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            await client.close()

    async def test_timeout_error(self):
        """Test timeout error handling."""
        with patch("uapk_gateway.async_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

            client = AsyncUAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=1,
            )

            with pytest.raises(NetworkError) as exc_info:
                await client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            assert "timeout" in str(exc_info.value).lower()
            await client.close()


class TestAsyncConcurrency:
    """Test async client concurrency patterns."""

    async def test_batch_execution(self, async_client, mock_gateway, sample_action):
        """Test batch execution with concurrency."""
        # Create batch of actions
        tasks = [
            async_client.execute(
                uapk_id="test-uapk-v1",
                agent_id=f"agent-{i}",
                action=sample_action,
                raise_on_deny=False,
                raise_on_escalate=False,
            )
            for i in range(10)
        ]

        # Execute all concurrently
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.decision == "ALLOW" for r in results)

    async def test_mixed_results_batch(
        self, async_client, mock_gateway, sample_action, execute_deny_response
    ):
        """Test batch execution with mixed results."""
        # Some succeed, some denied
        def get_response(method, endpoint, data):
            if data and data.get("agent_id", "").endswith("5"):
                return execute_deny_response
            return mock_gateway._default_execute_response()

        original_get_response = mock_gateway.get_response

        def custom_get_response(method, endpoint, data):
            if endpoint == "/api/v1/gateway/execute":
                return get_response(method, endpoint, data)
            return original_get_response(method, endpoint, data)

        mock_gateway.get_response = custom_get_response

        tasks = [
            async_client.execute(
                uapk_id="test-uapk-v1",
                agent_id=f"agent-{i}",
                action=sample_action,
                raise_on_deny=False,
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # Check we got mix of ALLOW and DENY
        allow_count = sum(1 for r in results if r.decision == "ALLOW")
        deny_count = sum(1 for r in results if r.decision == "DENY")

        assert allow_count == 9
        assert deny_count == 1
