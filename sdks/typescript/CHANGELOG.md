# Changelog

All notable changes to the UAPK Gateway TypeScript SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-28

### Added

- Initial release of UAPK Gateway TypeScript SDK
- Core client (`UAPKGatewayClient`)
- Full TypeScript type definitions
- Zod schema validation for runtime type safety
- Exception hierarchy for error handling
- Retry logic with exponential backoff
- Support for:
  - Action evaluation (dry-run)
  - Action execution
  - Approval workflows
  - Capability tokens
  - Counterparty information
  - Custom context
  - Override tokens
- Dual package support (ESM + CommonJS)
- Comprehensive documentation
- Example implementations

### Features

#### Core Client

- HTTP/HTTPS support with Axios
- Automatic retry on network errors and 5xx responses
- Rate limit handling with retry-after support
- Authentication via API key
- Configurable timeouts and retry behavior
- Full TypeScript type safety

#### Approval Workflows

- Manual approval polling via `getApprovalStatus()`
- Automatic approval waiting with `executeWithRetryOnEscalate()`
- Configurable poll intervals and max wait times
- Override token support for approved actions

#### Type Safety

- Full TypeScript definitions for all interfaces
- Runtime validation with Zod schemas
- IntelliSense support in modern IDEs
- Comprehensive JSDoc documentation

#### Error Handling

- `ActionDeniedError` - Action blocked by policy
- `ActionEscalatedError` - Approval required
- `ToolExecutionError` - Tool execution failed
- `AuthenticationError` - Invalid API key
- `NetworkError` - Network/HTTP errors
- `ValidationError` - Request validation failed
- `RateLimitError` - Rate limit exceeded

## [Unreleased]

### Planned

- LangChain integration wrapper
- OpenAI tools integration
- React hooks for browser usage
- WebSocket support for real-time updates
- Streaming support for long-running actions
- Circuit breaker pattern
