"""Async usage example for UAPK Gateway Python SDK.

This example shows how to use the AsyncUAPKGatewayClient for concurrent operations.

Usage:
    export GATEWAY_URL=http://localhost:8000
    export GATEWAY_API_KEY=your-api-key
    python examples/async_usage.py
"""

import asyncio
import os
from uapk_gateway import AsyncUAPKGatewayClient
from uapk_gateway.models import ActionInfo
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError


async def evaluate_multiple_actions():
    """Example: Evaluate multiple actions concurrently."""
    print("\n" + "=" * 60)
    print("Example 1: Concurrent action evaluation")
    print("=" * 60)

    async with AsyncUAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    ) as client:
        # Create multiple actions
        actions = [
            ActionInfo(
                type="send_email",
                tool="smtp",
                params={"to": f"user{i}@example.com", "subject": "Hello"},
            )
            for i in range(5)
        ]

        # Evaluate all concurrently
        tasks = [
            client.evaluate(
                uapk_id="email-agent-v1",
                agent_id=f"agent-{i:03d}",
                action=action,
            )
            for i, action in enumerate(actions)
        ]

        results = await asyncio.gather(*tasks)

        # Print results
        for i, result in enumerate(results):
            print(f"Action {i}: {result.decision}")


async def execute_with_approval_handling():
    """Example: Execute action with approval workflow."""
    print("\n" + "=" * 60)
    print("Example 2: Execute with approval handling")
    print("=" * 60)

    async with AsyncUAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    ) as client:
        action = ActionInfo(
            type="refund",
            tool="stripe_api",
            params={"charge_id": "ch_12345"},
            amount=500.00,
            currency="USD",
        )

        try:
            response = await client.execute(
                uapk_id="refund-bot-v1",
                agent_id="agent-001",
                action=action,
                raise_on_escalate=True,
            )
            print(f"✅ Action completed: {response.decision}")

        except ActionEscalatedError as e:
            print(f"⏳ Action escalated for approval")
            print(f"   Approval ID: {e.approval_id}")

            # Poll for approval
            print("   Polling for approval (max 30s)...")
            for _ in range(6):  # Check 6 times over 30 seconds
                await asyncio.sleep(5)

                approval = await client.get_approval_status(e.approval_id)
                status = approval["status"]
                print(f"   Status: {status}")

                if status == "APPROVED":
                    # Retry with override token
                    response = await client.execute(
                        uapk_id="refund-bot-v1",
                        agent_id="agent-001",
                        action=action,
                        override_token=approval["override_token"],
                    )
                    print(f"✅ Action completed after approval!")
                    break

                elif status == "DENIED":
                    print(f"❌ Approval was denied")
                    break


async def execute_with_automatic_retry():
    """Example: Use execute_with_retry_on_escalate for automatic approval waiting."""
    print("\n" + "=" * 60)
    print("Example 3: Automatic approval retry")
    print("=" * 60)

    async with AsyncUAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    ) as client:
        action = ActionInfo(
            type="database_update",
            tool="postgres",
            params={"table": "users", "operation": "delete"},
        )

        try:
            # This will automatically wait for approval if escalated
            response = await client.execute_with_retry_on_escalate(
                uapk_id="admin-bot-v1",
                agent_id="agent-001",
                action=action,
                poll_interval=5,  # Check every 5 seconds
                max_wait=60,  # Wait max 60 seconds
            )

            print(f"✅ Action completed: {response.decision}")

        except TimeoutError:
            print(f"⏱️  Timeout: Approval not received within 60s")

        except ActionDeniedError:
            print(f"❌ Action was denied")


async def batch_operations():
    """Example: Process batch operations with concurrency control."""
    print("\n" + "=" * 60)
    print("Example 4: Batch operations with concurrency")
    print("=" * 60)

    async with AsyncUAPKGatewayClient(
        base_url=os.getenv("GATEWAY_URL", "http://localhost:8000"),
        api_key=os.getenv("GATEWAY_API_KEY", "test-api-key"),
    ) as client:
        # Simulate batch email sending
        recipients = [f"user{i}@example.com" for i in range(20)]

        # Process in batches of 5 to avoid overwhelming the gateway
        batch_size = 5
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            tasks = []
            for recipient in batch:
                action = ActionInfo(
                    type="send_email",
                    tool="smtp",
                    params={
                        "to": recipient,
                        "subject": "Batch notification",
                        "body": "This is a batch message",
                    },
                )

                task = client.execute(
                    uapk_id="email-agent-v1",
                    agent_id=f"batch-agent-{i}",
                    action=action,
                    raise_on_deny=False,  # Continue on deny
                    raise_on_escalate=False,  # Continue on escalate
                )
                tasks.append(task)

            # Execute batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count outcomes
            allowed = sum(1 for r in results if not isinstance(r, Exception) and r.decision == "ALLOW")
            denied = sum(1 for r in results if not isinstance(r, Exception) and r.decision == "DENY")
            escalated = sum(1 for r in results if not isinstance(r, Exception) and r.decision == "ESCALATE")

            print(f"Batch {i // batch_size + 1}: {allowed} allowed, {denied} denied, {escalated} escalated")


async def main():
    """Run all async examples."""
    print("\n" + "=" * 80)
    print("UAPK Gateway Python SDK - Async Examples")
    print("=" * 80)

    await evaluate_multiple_actions()
    await execute_with_approval_handling()
    await execute_with_automatic_retry()
    await batch_operations()

    print("\n✅ All async examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
