"""Tests for LangChain integration."""

import pytest
from unittest.mock import Mock, AsyncMock

# Skip all tests if LangChain is not installed
pytest.importorskip("langchain")

from langchain.tools import BaseTool

from uapk_gateway.integrations.langchain import UAPKGatewayTool, wrap_langchain_tools
from uapk_gateway.models import ActionInfo, CounterpartyInfo
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError


# ============================================================================
# Mock Tools
# ============================================================================


class MockTool(BaseTool):
    """Mock LangChain tool for testing."""

    name = "mock_tool"
    description = "A mock tool for testing"

    def _run(self, tool_input: str) -> str:
        """Sync run."""
        return f"Mock result: {tool_input}"

    async def _arun(self, tool_input: str) -> str:
        """Async run."""
        return f"Mock async result: {tool_input}"


class EmailTool(BaseTool):
    """Mock email tool."""

    name = "send_email"
    description = "Send an email"

    def _run(self, tool_input: str) -> str:
        return f"Email sent: {tool_input}"

    async def _arun(self, tool_input: str) -> str:
        return f"Email sent async: {tool_input}"


# ============================================================================
# Tests
# ============================================================================


class TestUAPKGatewayTool:
    """Test UAPKGatewayTool wrapper."""

    def test_tool_creation(self, client, mock_langchain_tool):
        """Test creating a wrapped tool."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        assert wrapped.name == mock_langchain_tool.name
        assert wrapped.description == mock_langchain_tool.description
        assert wrapped.uapk_id == "test-uapk-v1"
        assert wrapped.agent_id == "agent-123"
        assert wrapped.action_type == "test_action"

    def test_tool_creation_with_name_override(self, client, mock_langchain_tool):
        """Test creating wrapped tool with name override."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            tool_name="custom_tool_name",
        )

        assert wrapped.tool_name == "custom_tool_name"
        assert wrapped.name == mock_langchain_tool.name  # Display name unchanged

    def test_tool_requires_client(self, mock_langchain_tool):
        """Test tool creation fails without client."""
        with pytest.raises(ValueError) as exc_info:
            UAPKGatewayTool(
                tool=mock_langchain_tool,
                uapk_id="test-uapk-v1",
                agent_id="agent-123",
                action_type="test_action",
            )

        assert "gateway_client" in str(exc_info.value).lower()

    def test_sync_run_allow(self, client, mock_gateway, mock_langchain_tool):
        """Test sync tool execution with ALLOW decision."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = wrapped.run("test input")

        # Should call through to original tool
        assert "Mock result" in result
        assert len(mock_gateway.call_history) == 1

    def test_sync_run_deny_raises(self, client, mock_gateway, mock_langchain_tool, execute_deny_response):
        """Test sync tool execution raises on DENY."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        with pytest.raises(ActionDeniedError):
            wrapped.run("test input")

    def test_sync_run_escalate_raises(
        self, client, mock_gateway, mock_langchain_tool, execute_escalate_response
    ):
        """Test sync tool execution raises on ESCALATE."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            handle_approval_required="raise",
        )

        with pytest.raises(ActionEscalatedError) as exc_info:
            wrapped.run("test input")

        assert exc_info.value.approval_id == "appr_123"

    def test_sync_run_escalate_deny_mode(
        self, client, mock_gateway, mock_langchain_tool, execute_escalate_response
    ):
        """Test sync tool execution treats ESCALATE as DENY."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            handle_approval_required="deny",
        )

        with pytest.raises(ActionDeniedError) as exc_info:
            wrapped.run("test input")

        assert "approval" in str(exc_info.value).lower()

    def test_sync_run_with_string_input(self, client, mock_gateway, mock_langchain_tool):
        """Test tool with string input."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = wrapped.run("simple string input")

        # Check action was created correctly
        call = mock_gateway.call_history[0]
        assert call["data"]["action"]["params"]["query"] == "simple string input"

    def test_sync_run_with_dict_input(self, client, mock_gateway, mock_langchain_tool):
        """Test tool with dict input."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = wrapped.run({"key": "value", "count": 42})

        # Check action params
        call = mock_gateway.call_history[0]
        assert call["data"]["action"]["params"]["key"] == "value"
        assert call["data"]["action"]["params"]["count"] == 42

    def test_custom_counterparty_extraction(self, client, mock_gateway, mock_langchain_tool):
        """Test custom counterparty extraction function."""

        def extract_counterparty(params: dict) -> CounterpartyInfo | None:
            if "email" in params:
                return CounterpartyInfo(email=params["email"])
            return None

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="send_email",
            get_counterparty=extract_counterparty,
        )

        wrapped.run({"email": "user@example.com", "subject": "Test"})

        # Check counterparty was extracted
        call = mock_gateway.call_history[0]
        assert call["data"]["counterparty"] is not None
        assert call["data"]["counterparty"]["email"] == "user@example.com"

    def test_custom_context_extraction(self, client, mock_gateway, mock_langchain_tool):
        """Test custom context extraction function."""

        def extract_context(params: dict) -> dict:
            return {"priority": params.get("priority", "normal")}

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            get_context=extract_context,
        )

        wrapped.run({"priority": "high", "other": "data"})

        # Check context was extracted
        call = mock_gateway.call_history[0]
        assert call["data"]["context"]["priority"] == "high"

    def test_capability_token(self, client, mock_gateway, mock_langchain_tool):
        """Test passing capability token."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            capability_token="cap_xyz",
        )

        wrapped.run("test")

        # Check token was sent
        call = mock_gateway.call_history[0]
        assert call["data"]["capability_token"] == "cap_xyz"


class TestUAPKGatewayToolAsync:
    """Test async UAPKGatewayTool execution."""

    @pytest.mark.asyncio
    async def test_async_run_allow(self, async_client, mock_gateway, mock_langchain_tool):
        """Test async tool execution with ALLOW decision."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            async_gateway_client=async_client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = await wrapped._arun("test input")

        assert "Mock async result" in result
        assert len(mock_gateway.call_history) == 1

    @pytest.mark.asyncio
    async def test_async_run_deny_raises(
        self, async_client, mock_gateway, mock_langchain_tool, execute_deny_response
    ):
        """Test async tool execution raises on DENY."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            async_gateway_client=async_client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        with pytest.raises(ActionDeniedError):
            await wrapped._arun("test input")

    @pytest.mark.asyncio
    async def test_async_run_escalate_raises(
        self, async_client, mock_gateway, mock_langchain_tool, execute_escalate_response
    ):
        """Test async tool execution raises on ESCALATE."""
        mock_gateway.set_response("/api/v1/gateway/execute", execute_escalate_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            async_gateway_client=async_client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
            handle_approval_required="raise",
        )

        with pytest.raises(ActionEscalatedError):
            await wrapped._arun("test input")

    @pytest.mark.asyncio
    async def test_async_client_required(self, mock_langchain_tool):
        """Test async execution fails without async client."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=Mock(),  # Sync client only
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        with pytest.raises(RuntimeError) as exc_info:
            await wrapped._arun("test")

        assert "async_gateway_client" in str(exc_info.value).lower()


class TestWrapLangChainTools:
    """Test batch tool wrapping utility."""

    def test_wrap_multiple_tools(self, client):
        """Test wrapping multiple tools at once."""
        tools = [
            MockTool(),
            EmailTool(),
        ]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
        )

        assert len(wrapped) == 2
        assert all(isinstance(t, UAPKGatewayTool) for t in wrapped)
        assert wrapped[0].name == "mock_tool"
        assert wrapped[1].name == "send_email"

    def test_wrap_with_action_type_map(self, client):
        """Test wrapping with custom action type mapping."""
        tools = [MockTool(), EmailTool()]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type_map={
                "mock_tool": "custom_action",
                "send_email": "email_send",
            },
        )

        assert wrapped[0].action_type == "custom_action"
        assert wrapped[1].action_type == "email_send"

    def test_wrap_with_default_action_type(self, client):
        """Test wrapping without action type map uses default."""
        tools = [MockTool()]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
        )

        # Should default to "tool_use"
        assert wrapped[0].action_type == "tool_use"

    def test_wrap_with_sync_client(self, client):
        """Test wrapping with sync client."""
        tools = [MockTool()]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
        )

        assert wrapped[0].gateway_client is client
        assert wrapped[0].async_gateway_client is None

    @pytest.mark.asyncio
    async def test_wrap_with_async_client(self, async_client):
        """Test wrapping with async client."""
        tools = [MockTool()]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=async_client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
        )

        assert wrapped[0].gateway_client is None
        assert wrapped[0].async_gateway_client is async_client

    def test_wrap_with_additional_kwargs(self, client):
        """Test wrapping with additional keyword arguments."""
        tools = [MockTool()]

        wrapped = wrap_langchain_tools(
            tools=tools,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            handle_approval_required="deny",
            capability_token="cap_xyz",
        )

        assert wrapped[0].handle_approval_required == "deny"
        assert wrapped[0].capability_token == "cap_xyz"

    def test_wrap_empty_list(self, client):
        """Test wrapping empty tool list."""
        wrapped = wrap_langchain_tools(
            tools=[],
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
        )

        assert wrapped == []


class TestToolIntegration:
    """Test tool integration patterns."""

    def test_tool_preserves_metadata(self, client, mock_langchain_tool):
        """Test wrapped tool preserves original metadata."""
        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        assert wrapped.name == mock_langchain_tool.name
        assert wrapped.description == mock_langchain_tool.description

    def test_gateway_executed_result(self, client, mock_gateway, mock_langchain_tool):
        """Test when gateway executes the tool."""
        # Mock gateway returning executed result
        execute_response = {
            "interaction_id": "int_123",
            "decision": "ALLOW",
            "reasons": [{"code": "POLICY_ALLOWS", "message": "OK", "details": None}],
            "timestamp": "2024-01-01T00:00:00Z",
            "policy_version": "v1.0.0",
            "executed": True,
            "result": {
                "success": True,
                "data": {"output": "Gateway executed this"},
            },
        }
        mock_gateway.set_response("/api/v1/gateway/execute", execute_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = wrapped.run("test")

        # Should return gateway result
        assert result == "Gateway executed this"

    def test_local_tool_execution(self, client, mock_gateway, mock_langchain_tool):
        """Test when gateway allows but doesn't execute."""
        # Mock gateway returning ALLOW without execution
        execute_response = {
            "interaction_id": "int_123",
            "decision": "ALLOW",
            "reasons": [{"code": "POLICY_ALLOWS", "message": "OK", "details": None}],
            "timestamp": "2024-01-01T00:00:00Z",
            "policy_version": "v1.0.0",
            "executed": False,
            "result": None,
        }
        mock_gateway.set_response("/api/v1/gateway/execute", execute_response)

        wrapped = UAPKGatewayTool(
            tool=mock_langchain_tool,
            gateway_client=client,
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action_type="test_action",
        )

        result = wrapped.run("test")

        # Should execute local tool
        assert "Mock result" in result
