"""Tests for synchronous UAPKGatewayClient."""

import pytest
import time
from unittest.mock import Mock, patch
import httpx

from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo, CounterpartyInfo
from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ToolExecutionError,
    ValidationError,
)


class TestClientInitialization:
    """Test client initialization."""

    def test_client_init(self):
        """Test basic client initialization."""
        client = UAPKGatewayClient(
            base_url="http://localhost:8000",
            api_key="test-key",
        )
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test-key"
        assert client.timeout == 30
        assert client.max_retries == 3
        client.close()

    def test_client_init_custom_params(self):
        """Test client initialization with custom parameters."""
        client = UAPKGatewayClient(
            base_url="https://gateway.example.com/",
            api_key="custom-key",
            timeout=60,
            max_retries=5,
            retry_backoff=2.0,
        )
        assert client.base_url == "https://gateway.example.com"  # Trailing slash removed
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0
        client.close()

    def test_context_manager(self):
        """Test client as context manager."""
        with UAPKGatewayClient(base_url="http://localhost:8000", api_key="test") as client:
            assert client is not None
        # Client should be closed after context exit


class TestEvaluate:
    """Test evaluate method."""

    def test_evaluate_success(self, client, mock_gateway, sample_action):
        """Test successful action evaluation."""
        response = client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        assert response.interaction_id == "int_test_123"
        assert len(response.reasons) > 0

        # Check request was made
        assert len(mock_gateway.call_history) == 1
        call = mock_gateway.call_history[0]
        assert call["method"] == "POST"
        assert call["endpoint"] == "/api/v1/gateway/evaluate"
        assert call["data"]["uapk_id"] == "test-uapk-v1"

    def test_evaluate_with_counterparty(self, client, mock_gateway, sample_action, sample_counterparty):
        """Test evaluation with counterparty info."""
        response = client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            counterparty=sample_counterparty,
        )

        assert response.decision == "ALLOW"

        # Check counterparty was sent
        call = mock_gateway.call_history[0]
        assert "counterparty" in call["data"]
        assert call["data"]["counterparty"]["email"] == "customer@example.com"

    def test_evaluate_with_context(self, client, mock_gateway, sample_action):
        """Test evaluation with context."""
        context = {"user_tier": "premium", "session_id": "sess_123"}

        response = client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            context=context,
        )

        assert response.decision == "ALLOW"

        # Check context was sent
        call = mock_gateway.call_history[0]
        assert call["data"]["context"] == context

    def test_evaluate_with_capability_token(self, client, mock_gateway, sample_action):
        """Test evaluation with capability token."""
        response = client.evaluate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            capability_token="cap_token_xyz",
        )

        assert response.decision == "ALLOW"

        # Check token was sent
        call = mock_gateway.call_history[0]
        assert call["data"]["capability_token"] == "cap_token_xyz"


class TestExecute:
    """Test execute method."""

    def test_execute_success(self, client, mock_gateway, sample_action):
        """Test successful action execution."""
        response = client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        assert response.executed is True
        assert response.result is not None
        assert response.result.success is True

        # Check request was made
        assert len(mock_gateway.call_history) == 1
        call = mock_gateway.call_history[0]
        assert call["endpoint"] == "/api/v1/gateway/execute"

    def test_execute_with_override_token(self, client, mock_gateway, sample_action):
        """Test execution with override token."""
        response = client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            override_token="override_xyz",
        )

        assert response.decision == "ALLOW"

        # Check token was sent
        call = mock_gateway.call_history[0]
        assert call["data"]["override_token"] == "override_xyz"

    def test_execute_deny_raises(self, client, mock_gateway, sample_action, execute_deny_response):
        """Test execute raises ActionDeniedError on DENY."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        with pytest.raises(ActionDeniedError) as exc_info:
            client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_deny=True,
            )

        error = exc_info.value
        assert "denied" in str(error).lower()
        assert error.decision_response is not None
        assert len(error.reasons) > 0

    def test_execute_deny_no_raise(self, client, mock_gateway, sample_action, execute_deny_response):
        """Test execute returns response on DENY when raise_on_deny=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        response = client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_deny=False,
        )

        assert response.decision == "DENY"
        assert response.executed is False

    def test_execute_escalate_raises(self, client, mock_gateway, sample_action, execute_escalate_response):
        """Test execute raises ActionEscalatedError on ESCALATE."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        with pytest.raises(ActionEscalatedError) as exc_info:
            client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_escalate=True,
            )

        error = exc_info.value
        assert error.approval_id == "appr_123"
        assert "approval" in str(error).lower()

    def test_execute_escalate_no_raise(self, client, mock_gateway, sample_action, execute_escalate_response):
        """Test execute returns response on ESCALATE when raise_on_escalate=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        response = client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_escalate=False,
        )

        assert response.decision == "ESCALATE"
        assert response.approval_id == "appr_123"

    def test_execute_tool_error_raises(self, client, mock_gateway, sample_action, tool_error_response):
        """Test execute raises ToolExecutionError on tool failure."""
        mock_gateway.set_response("/api/v1/gateway/execute", tool_error_response)

        with pytest.raises(ToolExecutionError) as exc_info:
            client.execute(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                raise_on_tool_error=True,
            )

        error = exc_info.value
        assert "failed" in str(error).lower()
        assert error.tool_result is not None

    def test_execute_tool_error_no_raise(self, client, mock_gateway, sample_action, tool_error_response):
        """Test execute returns response on tool error when raise_on_tool_error=False."""
        mock_gateway.set_response("/api/v1/gateway/execute", tool_error_response)

        response = client.execute(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            raise_on_tool_error=False,
        )

        assert response.result.success is False
        assert response.result.error is not None


class TestApprovalWorkflow:
    """Test approval workflow methods."""

    def test_get_approval_status(self, client, mock_gateway):
        """Test getting approval status."""
        approval_response = {
            "id": "appr_123",
            "status": "APPROVED",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "override_token": "override_xyz",
        }
        mock_gateway.set_response("/api/v1/approvals/appr_123", approval_response)

        approval = client.get_approval_status("appr_123")

        assert approval["id"] == "appr_123"
        assert approval["status"] == "APPROVED"
        assert approval["override_token"] == "override_xyz"

    def test_execute_with_retry_on_escalate_immediate_allow(
        self, client, mock_gateway, sample_action
    ):
        """Test execute_with_retry_on_escalate when action is immediately allowed."""
        response = client.execute_with_retry_on_escalate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert response.decision == "ALLOW"
        # Should only call execute once
        assert len(mock_gateway.call_history) == 1

    def test_execute_with_retry_on_escalate_approval_flow(
        self, client, mock_gateway, sample_action, execute_escalate_response
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
                # Return success when override token is present
                return {
                    "interaction_id": "int_approved_123",
                    "decision": "ALLOW",
                    "reasons": [{"code": "POLICY_ALLOWS", "message": "Approved", "details": None}],
                    "timestamp": "2024-01-01T00:00:00Z",
                    "policy_version": "v1.0.0",
                    "executed": True,
                    "result": {
                        "success": True,
                        "data": {"output": "Success after approval"},
                    },
                }
            return execute_escalate_response

        # Mock the response based on request
        original_get_response = mock_gateway.get_response

        def custom_get_response(method, endpoint, data):
            if endpoint == "/api/v1/gateway/execute":
                return get_execute_response(method, endpoint, data)
            return original_get_response(method, endpoint, data)

        mock_gateway.get_response = custom_get_response

        response = client.execute_with_retry_on_escalate(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            poll_interval=0.1,  # Short interval for testing
            max_wait=10,
        )

        assert response.decision == "ALLOW"
        assert response.executed is True

    def test_execute_with_retry_on_escalate_denied(
        self, client, mock_gateway, sample_action, execute_escalate_response
    ):
        """Test execute_with_retry_on_escalate when approval is denied."""
        # First call: ESCALATE
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        # Approval status: DENIED
        approval_response = {
            "id": "appr_123",
            "status": "DENIED",
        }
        mock_gateway.set_response("/api/v1/approvals/appr_123", approval_response)

        with pytest.raises(ActionDeniedError):
            client.execute_with_retry_on_escalate(
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action=sample_action,
                poll_interval=0.1,
                max_wait=10,
            )


class TestErrorHandling:
    """Test error handling."""

    def test_authentication_error(self, mock_gateway):
        """Test handling of 401 authentication error."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock 401 response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.request.return_value = mock_response

            client = UAPKGatewayClient(base_url="http://localhost:8000", api_key="invalid")

            with pytest.raises(AuthenticationError):
                client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            client.close()

    def test_validation_error(self, mock_gateway):
        """Test handling of 422 validation error."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock 422 response
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {"detail": "Invalid request"}
            mock_client.request.return_value = mock_response

            client = UAPKGatewayClient(base_url="http://localhost:8000", api_key="test")

            with pytest.raises(ValidationError) as exc_info:
                client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            assert "validation" in str(exc_info.value).lower()
            client.close()

    def test_rate_limit_error(self, mock_gateway):
        """Test handling of 429 rate limit error."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock 429 response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_client.request.return_value = mock_response

            client = UAPKGatewayClient(base_url="http://localhost:8000", api_key="test")

            with pytest.raises(RateLimitError) as exc_info:
                client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            assert exc_info.value.retry_after == 60
            client.close()

    def test_server_error_with_retry(self, mock_gateway):
        """Test server error handling with retry."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock 500 response that eventually succeeds
            call_count = [0]

            def mock_request(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] < 3:
                    mock_response = Mock()
                    mock_response.status_code = 500
                    mock_response.text = "Internal Server Error"
                    return mock_response
                else:
                    # Success on 3rd try
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

            client = UAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=3,
                retry_backoff=0.01,  # Fast retry for testing
            )

            response = client.evaluate(
                uapk_id="test",
                agent_id="test",
                action=ActionInfo(type="test", tool="test", params={}),
            )

            assert response.decision == "ALLOW"
            assert call_count[0] == 3  # Should have retried

            client.close()

    def test_network_error(self, mock_gateway):
        """Test network error handling."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock network error
            mock_client.request.side_effect = httpx.RequestError("Connection failed")

            client = UAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=1,
            )

            with pytest.raises(NetworkError):
                client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            client.close()

    def test_timeout_error(self, mock_gateway):
        """Test timeout error handling."""
        with patch("uapk_gateway.client.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock timeout
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

            client = UAPKGatewayClient(
                base_url="http://localhost:8000",
                api_key="test",
                max_retries=1,
            )

            with pytest.raises(NetworkError) as exc_info:
                client.evaluate(
                    uapk_id="test",
                    agent_id="test",
                    action=ActionInfo(type="test", tool="test", params={}),
                )

            assert "timeout" in str(exc_info.value).lower()
            client.close()
