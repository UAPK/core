# Changelog

All notable changes to the UAPK Gateway Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-28

### Added

- Initial release of UAPK Gateway Python SDK
- Synchronous client (`UAPKGatewayClient`)
- Asynchronous client (`AsyncUAPKGatewayClient`)
- Full Pydantic model validation
- Exception hierarchy for error handling
- Retry logic with exponential backoff
- Context manager support (sync and async)
- LangChain integration (`UAPKGatewayTool`)
- OpenAI function calling integration examples
- Comprehensive documentation and examples
- Support for:
  - Action evaluation (dry-run)
  - Action execution
  - Approval workflows
  - Capability tokens
  - Counterparty information
  - Custom context
  - Override tokens

### Features

#### Core Client

- HTTP/HTTPS support with automatic retry on network errors
- Rate limit handling with `Retry-After` header support
- Authentication via API key
- Configurable timeouts and retry behavior
- Automatic JSON serialization/deserialization
- Full type safety with Pydantic v2

#### Approval Workflows

- Manual approval polling via `get_approval_status()`
- Automatic approval waiting with `execute_with_retry_on_escalate()`
- Configurable poll intervals and max wait times
- Override token support for approved actions

#### Integrations

- LangChain tool wrapper with sync/async support
- Batch tool wrapping utility
- Custom counterparty extraction hooks
- Flexible approval handling modes (raise, deny, wait)
- OpenAI function calling examples

#### Error Handling

- `ActionDeniedError` - Action blocked by policy
- `ActionEscalatedError` - Approval required
- `ToolExecutionError` - Tool execution failed
- `AuthenticationError` - Invalid API key
- `NetworkError` - Network/HTTP errors
- `ValidationError` - Request validation failed
- `RateLimitError` - Rate limit exceeded

### Examples

- `examples/quickstart.py` - Basic usage patterns
- `examples/async_usage.py` - Async client examples
- `examples/langchain_integration.py` - LangChain integration
- `examples/openai_function_calling.py` - OpenAI function calling

### Documentation

- Comprehensive README with:
  - Installation instructions
  - Quick start guide
  - Core concepts
  - Usage patterns
  - Error handling
  - Framework integrations
  - API reference
- Inline docstrings for all public APIs
- Example code for common scenarios

## [Unreleased]

### Planned

- CrewAI integration
- AutoGen integration
- Streaming support for long-running actions
- Webhook callback support
- Metrics and telemetry
- Circuit breaker pattern for fault tolerance
