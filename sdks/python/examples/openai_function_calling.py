"""Example: Using UAPK Gateway with OpenAI Function Calling.

This example demonstrates how to intercept OpenAI function calls and route them
through UAPK Gateway for compliance, approval workflows, and audit logging.

The pattern shown here works with:
- OpenAI ChatCompletion API with function calling
- Azure OpenAI
- Any OpenAI-compatible API (Anthropic, Mistral, etc.)

Usage:
    python examples/openai_function_calling.py
"""

import json
import os
from typing import Any

from openai import OpenAI

from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo, CounterpartyInfo
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError


# ============================================================================
# 1. Define your functions (tools) that will be called
# ============================================================================


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email (example function - not actually implemented)."""
    print(f"\n[MOCK] Sending email to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body}\n")
    return {"success": True, "message_id": "msg_12345"}


def refund_charge(charge_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Process a refund (example function - not actually implemented)."""
    print(f"\n[MOCK] Processing refund for charge {charge_id}")
    print(f"Amount: ${amount}")
    print(f"Reason: {reason}\n")
    return {"success": True, "refund_id": "re_67890", "amount": amount}


def search_customer_database(query: str) -> dict[str, Any]:
    """Search customer database (example function - not actually implemented)."""
    print(f"\n[MOCK] Searching customers for: {query}\n")
    return {
        "results": [
            {"id": "cust_001", "name": "Alice", "email": "alice@example.com"},
            {"id": "cust_002", "name": "Bob", "email": "bob@example.com"},
        ]
    }


# ============================================================================
# 2. Define OpenAI function schemas
# ============================================================================

FUNCTIONS = [
    {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "refund_charge",
        "description": "Process a refund for a charge",
        "parameters": {
            "type": "object",
            "properties": {
                "charge_id": {"type": "string", "description": "Stripe charge ID"},
                "amount": {"type": "number", "description": "Refund amount in dollars"},
                "reason": {"type": "string", "description": "Reason for refund"},
            },
            "required": ["charge_id", "amount", "reason"],
        },
    },
    {
        "name": "search_customer_database",
        "description": "Search the customer database",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
]


# Function registry
FUNCTION_REGISTRY = {
    "send_email": send_email,
    "refund_charge": refund_charge,
    "search_customer_database": search_customer_database,
}


# ============================================================================
# 3. Gateway-aware function executor
# ============================================================================


class GatewayFunctionExecutor:
    """Executes OpenAI function calls through UAPK Gateway.

    This class intercepts OpenAI function calls and routes them through
    the gateway for policy evaluation, approval workflows, and audit logging.
    """

    def __init__(
        self,
        gateway_client: UAPKGatewayClient,
        uapk_id: str,
        agent_id: str,
        function_registry: dict,
    ):
        """Initialize the executor.

        Args:
            gateway_client: UAPK Gateway client
            uapk_id: UAPK manifest ID
            agent_id: Agent instance ID
            function_registry: Map of function name -> callable
        """
        self.gateway_client = gateway_client
        self.uapk_id = uapk_id
        self.agent_id = agent_id
        self.function_registry = function_registry

    def execute_function(self, function_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a function through the gateway.

        Args:
            function_name: Name of the function to call
            arguments: Function arguments from OpenAI

        Returns:
            Function execution result

        Raises:
            ActionDeniedError: If action is denied by gateway
            ActionEscalatedError: If action requires approval
        """
        print(f"🔒 Gateway: Evaluating {function_name} with args: {arguments}")

        # Map function to action type
        action_type_map = {
            "send_email": "send_email",
            "refund_charge": "refund",
            "search_customer_database": "database_query",
        }
        action_type = action_type_map.get(function_name, "function_call")

        # Extract counterparty if applicable
        counterparty = None
        if function_name == "send_email" and "to" in arguments:
            counterparty = CounterpartyInfo(
                email=arguments["to"],
                domain=arguments["to"].split("@")[1] if "@" in arguments["to"] else None,
            )

        # Extract amount if applicable
        amount = None
        currency = None
        if function_name == "refund_charge" and "amount" in arguments:
            amount = float(arguments["amount"])
            currency = "USD"

        # Create action
        action = ActionInfo(
            type=action_type,
            tool=function_name,
            params=arguments,
            amount=amount,
            currency=currency,
            description=f"{action_type} via OpenAI function calling",
        )

        try:
            # Route through gateway
            response = self.gateway_client.execute(
                uapk_id=self.uapk_id,
                agent_id=self.agent_id,
                action=action,
                counterparty=counterparty,
                raise_on_deny=True,
                raise_on_escalate=True,
            )

            print(f"✅ Gateway: {response.decision} - {response.reasons[0].message if response.reasons else 'Allowed'}")

            # If gateway executed the tool, return that result
            if response.executed and response.result:
                return response.result.data or {}

            # Otherwise, execute the function locally
            if function_name not in self.function_registry:
                return {"error": f"Function {function_name} not found"}

            func = self.function_registry[function_name]
            result = func(**arguments)
            return result

        except ActionDeniedError as e:
            print(f"❌ Gateway: Action DENIED - {e}")
            return {"error": f"Action denied by gateway: {e}", "denied": True}

        except ActionEscalatedError as e:
            print(f"⏳ Gateway: Action ESCALATED - Approval required")
            print(f"   Approval ID: {e.approval_id}")
            return {
                "error": "Action requires approval",
                "approval_id": e.approval_id,
                "escalated": True,
            }


# ============================================================================
# 4. Main agent loop
# ============================================================================


def run_agent(user_message: str):
    """Run an OpenAI agent with gateway-protected function calling.

    Args:
        user_message: User's input message
    """
    # Initialize clients
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    gateway_client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    executor = GatewayFunctionExecutor(
        gateway_client=gateway_client,
        uapk_id=os.getenv("UAPK_ID", "customer-service-bot-v1"),
        agent_id=os.getenv("AGENT_ID", "agent-openai-001"),
        function_registry=FUNCTION_REGISTRY,
    )

    # Conversation history
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful customer service agent. You can send emails, "
                "process refunds, and search customer data. Always be polite and "
                "confirm actions before executing them."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    print(f"\n{'='*80}")
    print(f"User: {user_message}")
    print(f"{'='*80}\n")

    # Agent loop (max 5 iterations to prevent infinite loops)
    for iteration in range(5):
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto",
        )

        message = response.choices[0].message

        # Add assistant message to history
        messages.append(message.model_dump())

        # Check if function call
        if message.function_call:
            function_name = message.function_call.name
            arguments = json.loads(message.function_call.arguments)

            # Execute through gateway
            result = executor.execute_function(function_name, arguments)

            # Add function result to conversation
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(result),
                }
            )

            # Handle approval required
            if result.get("escalated"):
                print("\n🔔 ACTION REQUIRES APPROVAL")
                print(f"   Approval ID: {result['approval_id']}")
                print("   Waiting for human operator to approve/deny this action...")
                print("   (In production, agent would poll approval endpoint)\n")
                break

            # Handle denial
            if result.get("denied"):
                print("\n🚫 ACTION DENIED BY GATEWAY")
                print("   Agent will inform user that action is not allowed.\n")
                # Continue loop so agent can respond to user

        else:
            # No function call - agent is done
            print(f"\nAssistant: {message.content}\n")
            break

    gateway_client.close()


# ============================================================================
# 5. Example scenarios
# ============================================================================


def main():
    """Run example scenarios."""

    print("\n" + "=" * 80)
    print("UAPK Gateway + OpenAI Function Calling Examples")
    print("=" * 80)

    # Scenario 1: Low-risk action (should be allowed)
    print("\n\n📧 SCENARIO 1: Send a routine email (low risk)")
    print("-" * 80)
    run_agent("Send an email to alice@example.com saying 'Your order has shipped!'")

    # Scenario 2: High-risk action (might require approval)
    print("\n\n💰 SCENARIO 2: Process a large refund (high risk)")
    print("-" * 80)
    run_agent("Refund charge ch_12345 for $5000 due to product defect")

    # Scenario 3: Read-only action (low risk)
    print("\n\n🔍 SCENARIO 3: Search customer database (read-only)")
    print("-" * 80)
    run_agent("Search for customers named 'Alice'")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Check for required env vars
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set. Using mock responses.")
        print("   Set OPENAI_API_KEY to run real examples.\n")

    # Set defaults for local testing
    os.environ.setdefault("GATEWAY_URL", "http://localhost:8000")
    os.environ.setdefault("GATEWAY_API_KEY", "test-api-key")
    os.environ.setdefault("UAPK_ID", "customer-service-bot-v1")
    os.environ.setdefault("AGENT_ID", "agent-openai-001")

    if os.getenv("OPENAI_API_KEY"):
        main()
    else:
        print("Skipping examples - set OPENAI_API_KEY to run.")
