"""Example: Using UAPK Gateway with LangChain agents.

This example shows how to wrap LangChain tools with UAPK Gateway for
compliance and audit in LangChain agents.

Requirements:
    pip install langchain langchain-openai duckduckgo-search

Usage:
    export OPENAI_API_KEY=your-openai-key
    export GATEWAY_URL=http://localhost:8000
    export GATEWAY_API_KEY=your-gateway-key
    python examples/langchain_integration.py
"""

import os
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool

from uapk_gateway import UAPKGatewayClient
from uapk_gateway.integrations.langchain import UAPKGatewayTool, wrap_langchain_tools
from uapk_gateway.models import CounterpartyInfo
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError


# ============================================================================
# Define some example tools
# ============================================================================


def send_email_tool(to: str, subject: str, body: str) -> str:
    """Send an email (mock implementation)."""
    print(f"\n📧 [MOCK] Sending email:")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")
    print(f"   Body: {body}\n")
    return f"Email sent successfully to {to}"


def database_query_tool(query: str) -> str:
    """Query database (mock implementation)."""
    print(f"\n🔍 [MOCK] Database query: {query}\n")
    return "Found 3 matching records"


def refund_tool(customer_email: str, amount: float, reason: str) -> str:
    """Process refund (mock implementation)."""
    print(f"\n💰 [MOCK] Processing refund:")
    print(f"   Customer: {customer_email}")
    print(f"   Amount: ${amount}")
    print(f"   Reason: {reason}\n")
    return f"Refund of ${amount} processed for {customer_email}"


# ============================================================================
# Example 1: Basic tool wrapping
# ============================================================================


def example_basic_wrapping():
    """Example: Wrap a single LangChain tool."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Tool Wrapping")
    print("=" * 80 + "\n")

    # Create gateway client
    gateway_client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    # Create a LangChain tool
    email_tool = Tool(
        name="SendEmail",
        func=lambda input_str: send_email_tool(
            to=input_str.split("|")[0],
            subject=input_str.split("|")[1],
            body=input_str.split("|")[2],
        ),
        description="Send an email. Input format: 'to|subject|body'",
    )

    # Wrap with gateway
    gateway_email_tool = UAPKGatewayTool(
        tool=email_tool,
        gateway_client=gateway_client,
        uapk_id="email-agent-v1",
        agent_id="langchain-agent-001",
        action_type="send_email",
    )

    # Use the tool (now protected by gateway)
    try:
        result = gateway_email_tool.run("user@example.com|Hello|Test message")
        print(f"Result: {result}")
    except ActionDeniedError as e:
        print(f"❌ Action denied: {e}")
    except ActionEscalatedError as e:
        print(f"⏳ Approval required: {e.approval_id}")

    gateway_client.close()


# ============================================================================
# Example 2: Wrap multiple tools at once
# ============================================================================


def example_batch_wrapping():
    """Example: Wrap multiple tools at once."""
    print("\n" + "=" * 80)
    print("Example 2: Batch Tool Wrapping")
    print("=" * 80 + "\n")

    gateway_client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    # Create multiple tools
    tools = [
        Tool(
            name="SendEmail",
            func=lambda x: send_email_tool("user@example.com", "Subject", x),
            description="Send an email",
        ),
        Tool(
            name="DatabaseQuery",
            func=database_query_tool,
            description="Query the database",
        ),
        Tool(
            name="ProcessRefund",
            func=lambda x: refund_tool("customer@example.com", 100.0, x),
            description="Process a refund",
        ),
    ]

    # Wrap all tools at once
    wrapped_tools = wrap_langchain_tools(
        tools=tools,
        gateway_client=gateway_client,
        uapk_id="customer-service-v1",
        agent_id="langchain-agent-002",
        action_type_map={
            "SendEmail": "send_email",
            "DatabaseQuery": "database_query",
            "ProcessRefund": "refund",
        },
        handle_approval_required="raise",  # Raise exception on escalation
    )

    print(f"✅ Wrapped {len(wrapped_tools)} tools with UAPK Gateway")

    # Test each tool
    for tool in wrapped_tools:
        print(f"\nTesting {tool.name}...")
        try:
            result = tool.run("test input")
            print(f"  Result: {result}")
        except (ActionDeniedError, ActionEscalatedError) as e:
            print(f"  Gateway response: {e}")

    gateway_client.close()


# ============================================================================
# Example 3: Full agent with wrapped tools
# ============================================================================


def example_full_agent():
    """Example: LangChain agent with gateway-protected tools."""
    print("\n" + "=" * 80)
    print("Example 3: Full LangChain Agent with Gateway")
    print("=" * 80 + "\n")

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Skipping agent example - OPENAI_API_KEY not set")
        return

    # Initialize gateway client
    gateway_client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    # Create tools
    tools = [
        Tool(
            name="SendEmail",
            func=lambda input_str: send_email_tool(
                to=input_str.split("|")[0],
                subject=input_str.split("|")[1],
                body=input_str.split("|")[2] if len(input_str.split("|")) > 2 else "",
            ),
            description="Send an email. Input: 'to|subject|body'",
        ),
        Tool(
            name="SearchCustomers",
            func=database_query_tool,
            description="Search customer database. Input: search query",
        ),
    ]

    # Wrap tools with gateway
    wrapped_tools = wrap_langchain_tools(
        tools=tools,
        gateway_client=gateway_client,
        uapk_id="customer-service-v1",
        agent_id="langchain-agent-003",
        action_type_map={
            "SendEmail": "send_email",
            "SearchCustomers": "database_query",
        },
        handle_approval_required="deny",  # Treat escalations as denials
    )

    # Create LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # Create prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a customer service agent. Be helpful and polite."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # Create agent
    agent = create_openai_functions_agent(llm, wrapped_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=wrapped_tools, verbose=True)

    # Run agent
    print("\n🤖 Running agent with gateway-protected tools...\n")

    try:
        result = agent_executor.invoke(
            {"input": "Search for customers named Alice and send them an email about our sale"}
        )
        print(f"\n✅ Agent completed:")
        print(f"   {result['output']}")

    except Exception as e:
        print(f"\n❌ Agent error: {e}")

    gateway_client.close()


# ============================================================================
# Example 4: Advanced - Custom counterparty extraction
# ============================================================================


def example_custom_counterparty():
    """Example: Custom counterparty extraction from tool input."""
    print("\n" + "=" * 80)
    print("Example 4: Custom Counterparty Extraction")
    print("=" * 80 + "\n")

    gateway_client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    # Create email tool
    email_tool = Tool(
        name="SendEmail",
        func=lambda x: send_email_tool("user@example.com", "Subject", x),
        description="Send an email",
    )

    # Custom counterparty extraction function
    def extract_counterparty(params: dict) -> CounterpartyInfo | None:
        """Extract counterparty info from tool parameters."""
        if "query" in params:
            # Parse email from query string
            query = params["query"]
            if "@" in query:
                email = query.split()[0]  # First word with @
                domain = email.split("@")[1] if "@" in email else None
                return CounterpartyInfo(email=email, domain=domain)
        return None

    # Wrap with custom extraction
    gateway_email_tool = UAPKGatewayTool(
        tool=email_tool,
        gateway_client=gateway_client,
        uapk_id="email-agent-v1",
        agent_id="langchain-agent-004",
        action_type="send_email",
        get_counterparty=extract_counterparty,  # Custom extraction
    )

    print("✅ Tool wrapped with custom counterparty extraction")

    gateway_client.close()


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("UAPK Gateway + LangChain Integration Examples")
    print("=" * 80)

    example_basic_wrapping()
    example_batch_wrapping()
    example_full_agent()
    example_custom_counterparty()

    print("\n" + "=" * 80)
    print("✅ All examples complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
