# UAPK Gateway SDK Tests

Comprehensive test suite for the UAPK Gateway Python SDK.

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and mocks
├── test_client.py                 # Sync client tests
├── test_async_client.py           # Async client tests
├── test_models.py                 # Pydantic model tests
├── test_exceptions.py             # Exception handling tests
└── test_langchain_integration.py  # LangChain integration tests
```

## Running Tests

### Install Dependencies

```bash
# Install SDK with dev dependencies
pip install -e ".[dev]"

# Or install LangChain integration tests
pip install -e ".[dev,langchain]"
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test sync client only
pytest tests/test_client.py

# Test async client only
pytest tests/test_async_client.py

# Test models
pytest tests/test_models.py
```

### Run Specific Test Classes

```bash
# Test client initialization
pytest tests/test_client.py::TestClientInitialization

# Test async error handling
pytest tests/test_async_client.py::TestAsyncErrorHandling
```

### Run Specific Tests

```bash
# Test specific function
pytest tests/test_client.py::TestExecute::test_execute_success
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=uapk_gateway --cov-report=html

# View coverage
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Fast Tests Only (Skip Slow Tests)

```bash
pytest -m "not slow"
```

## Test Coverage

### Sync Client (`test_client.py`)
- ✅ Client initialization
- ✅ Context manager support
- ✅ Action evaluation
- ✅ Action execution
- ✅ DENY/ESCALATE/ALLOW handling
- ✅ Tool execution errors
- ✅ Approval workflows
- ✅ Approval polling
- ✅ Error handling (auth, network, timeout, rate limit)
- ✅ Retry logic
- ✅ Counterparty and context parameters

**Total: 25+ test cases**

### Async Client (`test_async_client.py`)
- ✅ Async client initialization
- ✅ Async context manager
- ✅ Concurrent evaluations
- ✅ Async execution
- ✅ Async error handling
- ✅ Async approval workflows
- ✅ Batch operations
- ✅ Mixed results handling

**Total: 20+ test cases**

### Models (`test_models.py`)
- ✅ ActionInfo validation
- ✅ CounterpartyInfo validation
- ✅ ReasonDetail validation
- ✅ GatewayActionRequest validation
- ✅ GatewayDecisionResponse validation
- ✅ GatewayExecuteResponse validation
- ✅ ToolResult validation
- ✅ Enum values
- ✅ Serialization/deserialization
- ✅ Model round-trip

**Total: 30+ test cases**

### Exceptions (`test_exceptions.py`)
- ✅ Exception hierarchy
- ✅ ActionDeniedError
- ✅ ActionEscalatedError
- ✅ ToolExecutionError
- ✅ RateLimitError
- ✅ NetworkError
- ✅ AuthenticationError
- ✅ ValidationError
- ✅ Exception attributes
- ✅ Exception chaining

**Total: 25+ test cases**

### LangChain Integration (`test_langchain_integration.py`)
- ✅ Tool wrapping
- ✅ Sync tool execution
- ✅ Async tool execution
- ✅ DENY/ESCALATE handling modes
- ✅ Custom counterparty extraction
- ✅ Custom context extraction
- ✅ Batch tool wrapping
- ✅ Action type mapping
- ✅ Gateway vs local execution

**Total: 25+ test cases**

## Coverage Goals

- **Line Coverage**: >90%
- **Branch Coverage**: >85%
- **Critical Paths**: 100%

Current coverage (after running tests):

```bash
pytest --cov=uapk_gateway --cov-report=term-missing
```

## Mock Strategy

All tests use mocked HTTP clients and gateway responses to ensure:
- ✅ Fast test execution (no network calls)
- ✅ Reliable tests (no external dependencies)
- ✅ Reproducible results
- ✅ Comprehensive error scenario coverage

### Mock Gateway Server

The `MockGatewayServer` in `conftest.py` provides:
- Configurable responses per endpoint
- Request history tracking
- Default responses for all endpoints
- Support for error scenarios

### Fixtures Available

- `client` - Sync client with mocked HTTP
- `async_client` - Async client with mocked HTTP
- `mock_gateway` - Mock gateway server
- `sample_action` - Sample ActionInfo
- `sample_counterparty` - Sample CounterpartyInfo
- `deny_response` - DENY decision response
- `escalate_response` - ESCALATE decision response
- `tool_error_response` - Tool execution error response
- `mock_langchain_tool` - Mock LangChain tool

## Writing New Tests

### Test Naming Convention

```python
class TestFeatureName:
    """Test feature description."""

    def test_specific_behavior(self):
        """Test that specific behavior works."""
        # Arrange
        ...

        # Act
        ...

        # Assert
        ...
```

### Using Fixtures

```python
def test_with_fixtures(client, mock_gateway, sample_action):
    """Test using provided fixtures."""
    # Configure mock response
    mock_gateway.set_response("/api/v1/gateway/execute", {...})

    # Use client
    response = client.execute(
        uapk_id="test",
        agent_id="test",
        action=sample_action,
    )

    # Assert
    assert response.decision == "ALLOW"
```

### Testing Error Scenarios

```python
def test_error_scenario(client, mock_gateway, execute_deny_response):
    """Test error handling."""
    # Set error response
    mock_gateway.set_response("/api/v1/gateway/execute", execute_deny_response)

    # Test exception is raised
    with pytest.raises(ActionDeniedError) as exc_info:
        client.execute(...)

    # Assert exception details
    assert exc_info.value.decision_response is not None
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_feature(async_client, mock_gateway):
    """Test async functionality."""
    response = await async_client.execute(...)
    assert response.decision == "ALLOW"
```

## Continuous Integration

Tests are run automatically on:
- Every pull request
- Every commit to main branch
- Nightly builds

### GitHub Actions

```yaml
- name: Run tests
  run: |
    pip install -e ".[dev,langchain]"
    pytest --cov=uapk_gateway --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Ensure SDK is installed in editable mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev,langchain]"
```

### LangChain Tests Skipped

If LangChain tests are skipped:

```bash
# Install LangChain
pip install langchain

# Or install all optional dependencies
pip install -e ".[all,dev]"
```

### Async Tests Failing

If async tests fail with warnings:

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
cat pytest.ini | grep asyncio_mode
```

### Coverage Not Working

If coverage isn't being collected:

```bash
# Install pytest-cov
pip install pytest-cov

# Run with explicit coverage
pytest --cov=uapk_gateway tests/
```

## Contributing Tests

When adding new features:

1. Write tests first (TDD)
2. Ensure >90% coverage for new code
3. Test both success and error paths
4. Test edge cases
5. Add docstrings to test functions
6. Run full test suite before submitting PR

```bash
# Run tests
pytest

# Check coverage
pytest --cov=uapk_gateway --cov-report=term-missing

# Format code
black tests/
ruff check tests/
```
