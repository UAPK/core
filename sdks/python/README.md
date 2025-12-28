# UAPK Gateway Python SDK

Official Python SDK for [UAPK Gateway](https://github.com/anthropics/uapk-gateway) - the compliance and audit control plane for AI agents.

## Features

- ✅ **Sync & Async Support** - Both synchronous and async clients with identical APIs
- 🔒 **Policy Enforcement** - Route all agent actions through compliance policies
- 📊 **Audit Logging** - Automatic tamper-evident audit trail for all actions
- 👤 **Approval Workflows** - Built-in human-in-the-loop for high-risk actions
- 🎯 **Framework Integration** - Native support for LangChain, OpenAI, and more
- 🛡️ **Type Safety** - Full Pydantic validation on all requests/responses
- ⚡ **Retry Logic** - Automatic retries with exponential backoff

## Installation

```bash
pip install uapk-gateway
```

### Optional Dependencies

```bash
# For LangChain integration
pip install uapk-gateway[langchain]

# For all integrations
pip install uapk-gateway[all]
```

## Quick Start

### Synchronous Client

```python
from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo

# Initialize client
client = UAPKGatewayClient(
    base_url="https://gateway.yourcompany.com",
    api_key="your-api-key"
)

# Execute an action
response = client.execute(
    uapk_id="refund-bot-v1",
    agent_id="agent-123",
    action=ActionInfo(
        type="refund",
        tool="stripe_api",
        params={"charge_id": "ch_123", "amount": 1000}
    )
)

print(f"Decision: {response.decision}")  # ALLOW, DENY, or ESCALATE
print(f"Executed: {response.executed}")

client.close()
```

### Asynchronous Client

```python
import asyncio
from uapk_gateway import AsyncUAPKGatewayClient
from uapk_gateway.models import ActionInfo

async def main():
    async with AsyncUAPKGatewayClient(
        base_url="https://gateway.yourcompany.com",
        api_key="your-api-key"
    ) as client:
        response = await client.execute(
            uapk_id="refund-bot-v1",
            agent_id="agent-123",
            action=ActionInfo(
                type="refund",
                tool="stripe_api",
                params={"charge_id": "ch_123", "amount": 1000}
            )
        )
        print(f"Decision: {response.decision}")

asyncio.run(main())
```

## Core Concepts

### Actions

Actions represent operations your agent wants to perform. Each action includes:

```python
from uapk_gateway.models import ActionInfo

action = ActionInfo(
    type="send_email",           # Action type for policy matching
    tool="smtp_connector",       # Tool/connector to execute
    params={                     # Tool-specific parameters
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Message text"
    },
    amount=None,                 # Optional: transaction amount
    currency=None,               # Optional: currency code
    description="Send welcome email"  # Optional: human-readable description
)
```

### Decisions

The gateway returns one of three decisions:

- **ALLOW** - Action is permitted and may be executed
- **DENY** - Action is blocked by policy
- **ESCALATE** - Action requires human approval

### Counterparties

For actions involving external parties, provide counterparty information:

```python
from uapk_gateway.models import CounterpartyInfo

counterparty = CounterpartyInfo(
    email="customer@example.com",
    domain="example.com",
    jurisdiction="US"
)

response = client.execute(
    uapk_id="refund-bot-v1",
    agent_id="agent-123",
    action=action,
    counterparty=counterparty  # Used for policy evaluation
)
```

## Usage Guide

### 1. Evaluation (Dry-Run)

Evaluate an action without executing it:

```python
response = client.evaluate(
    uapk_id="refund-bot-v1",
    agent_id="agent-123",
    action=action
)

if response.decision == "ALLOW":
    print("Action would be allowed")
    # Proceed with execution
elif response.decision == "DENY":
    print(f"Action would be denied: {response.reasons[0].message}")
elif response.decision == "ESCALATE":
    print(f"Action would require approval: {response.approval_id}")
```

### 2. Execution

Execute an action through the gateway:

```python
from uapk_gateway.exceptions import ActionDeniedError, ActionEscalatedError

try:
    response = client.execute(
        uapk_id="refund-bot-v1",
        agent_id="agent-123",
        action=action,
        raise_on_deny=True,      # Raise exception if denied (default: True)
        raise_on_escalate=False  # Raise exception if escalated (default: False)
    )

    if response.executed and response.result:
        print(f"Result: {response.result.data}")

except ActionDeniedError as e:
    print(f"Action denied: {e}")
    print(f"Reasons: {[r.message for r in e.reasons]}")

except ActionEscalatedError as e:
    print(f"Approval required: {e.approval_id}")
```

### 3. Approval Workflows

#### Manual Polling

```python
try:
    response = client.execute(
        uapk_id="refund-bot-v1",
        agent_id="agent-123",
        action=action,
        raise_on_escalate=True
    )
except ActionEscalatedError as e:
    approval_id = e.approval_id

    # Poll for approval status
    while True:
        approval = client.get_approval_status(approval_id)

        if approval["status"] == "APPROVED":
            # Retry with override token
            response = client.execute(
                uapk_id="refund-bot-v1",
                agent_id="agent-123",
                action=action,
                override_token=approval["override_token"]
            )
            break

        elif approval["status"] == "DENIED":
            print("Approval was denied")
            break

        time.sleep(5)  # Wait before checking again
```

#### Automatic Retry

```python
# Automatically wait for approval and retry
response = client.execute_with_retry_on_escalate(
    uapk_id="refund-bot-v1",
    agent_id="agent-123",
    action=action,
    poll_interval=5,  # Check every 5 seconds
    max_wait=300      # Wait max 5 minutes
)
```

### 4. Capability Tokens (Delegation)

Use capability tokens for delegated actions:

```python
# Agent A issues a capability token (via gateway API)
# Agent B uses it to perform delegated action

response = client.execute(
    uapk_id="refund-bot-v1",
    agent_id="agent-b-456",
    action=action,
    capability_token="cap_token_xyz"  # Delegation proof
)
```

### 5. Context Information

Provide additional context for policy evaluation:

```python
response = client.execute(
    uapk_id="refund-bot-v1",
    agent_id="agent-123",
    action=action,
    context={
        "user_tier": "premium",
        "session_id": "sess_789",
        "source": "mobile_app",
        "custom_field": "value"
    }
)
```

## Error Handling

### Exception Hierarchy

```python
UAPKGatewayError                  # Base exception
├── AuthenticationError           # Invalid API key
├── ActionDeniedError             # Action denied by policy
├── ActionEscalatedError          # Approval required
├── ToolExecutionError            # Tool execution failed
├── NetworkError                  # Network/HTTP errors
├── ValidationError               # Request validation failed
└── RateLimitError                # Rate limit exceeded
```

### Exception Details

```python
from uapk_gateway.exceptions import (
    ActionDeniedError,
    ActionEscalatedError,
    RateLimitError
)

try:
    response = client.execute(...)

except ActionDeniedError as e:
    # Access denial details
    print(e.decision_response)  # Full gateway response
    print(e.reasons)            # List of reason dicts
    print(e.interaction_id)     # Audit trail ID

except ActionEscalatedError as e:
    # Access escalation details
    print(e.approval_id)        # Approval ID for polling
    print(e.interaction_id)     # Audit trail ID
    print(e.reasons)            # Why approval is required

except RateLimitError as e:
    # Retry after specified time
    print(f"Retry after {e.retry_after} seconds")
```

## Framework Integrations

### LangChain

Wrap LangChain tools to route through gateway:

```python
from langchain.tools import DuckDuckGoSearchRun
from uapk_gateway.integrations.langchain import UAPKGatewayTool

# Create original tool
search_tool = DuckDuckGoSearchRun()

# Wrap with gateway
gateway_search = UAPKGatewayTool(
    tool=search_tool,
    gateway_client=client,
    uapk_id="search-agent-v1",
    agent_id="agent-123",
    action_type="web_search",
    handle_approval_required="raise"  # or "deny" or "wait"
)

# Use in LangChain agent (calls now go through gateway)
result = gateway_search.run("latest AI news")
```

Wrap multiple tools at once:

```python
from uapk_gateway.integrations.langchain import wrap_langchain_tools

wrapped_tools = wrap_langchain_tools(
    tools=[tool1, tool2, tool3],
    gateway_client=client,
    uapk_id="my-agent-v1",
    agent_id="agent-123",
    action_type_map={
        "Tool1": "action_type_1",
        "Tool2": "action_type_2"
    }
)
```

See [examples/langchain_integration.py](examples/langchain_integration.py) for full examples.

### OpenAI Function Calling

Route OpenAI function calls through gateway:

```python
from openai import OpenAI
from uapk_gateway.models import ActionInfo

openai_client = OpenAI(api_key="...")
gateway_client = UAPKGatewayClient(...)

# OpenAI suggests a function call
response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    functions=[...]
)

if response.choices[0].message.function_call:
    func_name = response.choices[0].message.function_call.name
    func_args = json.loads(response.choices[0].message.function_call.arguments)

    # Route through gateway before executing
    gateway_response = gateway_client.execute(
        uapk_id="my-agent-v1",
        agent_id="agent-123",
        action=ActionInfo(
            type=func_name,
            tool=func_name,
            params=func_args
        )
    )

    if gateway_response.decision == "ALLOW":
        # Execute the function
        result = my_functions[func_name](**func_args)
```

See [examples/openai_function_calling.py](examples/openai_function_calling.py) for complete implementation.

## Advanced Usage

### Concurrent Operations (Async)

```python
import asyncio

async def process_batch():
    async with AsyncUAPKGatewayClient(...) as client:
        # Evaluate multiple actions concurrently
        tasks = [
            client.execute(
                uapk_id="bot-v1",
                agent_id=f"agent-{i}",
                action=actions[i]
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Action {i} failed: {result}")
            else:
                print(f"Action {i}: {result.decision}")
```

### Custom Retry Logic

```python
from uapk_gateway import UAPKGatewayClient

client = UAPKGatewayClient(
    base_url="...",
    api_key="...",
    timeout=30,           # Request timeout (seconds)
    max_retries=3,        # Max retry attempts
    retry_backoff=1.0     # Backoff multiplier
)
```

### Context Manager (Sync)

```python
with UAPKGatewayClient(base_url="...", api_key="...") as client:
    response = client.execute(...)
    # Client automatically closed on exit
```

### Context Manager (Async)

```python
async with AsyncUAPKGatewayClient(base_url="...", api_key="...") as client:
    response = await client.execute(...)
    # Client automatically closed on exit
```

## API Reference

### UAPKGatewayClient

#### `__init__(base_url, api_key, timeout=30, max_retries=3, retry_backoff=1.0)`

Initialize synchronous gateway client.

**Parameters:**
- `base_url` (str): Gateway base URL (e.g., "https://gateway.example.com")
- `api_key` (str): API key for authentication
- `timeout` (int): Request timeout in seconds (default: 30)
- `max_retries` (int): Max retry attempts for network errors (default: 3)
- `retry_backoff` (float): Backoff multiplier for retries (default: 1.0)

#### `evaluate(uapk_id, agent_id, action, counterparty=None, context=None, capability_token=None)`

Evaluate an action without executing (dry-run).

**Returns:** `GatewayDecisionResponse`

#### `execute(uapk_id, agent_id, action, counterparty=None, context=None, capability_token=None, override_token=None, raise_on_deny=True, raise_on_escalate=False, raise_on_tool_error=True)`

Execute an action through the gateway.

**Returns:** `GatewayExecuteResponse`

**Raises:** `ActionDeniedError`, `ActionEscalatedError`, `ToolExecutionError`

#### `execute_with_retry_on_escalate(uapk_id, agent_id, action, counterparty=None, context=None, capability_token=None, poll_interval=5, max_wait=300)`

Execute and automatically wait for approval if escalated.

**Returns:** `GatewayExecuteResponse`

**Raises:** `TimeoutError`, `ActionDeniedError`

#### `get_approval_status(approval_id)`

Get approval status by ID.

**Returns:** `dict` with approval details

### AsyncUAPKGatewayClient

Same API as `UAPKGatewayClient`, but all methods are async (use `await`).

### Models

#### ActionInfo

- `type` (str): Action type
- `tool` (str): Tool/connector name
- `params` (dict): Tool parameters
- `amount` (float, optional): Transaction amount
- `currency` (str, optional): Currency code
- `description` (str, optional): Human-readable description

#### CounterpartyInfo

- `id` (str, optional): Counterparty ID
- `name` (str, optional): Counterparty name
- `email` (str, optional): Email address
- `domain` (str, optional): Domain name
- `jurisdiction` (str, optional): Country/jurisdiction code

#### GatewayDecisionResponse

- `interaction_id` (str): Audit trail ID
- `decision` (GatewayDecision): ALLOW, DENY, or ESCALATE
- `reasons` (list[ReasonDetail]): Decision reasons
- `approval_id` (str, optional): Approval ID (if escalated)
- `timestamp` (datetime): Decision timestamp
- `policy_version` (str): Policy version used

#### GatewayExecuteResponse

Extends `GatewayDecisionResponse` with:

- `executed` (bool): Whether tool was executed
- `result` (ToolResult, optional): Tool execution result

#### ToolResult

- `success` (bool): Execution success
- `data` (dict, optional): Result data
- `error` (dict, optional): Error details
- `result_hash` (str, optional): Result hash for audit
- `duration_ms` (int, optional): Execution duration

## Examples

See the [examples/](examples/) directory:

- [`quickstart.py`](examples/quickstart.py) - Basic usage patterns
- [`async_usage.py`](examples/async_usage.py) - Async client examples
- [`langchain_integration.py`](examples/langchain_integration.py) - LangChain integration
- [`openai_function_calling.py`](examples/openai_function_calling.py) - OpenAI integration

## Configuration

### Environment Variables

```bash
# Gateway connection
export GATEWAY_URL=https://gateway.yourcompany.com
export GATEWAY_API_KEY=your-api-key

# UAPK manifest and agent identity
export UAPK_ID=your-manifest-id
export AGENT_ID=your-agent-id

# For OpenAI examples
export OPENAI_API_KEY=your-openai-key
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=uapk_gateway tests/
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
cd docs && make html
```

## Support

- **Documentation**: https://docs.uapk.dev
- **Issues**: https://github.com/anthropics/uapk-gateway/issues
- **Discussions**: https://github.com/anthropics/uapk-gateway/discussions

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
