# UAPK Gateway TypeScript SDK

Official TypeScript/JavaScript SDK for [UAPK Gateway](https://github.com/anthropics/uapk-gateway) - the compliance and audit control plane for AI agents.

## Features

- ✅ **Full TypeScript Support** - Complete type definitions with Zod validation
- 🔒 **Policy Enforcement** - Route all agent actions through compliance policies
- 📊 **Audit Logging** - Automatic tamper-evident audit trail for all actions
- 👤 **Approval Workflows** - Built-in human-in-the-loop for high-risk actions
- ⚡ **Retry Logic** - Automatic retries with exponential backoff
- 🛡️ **Type Safety** - Runtime validation with Zod schemas
- 📦 **Dual Packages** - Supports both ESM and CommonJS

## Installation

```bash
npm install @uapk/gateway-sdk
# or
yarn add @uapk/gateway-sdk
# or
pnpm add @uapk/gateway-sdk
```

## Quick Start

### Basic Usage

```typescript
import { UAPKGatewayClient } from '@uapk/gateway-sdk';

const client = new UAPKGatewayClient({
  baseURL: 'https://gateway.yourcompany.com',
  apiKey: 'your-api-key'
});

// Execute an action
const response = await client.execute({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-123',
  action: {
    type: 'refund',
    tool: 'stripe_api',
    params: { charge_id: 'ch_123', amount: 1000 }
  }
});

console.log(response.decision); // ALLOW, DENY, or ESCALATE
```

### With TypeScript

```typescript
import {
  UAPKGatewayClient,
  ActionInfo,
  GatewayExecuteResponse,
  ActionDeniedError,
  ActionEscalatedError
} from '@uapk/gateway-sdk';

const client = new UAPKGatewayClient({
  baseURL: process.env.GATEWAY_URL!,
  apiKey: process.env.GATEWAY_API_KEY!,
  timeout: 30000,
  maxRetries: 3
});

const action: ActionInfo = {
  type: 'send_email',
  tool: 'smtp_connector',
  params: {
    to: 'user@example.com',
    subject: 'Hello',
    body: 'Test message'
  }
};

try {
  const response: GatewayExecuteResponse = await client.execute({
    uapkId: 'email-agent-v1',
    agentId: 'agent-001',
    action
  });

  if (response.executed && response.result) {
    console.log('Result:', response.result.data);
  }
} catch (error) {
  if (error instanceof ActionDeniedError) {
    console.error('Action denied:', error.reasons);
  } else if (error instanceof ActionEscalatedError) {
    console.error('Approval required:', error.approvalId);
  }
}
```

## Core Concepts

### Actions

Actions represent operations your agent wants to perform:

```typescript
import { ActionInfo } from '@uapk/gateway-sdk';

const action: ActionInfo = {
  type: 'refund',           // Action type for policy matching
  tool: 'stripe_api',       // Tool/connector to execute
  params: {                 // Tool-specific parameters
    charge_id: 'ch_123',
    reason: 'Customer request'
  },
  amount: 100.00,          // Optional: transaction amount
  currency: 'USD',         // Optional: currency code
  description: 'Process customer refund'  // Optional: human-readable
};
```

### Decisions

The gateway returns one of three decisions:

- **ALLOW** - Action is permitted and may be executed
- **DENY** - Action is blocked by policy
- **ESCALATE** - Action requires human approval

### Counterparties

For actions involving external parties:

```typescript
import { CounterpartyInfo } from '@uapk/gateway-sdk';

const counterparty: CounterpartyInfo = {
  email: 'customer@example.com',
  domain: 'example.com',
  jurisdiction: 'US'
};

const response = await client.execute({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-123',
  action,
  counterparty  // Used for policy evaluation
});
```

## Usage Guide

### 1. Evaluation (Dry-Run)

Evaluate an action without executing it:

```typescript
const decision = await client.evaluate({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-123',
  action: {
    type: 'refund',
    tool: 'stripe_api',
    params: { charge_id: 'ch_123' }
  }
});

if (decision.decision === 'ALLOW') {
  console.log('Action would be allowed');
  // Proceed with execution
} else if (decision.decision === 'DENY') {
  console.log('Action would be denied:', decision.reasons);
} else if (decision.decision === 'ESCALATE') {
  console.log('Action would require approval:', decision.approval_id);
}
```

### 2. Execution

Execute an action through the gateway:

```typescript
import { ActionDeniedError, ActionEscalatedError } from '@uapk/gateway-sdk';

try {
  const response = await client.execute({
    uapkId: 'refund-bot-v1',
    agentId: 'agent-123',
    action,
    raiseOnDeny: true,      // Throw exception if denied (default: true)
    raiseOnEscalate: false  // Throw exception if escalated (default: false)
  });

  if (response.executed && response.result) {
    console.log('Result:', response.result.data);
  }
} catch (error) {
  if (error instanceof ActionDeniedError) {
    console.error('Denied:', error.reasons.map(r => r.message));
  } else if (error instanceof ActionEscalatedError) {
    console.error('Approval needed:', error.approvalId);
  }
}
```

### 3. Approval Workflows

#### Manual Polling

```typescript
let approvalId: string;

try {
  await client.execute({
    uapkId: 'refund-bot-v1',
    agentId: 'agent-123',
    action,
    raiseOnEscalate: true
  });
} catch (error) {
  if (error instanceof ActionEscalatedError) {
    approvalId = error.approvalId!;
  }
}

// Poll for approval status
const checkApproval = async () => {
  const approval = await client.getApprovalStatus(approvalId);

  if (approval.status === 'APPROVED') {
    // Retry with override token
    const response = await client.execute({
      uapkId: 'refund-bot-v1',
      agentId: 'agent-123',
      action,
      overrideToken: approval.override_token
    });
    console.log('Action completed after approval!');
  } else if (approval.status === 'DENIED') {
    console.log('Approval was denied');
  } else {
    // Still pending, check again later
    setTimeout(checkApproval, 5000);
  }
};

checkApproval();
```

#### Automatic Retry

```typescript
// Automatically wait for approval and retry
const response = await client.executeWithRetryOnEscalate({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-123',
  action,
  pollInterval: 5000,  // Check every 5 seconds
  maxWait: 300000      // Wait max 5 minutes
});
```

### 4. Context Information

Provide additional context for policy evaluation:

```typescript
const response = await client.execute({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-123',
  action,
  context: {
    user_tier: 'premium',
    session_id: 'sess_789',
    source: 'mobile_app',
    custom_field: 'value'
  }
});
```

### 5. Capability Tokens (Delegation)

Use capability tokens for delegated actions:

```typescript
// Agent B uses capability token from Agent A
const response = await client.execute({
  uapkId: 'refund-bot-v1',
  agentId: 'agent-b-456',
  action,
  capabilityToken: 'cap_token_xyz'  // Delegation proof
});
```

## Error Handling

### Exception Hierarchy

```typescript
import {
  UAPKGatewayError,        // Base exception
  AuthenticationError,     // Invalid API key
  ActionDeniedError,       // Action denied by policy
  ActionEscalatedError,    // Approval required
  ToolExecutionError,      // Tool execution failed
  NetworkError,            // Network/HTTP errors
  ValidationError,         // Request validation failed
  RateLimitError          // Rate limit exceeded
} from '@uapk/gateway-sdk';
```

### Exception Details

```typescript
try {
  await client.execute({...});
} catch (error) {
  if (error instanceof ActionDeniedError) {
    console.log(error.decisionResponse);  // Full gateway response
    console.log(error.reasons);           // List of reason details
    console.log(error.interactionId);     // Audit trail ID
  } else if (error instanceof ActionEscalatedError) {
    console.log(error.approvalId);        // Approval ID for polling
    console.log(error.interactionId);     // Audit trail ID
    console.log(error.reasons);           // Why approval is required
  } else if (error instanceof RateLimitError) {
    console.log(`Retry after ${error.retryAfter} seconds`);
  }
}
```

## API Reference

### UAPKGatewayClient

#### Constructor

```typescript
new UAPKGatewayClient(config: ClientConfig)
```

**ClientConfig:**
- `baseURL` (string): Gateway base URL
- `apiKey` (string): API key for authentication
- `timeout?` (number): Request timeout in ms (default: 30000)
- `maxRetries?` (number): Max retry attempts (default: 3)
- `retryDelay?` (number): Base retry delay in ms (default: 1000)

#### Methods

**evaluate(options: EvaluateOptions): Promise<GatewayDecisionResponse>**

Evaluate an action without executing (dry-run).

**execute(options: ExecuteOptions): Promise<GatewayExecuteResponse>**

Execute an action through the gateway.

**executeWithRetryOnEscalate(options: ExecuteWithRetryOptions): Promise<GatewayExecuteResponse>**

Execute and automatically wait for approval if escalated.

**getApprovalStatus(approvalId: string): Promise<ApprovalStatusResponse>**

Get approval status by ID.

## TypeScript Support

The SDK is written in TypeScript and includes complete type definitions:

```typescript
import type {
  ActionInfo,
  CounterpartyInfo,
  GatewayDecision,
  GatewayDecisionResponse,
  GatewayExecuteResponse,
  ReasonCode,
  ReasonDetail,
  ToolResult,
  ClientConfig,
  ExecuteOptions,
  EvaluateOptions
} from '@uapk/gateway-sdk';
```

All types are validated at runtime using Zod schemas.

## Examples

See the [examples](./examples) directory for complete working examples:

- `basic-usage.ts` - Basic SDK usage
- `error-handling.ts` - Comprehensive error handling
- `approval-workflow.ts` - Approval workflow patterns
- `langchain-integration.ts` - LangChain integration (coming soon)

## Development

### Building

```bash
npm run build
```

### Testing

```bash
npm test
npm run test:coverage
```

### Linting

```bash
npm run lint
npm run lint:fix
```

### Type Checking

```bash
npm run type-check
```

## Configuration

### Environment Variables

```bash
# Gateway connection
GATEWAY_URL=https://gateway.yourcompany.com
GATEWAY_API_KEY=your-api-key

# UAPK manifest and agent identity
UAPK_ID=your-manifest-id
AGENT_ID=your-agent-id
```

## Browser Support

The SDK works in both Node.js and modern browsers. For browser usage:

```html
<script type="module">
  import { UAPKGatewayClient } from '@uapk/gateway-sdk';

  const client = new UAPKGatewayClient({
    baseURL: 'https://gateway.yourcompany.com',
    apiKey: 'your-api-key'
  });

  // Use the client...
</script>
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

## Support

- **Documentation**: https://docs.uapk.dev
- **Issues**: https://github.com/anthropics/uapk-gateway/issues
- **Discussions**: https://github.com/anthropics/uapk-gateway/discussions

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.
