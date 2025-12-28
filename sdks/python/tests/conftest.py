"""Pytest fixtures for UAPK Gateway SDK tests."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch
import httpx

from uapk_gateway import UAPKGatewayClient, AsyncUAPKGatewayClient
from uapk_gateway.models import (
    ActionInfo,
    CounterpartyInfo,
    GatewayDecision,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
    ReasonCode,
    ReasonDetail,
    ToolResult,
)


# ============================================================================
# Mock Gateway Server
# ============================================================================


class MockGatewayServer:
    """Mock UAPK Gateway server for testing."""

    def __init__(self):
        self.responses = {}
        self.call_history = []

    def set_response(self, endpoint: str, response_data: dict):
        """Set mock response for an endpoint."""
        self.responses[endpoint] = response_data

    def clear_responses(self):
        """Clear all mock responses."""
        self.responses.clear()
        self.call_history.clear()

    def get_response(self, method: str, endpoint: str, request_data: dict | None = None) -> dict:
        """Get mock response for a request."""
        self.call_history.append({
            "method": method,
            "endpoint": endpoint,
            "data": request_data,
        })

        if endpoint in self.responses:
            return self.responses[endpoint]

        # Default responses
        if endpoint == "/api/v1/gateway/evaluate":
            return self._default_evaluate_response()
        elif endpoint == "/api/v1/gateway/execute":
            return self._default_execute_response()
        elif endpoint.startswith("/api/v1/approvals/"):
            return self._default_approval_response()

        raise ValueError(f"No mock response configured for {endpoint}")

    def _default_evaluate_response(self) -> dict:
        return {
            "interaction_id": "int_test_123",
            "decision": "ALLOW",
            "reasons": [
                {
                    "code": "POLICY_ALLOWS",
                    "message": "Action allowed by policy",
                    "details": None,
                }
            ],
            "approval_id": None,
            "timestamp": datetime.now(UTC).isoformat(),
            "policy_version": "v1.0.0",
        }

    def _default_execute_response(self) -> dict:
        return {
            "interaction_id": "int_test_456",
            "decision": "ALLOW",
            "reasons": [
                {
                    "code": "POLICY_ALLOWS",
                    "message": "Action allowed by policy",
                    "details": None,
                }
            ],
            "approval_id": None,
            "timestamp": datetime.now(UTC).isoformat(),
            "policy_version": "v1.0.0",
            "executed": True,
            "result": {
                "success": True,
                "data": {"output": "Test result"},
                "error": None,
                "result_hash": "hash_123",
                "duration_ms": 42,
            },
        }

    def _default_approval_response(self) -> dict:
        return {
            "id": "appr_test_789",
            "status": "PENDING",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "override_token": None,
        }


@pytest.fixture
def mock_gateway():
    """Create a mock gateway server."""
    return MockGatewayServer()


# ============================================================================
# Client Fixtures
# ============================================================================


@pytest.fixture
def mock_httpx_client(mock_gateway):
    """Mock httpx.Client for sync client."""
    mock_client = Mock(spec=httpx.Client)

    def mock_request(method: str, url: str, json: dict | None = None):
        # Extract endpoint from URL
        endpoint = url.split("localhost:8000")[-1] if "localhost:8000" in url else url

        # Get mock response
        response_data = mock_gateway.get_response(method, endpoint, json)

        # Create mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.headers = {}

        return mock_response

    mock_client.request.side_effect = mock_request
    return mock_client


@pytest.fixture
def mock_async_httpx_client(mock_gateway):
    """Mock httpx.AsyncClient for async client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def mock_request(method: str, url: str, json: dict | None = None):
        # Extract endpoint from URL
        endpoint = url.split("localhost:8000")[-1] if "localhost:8000" in url else url

        # Get mock response
        response_data = mock_gateway.get_response(method, endpoint, json)

        # Create mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.headers = {}

        return mock_response

    mock_client.request.side_effect = mock_request
    return mock_client


@pytest.fixture
def client(mock_httpx_client):
    """Create a sync client with mocked HTTP client."""
    with patch("uapk_gateway.client.httpx.Client", return_value=mock_httpx_client):
        client = UAPKGatewayClient(
            base_url="http://localhost:8000",
            api_key="test-api-key",
        )
        yield client
        client.close()


@pytest.fixture
async def async_client(mock_async_httpx_client):
    """Create an async client with mocked HTTP client."""
    with patch("uapk_gateway.async_client.httpx.AsyncClient", return_value=mock_async_httpx_client):
        client = AsyncUAPKGatewayClient(
            base_url="http://localhost:8000",
            api_key="test-api-key",
        )
        yield client
        await client.close()


# ============================================================================
# Model Fixtures
# ============================================================================


@pytest.fixture
def sample_action():
    """Create a sample ActionInfo."""
    return ActionInfo(
        type="send_email",
        tool="smtp_connector",
        params={
            "to": "user@example.com",
            "subject": "Test",
            "body": "Test message",
        },
    )


@pytest.fixture
def sample_refund_action():
    """Create a sample refund ActionInfo."""
    return ActionInfo(
        type="refund",
        tool="stripe_api",
        params={"charge_id": "ch_123"},
        amount=100.00,
        currency="USD",
    )


@pytest.fixture
def sample_counterparty():
    """Create a sample CounterpartyInfo."""
    return CounterpartyInfo(
        email="customer@example.com",
        domain="example.com",
        jurisdiction="US",
    )


@pytest.fixture
def sample_decision_response():
    """Create a sample GatewayDecisionResponse."""
    return GatewayDecisionResponse(
        interaction_id="int_test_123",
        decision=GatewayDecision.ALLOW,
        reasons=[
            ReasonDetail(
                code=ReasonCode.POLICY_ALLOWS,
                message="Action allowed by policy",
            )
        ],
        timestamp=datetime.now(UTC),
        policy_version="v1.0.0",
    )


@pytest.fixture
def sample_execute_response():
    """Create a sample GatewayExecuteResponse."""
    return GatewayExecuteResponse(
        interaction_id="int_test_456",
        decision=GatewayDecision.ALLOW,
        reasons=[
            ReasonDetail(
                code=ReasonCode.POLICY_ALLOWS,
                message="Action allowed by policy",
            )
        ],
        timestamp=datetime.now(UTC),
        policy_version="v1.0.0",
        executed=True,
        result=ToolResult(
            success=True,
            data={"output": "Test result"},
            result_hash="hash_123",
            duration_ms=42,
        ),
    )


# ============================================================================
# LangChain Fixtures
# ============================================================================


@pytest.fixture
def mock_langchain_tool():
    """Create a mock LangChain tool."""
    try:
        from langchain.tools import BaseTool

        class MockTool(BaseTool):
            name = "mock_tool"
            description = "A mock tool for testing"

            def _run(self, input_str: str) -> str:
                return f"Mock result: {input_str}"

            async def _arun(self, input_str: str) -> str:
                return f"Mock async result: {input_str}"

        return MockTool()
    except ImportError:
        pytest.skip("LangChain not installed")


# ============================================================================
# Error Response Fixtures
# ============================================================================


@pytest.fixture
def deny_response():
    """Create a DENY response."""
    return {
        "interaction_id": "int_deny_123",
        "decision": "DENY",
        "reasons": [
            {
                "code": "ACTION_TYPE_DENIED",
                "message": "Action type is not allowed",
                "details": {"action_type": "dangerous_action"},
            }
        ],
        "approval_id": None,
        "timestamp": datetime.now(UTC).isoformat(),
        "policy_version": "v1.0.0",
    }


@pytest.fixture
def escalate_response():
    """Create an ESCALATE response."""
    return {
        "interaction_id": "int_escalate_123",
        "decision": "ESCALATE",
        "reasons": [
            {
                "code": "APPROVAL_REQUIRED",
                "message": "Action requires human approval",
                "details": {"threshold": 1000},
            }
        ],
        "approval_id": "appr_123",
        "timestamp": datetime.now(UTC).isoformat(),
        "policy_version": "v1.0.0",
    }


@pytest.fixture
def execute_deny_response(deny_response):
    """Create an execute DENY response."""
    return {
        **deny_response,
        "executed": False,
        "result": None,
    }


@pytest.fixture
def execute_escalate_response(escalate_response):
    """Create an execute ESCALATE response."""
    return {
        **escalate_response,
        "executed": False,
        "result": None,
    }


@pytest.fixture
def tool_error_response():
    """Create a tool execution error response."""
    return {
        "interaction_id": "int_error_123",
        "decision": "ALLOW",
        "reasons": [
            {
                "code": "POLICY_ALLOWS",
                "message": "Action allowed by policy",
                "details": None,
            }
        ],
        "approval_id": None,
        "timestamp": datetime.now(UTC).isoformat(),
        "policy_version": "v1.0.0",
        "executed": True,
        "result": {
            "success": False,
            "data": None,
            "error": {"message": "Tool execution failed", "code": "EXEC_ERROR"},
            "result_hash": None,
            "duration_ms": 10,
        },
    }
