"""Tests for exception classes."""

import pytest
from uapk_gateway.exceptions import (
    UAPKGatewayError,
    AuthenticationError,
    ActionDeniedError,
    ActionEscalatedError,
    ToolExecutionError,
    NetworkError,
    ValidationError,
    RateLimitError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_base_exception(self):
        """Test base UAPKGatewayError."""
        error = UAPKGatewayError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_authentication_error_hierarchy(self):
        """Test AuthenticationError inherits from base."""
        error = AuthenticationError("Invalid API key")
        assert isinstance(error, UAPKGatewayError)
        assert isinstance(error, Exception)

    def test_network_error_hierarchy(self):
        """Test NetworkError inherits from base."""
        error = NetworkError("Connection failed")
        assert isinstance(error, UAPKGatewayError)

    def test_validation_error_hierarchy(self):
        """Test ValidationError inherits from base."""
        error = ValidationError("Invalid request")
        assert isinstance(error, UAPKGatewayError)


class TestActionDeniedError:
    """Test ActionDeniedError exception."""

    def test_action_denied_error_basic(self):
        """Test basic ActionDeniedError creation."""
        decision_response = {
            "decision": "DENY",
            "reasons": [{"code": "ACTION_TYPE_DENIED", "message": "Not allowed"}],
            "interaction_id": "int_123",
        }

        error = ActionDeniedError("Action denied", decision_response=decision_response)

        assert "denied" in str(error).lower()
        assert error.decision_response == decision_response
        assert error.reasons == decision_response["reasons"]
        assert error.interaction_id == "int_123"

    def test_action_denied_error_with_reasons(self):
        """Test ActionDeniedError with multiple reasons."""
        decision_response = {
            "decision": "DENY",
            "reasons": [
                {"code": "BUDGET_EXCEEDED", "message": "Daily budget exceeded"},
                {"code": "JURISDICTION_DENIED", "message": "Jurisdiction not allowed"},
            ],
            "interaction_id": "int_456",
        }

        error = ActionDeniedError("Multiple violations", decision_response=decision_response)

        assert len(error.reasons) == 2
        assert error.reasons[0]["code"] == "BUDGET_EXCEEDED"
        assert error.reasons[1]["code"] == "JURISDICTION_DENIED"

    def test_action_denied_error_missing_reasons(self):
        """Test ActionDeniedError with missing reasons field."""
        decision_response = {
            "decision": "DENY",
            "interaction_id": "int_789",
        }

        error = ActionDeniedError("Denied", decision_response=decision_response)

        assert error.reasons == []  # Default to empty list

    def test_action_denied_error_catchable(self):
        """Test ActionDeniedError can be caught as base exception."""
        try:
            raise ActionDeniedError("Test", decision_response={})
        except UAPKGatewayError as e:
            assert isinstance(e, ActionDeniedError)
        except Exception:
            pytest.fail("Should be caught as UAPKGatewayError")


class TestActionEscalatedError:
    """Test ActionEscalatedError exception."""

    def test_action_escalated_error_basic(self):
        """Test basic ActionEscalatedError creation."""
        decision_response = {
            "decision": "ESCALATE",
            "approval_id": "appr_123",
            "reasons": [{"code": "APPROVAL_REQUIRED", "message": "Requires approval"}],
            "interaction_id": "int_123",
        }

        error = ActionEscalatedError("Approval required", decision_response=decision_response)

        assert error.approval_id == "appr_123"
        assert error.interaction_id == "int_123"
        assert len(error.reasons) == 1

    def test_action_escalated_error_message(self):
        """Test ActionEscalatedError message includes approval ID."""
        decision_response = {
            "approval_id": "appr_456",
            "reasons": [],
        }

        error = ActionEscalatedError(
            "Action requires approval (approval_id: appr_456)",
            decision_response=decision_response,
        )

        assert "appr_456" in str(error)
        assert "approval" in str(error).lower()

    def test_action_escalated_error_missing_approval_id(self):
        """Test ActionEscalatedError with missing approval_id."""
        decision_response = {
            "decision": "ESCALATE",
            "reasons": [],
        }

        error = ActionEscalatedError("Escalated", decision_response=decision_response)

        assert error.approval_id is None

    def test_action_escalated_error_catchable(self):
        """Test ActionEscalatedError can be caught as base exception."""
        try:
            raise ActionEscalatedError("Test", decision_response={"approval_id": "appr_123"})
        except UAPKGatewayError as e:
            assert isinstance(e, ActionEscalatedError)
            assert e.approval_id == "appr_123"


class TestToolExecutionError:
    """Test ToolExecutionError exception."""

    def test_tool_execution_error_basic(self):
        """Test basic ToolExecutionError creation."""
        tool_result = {
            "success": False,
            "error": {"message": "Tool failed", "code": "EXEC_ERROR"},
        }

        error = ToolExecutionError("Tool execution failed", tool_result=tool_result)

        assert error.tool_result == tool_result
        assert error.error == tool_result["error"]

    def test_tool_execution_error_with_details(self):
        """Test ToolExecutionError with detailed error info."""
        tool_result = {
            "success": False,
            "error": {
                "message": "Connection timeout",
                "code": "TIMEOUT",
                "details": {"timeout_ms": 30000},
            },
        }

        error = ToolExecutionError("Timeout occurred", tool_result=tool_result)

        assert error.error["code"] == "TIMEOUT"
        assert error.error["details"]["timeout_ms"] == 30000

    def test_tool_execution_error_missing_error_field(self):
        """Test ToolExecutionError with missing error field."""
        tool_result = {
            "success": False,
            "data": None,
        }

        error = ToolExecutionError("Failed", tool_result=tool_result)

        assert error.error == {}  # Default to empty dict

    def test_tool_execution_error_catchable(self):
        """Test ToolExecutionError can be caught as base exception."""
        try:
            raise ToolExecutionError("Test", tool_result={})
        except UAPKGatewayError as e:
            assert isinstance(e, ToolExecutionError)


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_rate_limit_error_basic(self):
        """Test basic RateLimitError creation."""
        error = RateLimitError("Rate limit exceeded")

        assert "rate limit" in str(error).lower()
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded. Retry after 60 seconds.", retry_after=60)

        assert error.retry_after == 60
        assert "60" in str(error)

    def test_rate_limit_error_retry_after_types(self):
        """Test RateLimitError with different retry_after types."""
        # Integer
        error1 = RateLimitError("Test", retry_after=30)
        assert error1.retry_after == 30

        # None
        error2 = RateLimitError("Test", retry_after=None)
        assert error2.retry_after is None

    def test_rate_limit_error_catchable(self):
        """Test RateLimitError can be caught as base exception."""
        try:
            raise RateLimitError("Test", retry_after=60)
        except UAPKGatewayError as e:
            assert isinstance(e, RateLimitError)
            assert e.retry_after == 60


class TestNetworkError:
    """Test NetworkError exception."""

    def test_network_error_basic(self):
        """Test basic NetworkError creation."""
        error = NetworkError("Connection failed")
        assert "connection" in str(error).lower()

    def test_network_error_types(self):
        """Test different types of network errors."""
        timeout_error = NetworkError("Request timeout after 30s")
        assert "timeout" in str(timeout_error).lower()

        connection_error = NetworkError("Network error: Connection refused")
        assert "connection" in str(connection_error).lower()

        server_error = NetworkError("Gateway server error: 500 - Internal Server Error")
        assert "500" in str(server_error)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_basic(self):
        """Test basic AuthenticationError creation."""
        error = AuthenticationError("Invalid API key")
        assert "invalid" in str(error).lower()

    def test_authentication_error_messages(self):
        """Test different authentication error messages."""
        invalid_key = AuthenticationError("Invalid API key or authentication failed")
        assert "invalid" in str(invalid_key).lower()

        expired = AuthenticationError("API key has expired")
        assert "expired" in str(expired).lower()


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_basic(self):
        """Test basic ValidationError creation."""
        error = ValidationError("Request validation failed")
        assert "validation" in str(error).lower()

    def test_validation_error_with_details(self):
        """Test ValidationError with detailed message."""
        error = ValidationError(
            "Request validation failed: field 'uapk_id' is required"
        )
        assert "uapk_id" in str(error)
        assert "required" in str(error).lower()


class TestExceptionUsage:
    """Test practical exception usage patterns."""

    def test_catching_specific_exceptions(self):
        """Test catching specific exception types."""
        # ActionDeniedError
        with pytest.raises(ActionDeniedError):
            raise ActionDeniedError("Denied", decision_response={})

        # ActionEscalatedError
        with pytest.raises(ActionEscalatedError):
            raise ActionEscalatedError("Escalated", decision_response={})

        # ToolExecutionError
        with pytest.raises(ToolExecutionError):
            raise ToolExecutionError("Failed", tool_result={})

    def test_catching_base_exception(self):
        """Test catching any SDK exception with base class."""
        exceptions = [
            ActionDeniedError("Test", decision_response={}),
            ActionEscalatedError("Test", decision_response={}),
            ToolExecutionError("Test", tool_result={}),
            AuthenticationError("Test"),
            NetworkError("Test"),
            ValidationError("Test"),
            RateLimitError("Test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except UAPKGatewayError:
                pass  # Successfully caught
            except Exception:
                pytest.fail(f"{type(exc).__name__} not caught by UAPKGatewayError")

    def test_exception_chaining(self):
        """Test exception chaining with cause."""
        original_error = ValueError("Original error")

        try:
            try:
                raise original_error
            except ValueError as e:
                raise NetworkError("Network error occurred") from e
        except NetworkError as e:
            assert e.__cause__ is original_error

    def test_multiple_exception_handling(self):
        """Test handling multiple exception types."""
        def raise_various_errors(error_type: str):
            if error_type == "denied":
                raise ActionDeniedError("Denied", decision_response={})
            elif error_type == "escalated":
                raise ActionEscalatedError("Escalated", decision_response={"approval_id": "appr_123"})
            elif error_type == "network":
                raise NetworkError("Network error")

        # Test handling each type
        for error_type in ["denied", "escalated", "network"]:
            with pytest.raises(UAPKGatewayError):
                raise_various_errors(error_type)
