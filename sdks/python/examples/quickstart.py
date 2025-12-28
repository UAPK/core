"""Quickstart example for UAPK Gateway Python SDK.

This example shows the basic usage patterns for the SDK.

Usage:
    export GATEWAY_URL=http://localhost:8000
    export GATEWAY_API_KEY=your-api-key
    python examples/quickstart.py
"""

import os
from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo, CounterpartyInfo
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError


def main():
    # Initialize client
    client = UAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    )

    # Example 1: Simple action evaluation (dry-run)
    print("\n" + "=" * 60)
    print("Example 1: Evaluate an action (dry-run)")
    print("=" * 60)

    action = ActionInfo(
        type="send_email",
        tool="smtp_connector",
        params={
            "to": "user@example.com",
            "subject": "Order confirmation",
            "body": "Your order has been confirmed!",
        },
    )

    response = client.evaluate(
        uapk_id="email-agent-v1",
        agent_id="agent-001",
        action=action,
    )

    print(f"Decision: {response.decision}")
    print(f"Reasons: {[r.message for r in response.reasons]}")

    # Example 2: Execute an action
    print("\n" + "=" * 60)
    print("Example 2: Execute an action")
    print("=" * 60)

    try:
        response = client.execute(
            uapk_id="email-agent-v1",
            agent_id="agent-001",
            action=action,
            raise_on_deny=True,
            raise_on_escalate=True,
        )

        print(f"Decision: {response.decision}")
        if response.executed and response.result:
            print(f"Executed: {response.result.success}")
            print(f"Result: {response.result.data}")

    except ActionDeniedError as e:
        print(f"❌ Action denied: {e}")
        print(f"   Reasons: {[r['message'] for r in e.reasons]}")

    except ActionEscalatedError as e:
        print(f"⏳ Action requires approval")
        print(f"   Approval ID: {e.approval_id}")

    # Example 3: Execute with counterparty info
    print("\n" + "=" * 60)
    print("Example 3: Execute with counterparty information")
    print("=" * 60)

    refund_action = ActionInfo(
        type="refund",
        tool="stripe_api",
        params={"charge_id": "ch_12345", "reason": "Customer request"},
        amount=100.00,
        currency="USD",
    )

    counterparty = CounterpartyInfo(
        email="customer@example.com",
        jurisdiction="US",
    )

    try:
        response = client.execute(
            uapk_id="refund-bot-v1",
            agent_id="agent-002",
            action=refund_action,
            counterparty=counterparty,
        )
        print(f"Decision: {response.decision}")

    except ActionEscalatedError as e:
        print(f"⏳ Refund requires approval (amount > threshold)")
        print(f"   Approval ID: {e.approval_id}")

        # Example 4: Check approval status
        print("\n" + "=" * 60)
        print("Example 4: Check approval status")
        print("=" * 60)

        approval = client.get_approval_status(e.approval_id)
        print(f"Approval status: {approval['status']}")
        print(f"Created at: {approval['created_at']}")

    # Example 5: Execute with automatic approval waiting
    print("\n" + "=" * 60)
    print("Example 5: Execute with automatic approval waiting")
    print("=" * 60)

    print("(This will wait up to 60 seconds for approval...)")

    try:
        response = client.execute_with_retry_on_escalate(
            uapk_id="refund-bot-v1",
            agent_id="agent-002",
            action=refund_action,
            counterparty=counterparty,
            poll_interval=5,  # Check every 5 seconds
            max_wait=60,  # Wait max 60 seconds
        )

        print(f"✅ Action completed after approval!")
        print(f"Decision: {response.decision}")

    except TimeoutError:
        print(f"⏱️  Timeout: Approval not granted within 60 seconds")

    except ActionDeniedError:
        print(f"❌ Approval was denied")

    # Cleanup
    client.close()
    print("\n✅ All examples completed!")


if __name__ == "__main__":
    main()
