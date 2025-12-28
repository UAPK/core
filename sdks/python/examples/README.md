# UAPK Gateway SDK Examples

This directory contains example code demonstrating various usage patterns for the UAPK Gateway Python SDK.

## Examples Overview

### 1. [quickstart.py](quickstart.py)
**Basic SDK usage patterns**

Learn the fundamentals:
- Initialize sync client
- Evaluate actions (dry-run)
- Execute actions
- Handle errors
- Work with counterparty info
- Check approval status
- Automatic approval waiting

Perfect for first-time users.

```bash
export GATEWAY_URL=http://localhost:8000
export GATEWAY_API_KEY=your-api-key
python examples/quickstart.py
```

---

### 2. [async_usage.py](async_usage.py)
**Asynchronous client examples**

Advanced async patterns:
- Concurrent action evaluation
- Approval workflow handling
- Automatic retry on escalation
- Batch operations with concurrency control

Great for high-performance applications.

```bash
export GATEWAY_URL=http://localhost:8000
export GATEWAY_API_KEY=your-api-key
python examples/async_usage.py
```

---

### 3. [langchain_integration.py](langchain_integration.py)
**LangChain framework integration**

Integrate with LangChain agents:
- Wrap single tools
- Batch wrap multiple tools
- Full agent with wrapped tools
- Custom counterparty extraction
- Approval handling modes

Requires: `pip install langchain langchain-openai`

```bash
export GATEWAY_URL=http://localhost:8000
export GATEWAY_API_KEY=your-api-key
export OPENAI_API_KEY=your-openai-key  # Optional for full agent
python examples/langchain_integration.py
```

---

### 4. [openai_function_calling.py](openai_function_calling.py)
**OpenAI function calling integration**

Route OpenAI function calls through gateway:
- Intercept function calls
- Policy evaluation before execution
- Approval workflows
- Multiple scenarios (low-risk, high-risk, read-only)

Requires: `pip install openai`

```bash
export GATEWAY_URL=http://localhost:8000
export GATEWAY_API_KEY=your-api-key
export OPENAI_API_KEY=your-openai-key
python examples/openai_function_calling.py
```

---

## Running Examples Locally

### Prerequisites

1. **Start UAPK Gateway**:
```bash
cd ../../backend
docker-compose up -d
```

2. **Install SDK**:
```bash
cd ../sdks/python
pip install -e .
```

3. **Set environment variables**:
```bash
export GATEWAY_URL=http://localhost:8000
export GATEWAY_API_KEY=test-api-key
export UAPK_ID=my-agent-v1
export AGENT_ID=agent-001
```

### Run an Example

```bash
python examples/quickstart.py
```

---

## Example Use Cases

### E-commerce Bot
```python
# Customer service agent that needs approval for refunds > $100
from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo

client = UAPKGatewayClient(base_url="...", api_key="...")

# Small refund - likely auto-approved
response = client.execute(
    uapk_id="customer-service-v1",
    agent_id="bot-001",
    action=ActionInfo(
        type="refund",
        tool="stripe_api",
        params={"charge_id": "ch_123"},
        amount=25.00,
        currency="USD"
    )
)

# Large refund - likely escalated for approval
response = client.execute_with_retry_on_escalate(
    uapk_id="customer-service-v1",
    agent_id="bot-001",
    action=ActionInfo(
        type="refund",
        tool="stripe_api",
        params={"charge_id": "ch_456"},
        amount=500.00,
        currency="USD"
    ),
    max_wait=300  # Wait up to 5 minutes for approval
)
```

### Financial Trading Bot
```python
# Trading agent with strict jurisdiction controls
from uapk_gateway.models import CounterpartyInfo

response = client.execute(
    uapk_id="trading-bot-v1",
    agent_id="trader-001",
    action=ActionInfo(
        type="trade",
        tool="trading_api",
        params={"symbol": "AAPL", "quantity": 100, "side": "buy"},
        amount=15000.00,
        currency="USD"
    ),
    counterparty=CounterpartyInfo(
        id="broker_123",
        jurisdiction="US",  # Policy may block sanctioned jurisdictions
    )
)
```

### Healthcare Assistant
```python
# Medical records agent with audit trail
response = client.execute(
    uapk_id="medical-assistant-v1",
    agent_id="assistant-001",
    action=ActionInfo(
        type="access_medical_record",
        tool="ehr_system",
        params={"patient_id": "P123456", "record_type": "lab_results"}
    ),
    context={
        "physician_id": "DR_789",
        "purpose": "treatment",
        "department": "cardiology"
    }
)

# All accesses are logged with tamper-evident audit trail
print(f"Audit ID: {response.interaction_id}")
```

---

## Common Patterns

### Pattern 1: Try Execute, Fall Back on Deny

```python
try:
    response = client.execute(action, raise_on_deny=True)
    # Proceed with action result
except ActionDeniedError:
    # Fall back to alternative approach
    alternative_action()
```

### Pattern 2: Notify User on Escalation

```python
try:
    response = client.execute(action, raise_on_escalate=True)
except ActionEscalatedError as e:
    notify_user(f"Approval required: {e.approval_id}")
    # Store approval_id for later retry
```

### Pattern 3: Batch with Individual Error Handling

```python
async def process_batch(actions):
    async with AsyncUAPKGatewayClient(...) as client:
        tasks = [
            client.execute(
                action=action,
                raise_on_deny=False,  # Don't raise, check decision
                raise_on_escalate=False
            )
            for action in actions
        ]

        results = await asyncio.gather(*tasks)

        for action, result in zip(actions, results):
            if result.decision == "ALLOW":
                process_success(action, result)
            elif result.decision == "DENY":
                log_denial(action, result)
            elif result.decision == "ESCALATE":
                queue_for_approval(action, result)
```

### Pattern 4: Pre-flight Check

```python
# Check if action would be allowed before attempting
decision = client.evaluate(action)

if decision.decision == "ALLOW":
    # Proceed with actual execution
    response = client.execute(action)
else:
    # Don't attempt - already know it would fail/escalate
    handle_non_allow(decision)
```

---

## Troubleshooting

### Connection Errors

```python
from uapk_gateway.exceptions import NetworkError

try:
    response = client.execute(...)
except NetworkError as e:
    print(f"Gateway unreachable: {e}")
    # Check GATEWAY_URL is correct
    # Verify gateway is running
```

### Authentication Errors

```python
from uapk_gateway.exceptions import AuthenticationError

try:
    response = client.execute(...)
except AuthenticationError:
    # Check GATEWAY_API_KEY is valid
    # Verify key has not expired
```

### Rate Limiting

```python
from uapk_gateway.exceptions import RateLimitError
import time

try:
    response = client.execute(...)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
    time.sleep(e.retry_after)
    response = client.execute(...)  # Retry
```

---

## Additional Resources

- **SDK Documentation**: [../README.md](../README.md)
- **Gateway Documentation**: [../../../README.md](../../../README.md)
- **API Reference**: [../../../docs/api.md](../../../docs/api.md)
- **Policy Guide**: [../../../docs/policy.md](../../../docs/policy.md)

---

## Contributing Examples

Have a great example to share? PRs welcome!

Guidelines:
1. Focus on a specific use case or pattern
2. Include clear comments and docstrings
3. Use mock implementations (don't require external services)
4. Add entry to this README
5. Test with `python examples/your_example.py`
