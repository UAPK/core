"""LangChain integration for UAPK Gateway.

This module provides a wrapper that routes LangChain tool calls through UAPK Gateway
for compliance, audit, and approval workflows.

Example:
    >>> from langchain.tools import DuckDuckGoSearchRun
    >>> from uapk_gateway.integrations.langchain import UAPKGatewayTool
    >>> from uapk_gateway import UAPKGatewayClient
    >>>
    >>> # Create gateway client
    >>> gateway_client = UAPKGatewayClient(
    ...     base_url="https://gateway.yourcompany.com",
    ...     api_key="your-api-key"
    ... )
    >>>
    >>> # Wrap existing tool
    >>> search_tool = DuckDuckGoSearchRun()
    >>> gateway_search = UAPKGatewayTool(
    ...     tool=search_tool,
    ...     gateway_client=gateway_client,
    ...     uapk_id="search-agent-v1",
    ...     agent_id="agent-123",
    ...     action_type="web_search"
    ... )
    >>>
    >>> # Use in LangChain agent (calls now go through gateway)
    >>> result = gateway_search.run("latest AI news")
"""

from typing import Any, Callable

try:
    from langchain.tools import BaseTool
    from langchain.callbacks.manager import (
        AsyncCallbackManagerForToolRun,
        CallbackManagerForToolRun,
    )
    from pydantic import Field
except ImportError:
    raise ImportError(
        "LangChain integration requires langchain package. "
        "Install with: pip install langchain"
    )

from uapk_gateway.client import UAPKGatewayClient
from uapk_gateway.async_client import AsyncUAPKGatewayClient
from uapk_gateway.models import ActionInfo, CounterpartyInfo
from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    ToolExecutionError,
)


class UAPKGatewayTool(BaseTool):
    """LangChain tool wrapper that routes calls through UAPK Gateway.

    This tool wraps an existing LangChain tool and intercepts all executions
    to route them through the UAPK Gateway for policy evaluation, approval
    workflows, and audit logging.

    Attributes:
        tool: The underlying LangChain tool to wrap
        gateway_client: Sync gateway client instance
        async_gateway_client: Async gateway client instance (optional)
        uapk_id: UAPK manifest ID for policy evaluation
        agent_id: Agent instance identifier
        action_type: Action type for gateway (e.g., "web_search", "send_email")
        tool_name: Tool identifier in gateway (defaults to LangChain tool name)
        get_counterparty: Optional function to extract counterparty from tool input
        get_context: Optional function to extract additional context from tool input
        capability_token: Optional capability token for delegated actions
        handle_approval_required: How to handle ESCALATE decisions
            - "raise": Raise ActionEscalatedError (default)
            - "deny": Treat as DENY
            - "wait": Poll for approval (requires poll_interval/max_wait)
        poll_interval: Seconds between approval status checks (default: 5)
        max_wait: Maximum seconds to wait for approval (default: 300)
    """

    # Gateway configuration
    tool: BaseTool = Field(description="Underlying LangChain tool")
    gateway_client: UAPKGatewayClient | None = Field(default=None)
    async_gateway_client: AsyncUAPKGatewayClient | None = Field(default=None)
    uapk_id: str = Field(description="UAPK manifest ID")
    agent_id: str = Field(description="Agent instance ID")
    action_type: str = Field(description="Action type for gateway")
    tool_name: str | None = Field(default=None, description="Tool name override")

    # Dynamic context extraction
    get_counterparty: Callable[[dict], CounterpartyInfo | None] | None = Field(default=None)
    get_context: Callable[[dict], dict] | None = Field(default=None)
    capability_token: str | None = Field(default=None)

    # Approval handling
    handle_approval_required: str = Field(default="raise")
    poll_interval: int = Field(default=5)
    max_wait: int = Field(default=300)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        # Inherit name and description from wrapped tool
        if "name" not in data and "tool" in data:
            data["name"] = data["tool"].name
        if "description" not in data and "tool" in data:
            data["description"] = data["tool"].description

        super().__init__(**data)

        # Validate gateway client
        if not self.gateway_client and not self.async_gateway_client:
            raise ValueError("Either gateway_client or async_gateway_client must be provided")

    def _prepare_action(self, tool_input: str | dict) -> tuple[ActionInfo, CounterpartyInfo | None, dict]:
        """Prepare gateway action from tool input.

        Args:
            tool_input: Input to the wrapped tool

        Returns:
            Tuple of (ActionInfo, CounterpartyInfo, context dict)
        """
        # Convert string input to dict
        if isinstance(tool_input, str):
            params = {"query": tool_input}
        else:
            params = tool_input

        # Create action
        action = ActionInfo(
            type=self.action_type,
            tool=self.tool_name or self.tool.name,
            params=params,
            description=f"{self.action_type} via {self.tool.name}",
        )

        # Extract counterparty if configured
        counterparty = None
        if self.get_counterparty:
            counterparty = self.get_counterparty(params)

        # Extract additional context if configured
        context = {}
        if self.get_context:
            context = self.get_context(params)

        return action, counterparty, context

    def _run(
        self,
        tool_input: str | dict,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """Execute tool through gateway (sync).

        Args:
            tool_input: Input to the tool
            run_manager: LangChain callback manager

        Returns:
            Tool execution result

        Raises:
            ActionDeniedError: If action is denied by gateway
            ActionEscalatedError: If approval required and handle_approval_required="raise"
            ToolExecutionError: If tool execution fails
        """
        if not self.gateway_client:
            raise RuntimeError("Sync gateway_client not configured. Use async_gateway_client for async execution.")

        action, counterparty, context = self._prepare_action(tool_input)

        try:
            # Route through gateway
            if self.handle_approval_required == "wait":
                response = self.gateway_client.execute_with_retry_on_escalate(
                    uapk_id=self.uapk_id,
                    agent_id=self.agent_id,
                    action=action,
                    counterparty=counterparty,
                    context=context,
                    capability_token=self.capability_token,
                    poll_interval=self.poll_interval,
                    max_wait=self.max_wait,
                )
            else:
                response = self.gateway_client.execute(
                    uapk_id=self.uapk_id,
                    agent_id=self.agent_id,
                    action=action,
                    counterparty=counterparty,
                    context=context,
                    capability_token=self.capability_token,
                    raise_on_deny=True,
                    raise_on_escalate=(self.handle_approval_required == "raise"),
                    raise_on_tool_error=True,
                )

            # If ESCALATE and handle_approval_required="deny", treat as denial
            if response.decision == "ESCALATE" and self.handle_approval_required == "deny":
                reasons_str = ", ".join([r.message for r in response.reasons])
                raise ActionDeniedError(
                    f"Action requires approval (treated as deny): {reasons_str}",
                    decision_response={"decision": "ESCALATE", "reasons": response.reasons},
                )

            # Extract result from gateway response
            if response.executed and response.result and response.result.success:
                # Gateway executed the tool - return result
                return str(response.result.data.get("output", ""))
            else:
                # Gateway allowed but didn't execute - run tool directly
                return self.tool._run(tool_input, run_manager=run_manager)

        except (ActionDeniedError, ActionEscalatedError, ToolExecutionError):
            # Re-raise gateway exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ToolExecutionError(
                f"Unexpected error during gateway execution: {str(e)}",
                tool_result={"error": {"message": str(e)}},
            ) from e

    async def _arun(
        self,
        tool_input: str | dict,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        """Execute tool through gateway (async).

        Args:
            tool_input: Input to the tool
            run_manager: LangChain async callback manager

        Returns:
            Tool execution result

        Raises:
            ActionDeniedError: If action is denied by gateway
            ActionEscalatedError: If approval required and handle_approval_required="raise"
            ToolExecutionError: If tool execution fails
        """
        if not self.async_gateway_client:
            raise RuntimeError("Async async_gateway_client not configured. Use gateway_client for sync execution.")

        action, counterparty, context = self._prepare_action(tool_input)

        try:
            # Route through gateway
            if self.handle_approval_required == "wait":
                response = await self.async_gateway_client.execute_with_retry_on_escalate(
                    uapk_id=self.uapk_id,
                    agent_id=self.agent_id,
                    action=action,
                    counterparty=counterparty,
                    context=context,
                    capability_token=self.capability_token,
                    poll_interval=self.poll_interval,
                    max_wait=self.max_wait,
                )
            else:
                response = await self.async_gateway_client.execute(
                    uapk_id=self.uapk_id,
                    agent_id=self.agent_id,
                    action=action,
                    counterparty=counterparty,
                    context=context,
                    capability_token=self.capability_token,
                    raise_on_deny=True,
                    raise_on_escalate=(self.handle_approval_required == "raise"),
                    raise_on_tool_error=True,
                )

            # If ESCALATE and handle_approval_required="deny", treat as denial
            if response.decision == "ESCALATE" and self.handle_approval_required == "deny":
                reasons_str = ", ".join([r.message for r in response.reasons])
                raise ActionDeniedError(
                    f"Action requires approval (treated as deny): {reasons_str}",
                    decision_response={"decision": "ESCALATE", "reasons": response.reasons},
                )

            # Extract result from gateway response
            if response.executed and response.result and response.result.success:
                # Gateway executed the tool - return result
                return str(response.result.data.get("output", ""))
            else:
                # Gateway allowed but didn't execute - run tool directly
                return await self.tool._arun(tool_input, run_manager=run_manager)

        except (ActionDeniedError, ActionEscalatedError, ToolExecutionError):
            # Re-raise gateway exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ToolExecutionError(
                f"Unexpected error during gateway execution: {str(e)}",
                tool_result={"error": {"message": str(e)}},
            ) from e


def wrap_langchain_tools(
    tools: list[BaseTool],
    gateway_client: UAPKGatewayClient | AsyncUAPKGatewayClient,
    uapk_id: str,
    agent_id: str,
    action_type_map: dict[str, str] | None = None,
    **kwargs,
) -> list[UAPKGatewayTool]:
    """Wrap multiple LangChain tools with UAPK Gateway.

    Args:
        tools: List of LangChain tools to wrap
        gateway_client: Gateway client instance (sync or async)
        uapk_id: UAPK manifest ID
        agent_id: Agent instance ID
        action_type_map: Map of tool name -> action type (optional)
        **kwargs: Additional arguments passed to UAPKGatewayTool

    Returns:
        List of wrapped tools

    Example:
        >>> from langchain.tools import DuckDuckGoSearchRun, WikipediaQueryRun
        >>> tools = [DuckDuckGoSearchRun(), WikipediaQueryRun()]
        >>> wrapped = wrap_langchain_tools(
        ...     tools=tools,
        ...     gateway_client=client,
        ...     uapk_id="search-agent-v1",
        ...     agent_id="agent-123",
        ...     action_type_map={
        ...         "DuckDuckGo Search": "web_search",
        ...         "Wikipedia": "knowledge_lookup"
        ...     }
        ... )
    """
    wrapped_tools = []

    for tool in tools:
        # Determine action type
        action_type = "tool_use"
        if action_type_map and tool.name in action_type_map:
            action_type = action_type_map[tool.name]

        # Determine client type
        client_kwargs = {}
        if isinstance(gateway_client, UAPKGatewayClient):
            client_kwargs["gateway_client"] = gateway_client
        else:
            client_kwargs["async_gateway_client"] = gateway_client

        wrapped = UAPKGatewayTool(
            tool=tool,
            uapk_id=uapk_id,
            agent_id=agent_id,
            action_type=action_type,
            **client_kwargs,
            **kwargs,
        )
        wrapped_tools.append(wrapped)

    return wrapped_tools
