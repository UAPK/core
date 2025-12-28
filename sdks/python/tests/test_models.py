"""Tests for Pydantic models."""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError

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


class TestActionInfo:
    """Test ActionInfo model."""

    def test_action_info_minimal(self):
        """Test ActionInfo with minimal required fields."""
        action = ActionInfo(
            type="send_email",
            tool="smtp",
            params={"to": "user@example.com"},
        )

        assert action.type == "send_email"
        assert action.tool == "smtp"
        assert action.params == {"to": "user@example.com"}
        assert action.amount is None
        assert action.currency is None
        assert action.description is None

    def test_action_info_full(self):
        """Test ActionInfo with all fields."""
        action = ActionInfo(
            type="refund",
            tool="stripe_api",
            params={"charge_id": "ch_123"},
            amount=100.50,
            currency="USD",
            description="Customer refund",
        )

        assert action.type == "refund"
        assert action.tool == "stripe_api"
        assert action.amount == 100.50
        assert action.currency == "USD"
        assert action.description == "Customer refund"

    def test_action_info_validation_missing_type(self):
        """Test ActionInfo validation fails without type."""
        with pytest.raises(ValidationError) as exc_info:
            ActionInfo(tool="smtp", params={})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_action_info_validation_missing_tool(self):
        """Test ActionInfo validation fails without tool."""
        with pytest.raises(ValidationError):
            ActionInfo(type="send_email", params={})

    def test_action_info_serialization(self):
        """Test ActionInfo can be serialized."""
        action = ActionInfo(
            type="refund",
            tool="stripe_api",
            params={"charge_id": "ch_123"},
            amount=100.00,
            currency="USD",
        )

        data = action.model_dump()
        assert data["type"] == "refund"
        assert data["tool"] == "stripe_api"
        assert data["amount"] == 100.00

    def test_action_info_exclude_none(self):
        """Test ActionInfo serialization excludes None values."""
        action = ActionInfo(
            type="send_email",
            tool="smtp",
            params={},
        )

        data = action.model_dump(exclude_none=True)
        assert "amount" not in data
        assert "currency" not in data
        assert "description" not in data


class TestCounterpartyInfo:
    """Test CounterpartyInfo model."""

    def test_counterparty_info_minimal(self):
        """Test CounterpartyInfo with minimal fields."""
        counterparty = CounterpartyInfo()
        assert counterparty.id is None
        assert counterparty.name is None
        assert counterparty.email is None

    def test_counterparty_info_full(self):
        """Test CounterpartyInfo with all fields."""
        counterparty = CounterpartyInfo(
            id="cust_123",
            name="John Doe",
            email="john@example.com",
            domain="example.com",
            jurisdiction="US",
        )

        assert counterparty.id == "cust_123"
        assert counterparty.name == "John Doe"
        assert counterparty.email == "john@example.com"
        assert counterparty.domain == "example.com"
        assert counterparty.jurisdiction == "US"

    def test_counterparty_info_serialization(self):
        """Test CounterpartyInfo serialization."""
        counterparty = CounterpartyInfo(
            email="user@example.com",
            jurisdiction="US",
        )

        data = counterparty.model_dump(exclude_none=True)
        assert data["email"] == "user@example.com"
        assert data["jurisdiction"] == "US"
        assert "id" not in data
        assert "name" not in data


class TestReasonDetail:
    """Test ReasonDetail model."""

    def test_reason_detail_minimal(self):
        """Test ReasonDetail with minimal fields."""
        reason = ReasonDetail(
            code=ReasonCode.POLICY_ALLOWS,
            message="Action allowed",
        )

        assert reason.code == ReasonCode.POLICY_ALLOWS
        assert reason.message == "Action allowed"
        assert reason.details is None

    def test_reason_detail_with_details(self):
        """Test ReasonDetail with details."""
        reason = ReasonDetail(
            code=ReasonCode.BUDGET_EXCEEDED,
            message="Daily budget exceeded",
            details={"daily_cap": 1000, "current": 1001},
        )

        assert reason.code == ReasonCode.BUDGET_EXCEEDED
        assert reason.details["daily_cap"] == 1000

    def test_reason_code_enum(self):
        """Test ReasonCode enum values."""
        assert ReasonCode.POLICY_ALLOWS == "POLICY_ALLOWS"
        assert ReasonCode.ACTION_TYPE_DENIED == "ACTION_TYPE_DENIED"
        assert ReasonCode.BUDGET_EXCEEDED == "BUDGET_EXCEEDED"
        assert ReasonCode.APPROVAL_REQUIRED == "APPROVAL_REQUIRED"


class TestGatewayActionRequest:
    """Test GatewayActionRequest model."""

    def test_action_request_minimal(self, sample_action):
        """Test GatewayActionRequest with minimal fields."""
        request = GatewayActionRequest(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        assert request.uapk_id == "test-uapk-v1"
        assert request.agent_id == "agent-123"
        assert request.action == sample_action
        assert request.counterparty is None
        assert request.context == {}

    def test_action_request_full(self, sample_action, sample_counterparty):
        """Test GatewayActionRequest with all fields."""
        request = GatewayActionRequest(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
            counterparty=sample_counterparty,
            context={"key": "value"},
            capability_token="cap_xyz",
            override_token="override_xyz",
        )

        assert request.counterparty is not None
        assert request.context == {"key": "value"}
        assert request.capability_token == "cap_xyz"
        assert request.override_token == "override_xyz"

    def test_action_request_serialization(self, sample_action):
        """Test GatewayActionRequest serialization."""
        request = GatewayActionRequest(
            uapk_id="test-uapk-v1",
            agent_id="agent-123",
            action=sample_action,
        )

        data = request.model_dump(exclude_none=True)
        assert data["uapk_id"] == "test-uapk-v1"
        assert data["agent_id"] == "agent-123"
        assert "action" in data
        assert "counterparty" not in data  # None excluded


class TestGatewayDecisionResponse:
    """Test GatewayDecisionResponse model."""

    def test_decision_response_allow(self):
        """Test GatewayDecisionResponse with ALLOW decision."""
        response = GatewayDecisionResponse(
            interaction_id="int_123",
            decision=GatewayDecision.ALLOW,
            reasons=[
                ReasonDetail(
                    code=ReasonCode.POLICY_ALLOWS,
                    message="Action allowed",
                )
            ],
            timestamp=datetime.now(UTC),
            policy_version="v1.0.0",
        )

        assert response.decision == GatewayDecision.ALLOW
        assert response.approval_id is None

    def test_decision_response_deny(self):
        """Test GatewayDecisionResponse with DENY decision."""
        response = GatewayDecisionResponse(
            interaction_id="int_123",
            decision=GatewayDecision.DENY,
            reasons=[
                ReasonDetail(
                    code=ReasonCode.ACTION_TYPE_DENIED,
                    message="Action type not allowed",
                )
            ],
            timestamp=datetime.now(UTC),
            policy_version="v1.0.0",
        )

        assert response.decision == GatewayDecision.DENY
        assert len(response.reasons) == 1

    def test_decision_response_escalate(self):
        """Test GatewayDecisionResponse with ESCALATE decision."""
        response = GatewayDecisionResponse(
            interaction_id="int_123",
            decision=GatewayDecision.ESCALATE,
            reasons=[
                ReasonDetail(
                    code=ReasonCode.APPROVAL_REQUIRED,
                    message="Approval required",
                )
            ],
            approval_id="appr_123",
            timestamp=datetime.now(UTC),
            policy_version="v1.0.0",
        )

        assert response.decision == GatewayDecision.ESCALATE
        assert response.approval_id == "appr_123"

    def test_decision_enum_values(self):
        """Test GatewayDecision enum values."""
        assert GatewayDecision.ALLOW == "ALLOW"
        assert GatewayDecision.DENY == "DENY"
        assert GatewayDecision.ESCALATE == "ESCALATE"

    def test_decision_response_from_dict(self):
        """Test creating GatewayDecisionResponse from dict."""
        data = {
            "interaction_id": "int_123",
            "decision": "ALLOW",
            "reasons": [
                {
                    "code": "POLICY_ALLOWS",
                    "message": "OK",
                    "details": None,
                }
            ],
            "approval_id": None,
            "timestamp": "2024-01-01T00:00:00Z",
            "policy_version": "v1.0.0",
        }

        response = GatewayDecisionResponse(**data)
        assert response.decision == GatewayDecision.ALLOW
        assert response.interaction_id == "int_123"


class TestToolResult:
    """Test ToolResult model."""

    def test_tool_result_success(self):
        """Test ToolResult with success."""
        result = ToolResult(
            success=True,
            data={"output": "Test result"},
            result_hash="hash_123",
            duration_ms=42,
        )

        assert result.success is True
        assert result.data["output"] == "Test result"
        assert result.error is None
        assert result.duration_ms == 42

    def test_tool_result_error(self):
        """Test ToolResult with error."""
        result = ToolResult(
            success=False,
            error={"message": "Tool failed", "code": "EXEC_ERROR"},
            duration_ms=10,
        )

        assert result.success is False
        assert result.data is None
        assert result.error["message"] == "Tool failed"

    def test_tool_result_serialization(self):
        """Test ToolResult serialization."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
        )

        data = result.model_dump(exclude_none=True)
        assert data["success"] is True
        assert data["data"] == {"key": "value"}
        assert "error" not in data
        assert "result_hash" not in data


class TestGatewayExecuteResponse:
    """Test GatewayExecuteResponse model."""

    def test_execute_response_success(self):
        """Test GatewayExecuteResponse with successful execution."""
        response = GatewayExecuteResponse(
            interaction_id="int_123",
            decision=GatewayDecision.ALLOW,
            reasons=[
                ReasonDetail(
                    code=ReasonCode.POLICY_ALLOWS,
                    message="OK",
                )
            ],
            timestamp=datetime.now(UTC),
            policy_version="v1.0.0",
            executed=True,
            result=ToolResult(
                success=True,
                data={"output": "Success"},
            ),
        )

        assert response.executed is True
        assert response.result is not None
        assert response.result.success is True

    def test_execute_response_not_executed(self):
        """Test GatewayExecuteResponse when not executed."""
        response = GatewayExecuteResponse(
            interaction_id="int_123",
            decision=GatewayDecision.DENY,
            reasons=[
                ReasonDetail(
                    code=ReasonCode.ACTION_TYPE_DENIED,
                    message="Denied",
                )
            ],
            timestamp=datetime.now(UTC),
            policy_version="v1.0.0",
            executed=False,
            result=None,
        )

        assert response.executed is False
        assert response.result is None

    def test_execute_response_from_dict(self):
        """Test creating GatewayExecuteResponse from dict."""
        data = {
            "interaction_id": "int_123",
            "decision": "ALLOW",
            "reasons": [{"code": "POLICY_ALLOWS", "message": "OK", "details": None}],
            "timestamp": "2024-01-01T00:00:00Z",
            "policy_version": "v1.0.0",
            "executed": True,
            "result": {
                "success": True,
                "data": {"output": "Test"},
                "result_hash": "hash_123",
                "duration_ms": 42,
            },
        }

        response = GatewayExecuteResponse(**data)
        assert response.executed is True
        assert response.result.success is True
        assert response.result.data["output"] == "Test"


class TestModelValidation:
    """Test model validation edge cases."""

    def test_empty_params(self):
        """Test ActionInfo with empty params dict."""
        action = ActionInfo(type="test", tool="test", params={})
        assert action.params == {}

    def test_nested_params(self):
        """Test ActionInfo with nested params."""
        action = ActionInfo(
            type="test",
            tool="test",
            params={
                "level1": {
                    "level2": {
                        "value": "deep"
                    }
                }
            }
        )
        assert action.params["level1"]["level2"]["value"] == "deep"

    def test_invalid_decision_value(self):
        """Test validation fails with invalid decision value."""
        with pytest.raises(ValidationError):
            GatewayDecisionResponse(
                interaction_id="int_123",
                decision="INVALID",  # Invalid enum value
                reasons=[],
                timestamp=datetime.now(UTC),
                policy_version="v1.0.0",
            )

    def test_invalid_reason_code(self):
        """Test validation fails with invalid reason code."""
        with pytest.raises(ValidationError):
            ReasonDetail(
                code="INVALID_CODE",  # Invalid enum value
                message="Test",
            )

    def test_model_round_trip(self, sample_execute_response):
        """Test model can be serialized and deserialized."""
        # Serialize
        data = sample_execute_response.model_dump()

        # Deserialize
        restored = GatewayExecuteResponse(**data)

        # Compare
        assert restored.interaction_id == sample_execute_response.interaction_id
        assert restored.decision == sample_execute_response.decision
        assert restored.executed == sample_execute_response.executed
