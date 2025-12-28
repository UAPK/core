"""Exceptions for UAPK Gateway SDK."""


class UAPKGatewayError(Exception):
    """Base exception for UAPK Gateway SDK."""

    pass


class AuthenticationError(UAPKGatewayError):
    """Raised when API key authentication fails."""

    pass


class ActionDeniedError(UAPKGatewayError):
    """Raised when an action is denied by the gateway."""

    def __init__(self, message: str, decision_response: dict):
        super().__init__(message)
        self.decision_response = decision_response
        self.reasons = decision_response.get("reasons", [])
        self.interaction_id = decision_response.get("interaction_id")


class ActionEscalatedError(UAPKGatewayError):
    """Raised when an action requires approval."""

    def __init__(self, message: str, decision_response: dict):
        super().__init__(message)
        self.decision_response = decision_response
        self.approval_id = decision_response.get("approval_id")
        self.interaction_id = decision_response.get("interaction_id")
        self.reasons = decision_response.get("reasons", [])


class ToolExecutionError(UAPKGatewayError):
    """Raised when tool execution fails."""

    def __init__(self, message: str, tool_result: dict):
        super().__init__(message)
        self.tool_result = tool_result
        self.error = tool_result.get("error", {})


class NetworkError(UAPKGatewayError):
    """Raised when network/HTTP errors occur."""

    pass


class ValidationError(UAPKGatewayError):
    """Raised when request validation fails."""

    pass


class RateLimitError(UAPKGatewayError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after
