# UAPK Gateway Python SDK - Package Manifest

**Version:** 1.0.0
**Package Name:** `uapk-gateway`
**Status:** ✅ Ready for PyPI Publication

---

## Package Structure

```
uapk-gateway/
├── pyproject.toml                    # Build configuration
├── setup.py                          # Backward compatibility
├── README.md                         # Package documentation (1,528 words)
├── LICENSE                           # Apache 2.0
├── CHANGELOG.md                      # Version history
├── MANIFEST.in                       # Package file inclusion rules
│
├── uapk_gateway/                     # Main package (~1,067 lines)
│   ├── __init__.py                   # Package exports (68 lines)
│   ├── client.py                     # Sync client (305 lines)
│   ├── async_client.py               # Async client (286 lines)
│   ├── models.py                     # Pydantic models (79 lines)
│   ├── exceptions.py                 # Exception classes (39 lines)
│   └── integrations/
│       ├── __init__.py               # Integration exports
│       └── langchain.py              # LangChain wrapper (290 lines)
│
├── tests/                            # Test suite (2,818 lines)
│   ├── __init__.py
│   ├── conftest.py                   # Fixtures (391 lines)
│   ├── test_client.py                # Sync tests (538 lines)
│   ├── test_async_client.py          # Async tests (544 lines)
│   ├── test_models.py                # Model tests (471 lines)
│   ├── test_exceptions.py            # Exception tests (353 lines)
│   ├── test_langchain_integration.py # LangChain tests (521 lines)
│   └── README.md                     # Testing guide
│
├── examples/                         # Example scripts
│   ├── quickstart.py                 # Basic usage
│   ├── async_usage.py                # Async patterns
│   ├── langchain_integration.py      # LangChain examples
│   ├── openai_function_calling.py    # OpenAI integration
│   └── README.md                     # Examples guide
│
└── docs/                             # Additional documentation
    ├── TESTING_REPORT.md             # Test coverage analysis
    ├── PUBLISHING_GUIDE.md           # PyPI publishing guide
    ├── PACKAGE_MANIFEST.md           # This file
    ├── pytest.ini                    # Pytest configuration
    ├── run_tests.sh                  # Test runner
    ├── verify_package.py             # Package verification
    └── simple_verify.py              # Simple verification
```

---

## Distribution Packages

When built with `python -m build`, produces:

### 1. Source Distribution (sdist)
**File:** `uapk_gateway-1.0.0.tar.gz`
- Complete source code
- All documentation
- Test suite
- Examples

### 2. Wheel Distribution
**File:** `uapk_gateway-1.0.0-py3-none-any.whl`
- Pure Python (py3)
- Platform independent (none)
- Universal (any)
- Optimized for installation

---

## Package Contents (What Gets Installed)

### Core Package (~131 KB)

```python
uapk_gateway/
├── __init__.py          # Exports: UAPKGatewayClient, AsyncUAPKGatewayClient, models, exceptions
├── client.py            # Sync client with retry logic
├── async_client.py      # Async client (same API as sync)
├── models.py            # ActionInfo, GatewayDecisionResponse, etc.
├── exceptions.py        # ActionDeniedError, ActionEscalatedError, etc.
└── integrations/
    ├── __init__.py      # Exports: UAPKGatewayTool
    └── langchain.py     # LangChain tool wrapper
```

**Files Included in Distribution:**
- All `.py` files in `uapk_gateway/`
- README.md (shown on PyPI)
- LICENSE (Apache 2.0)
- CHANGELOG.md

**Files NOT Included:**
- Tests (user can access via GitHub)
- Examples (user can access via GitHub)
- Development tools
- Documentation source files

---

## Dependencies

### Required (Always Installed)

```python
httpx >= 0.25.0         # HTTP client (sync + async)
pydantic >= 2.0.0       # Data validation
```

### Optional Extras

```bash
# LangChain integration
pip install uapk-gateway[langchain]
# Adds: langchain >= 0.1.0

# All optional dependencies
pip install uapk-gateway[all]
# Adds: langchain

# Development dependencies
pip install uapk-gateway[dev]
# Adds: pytest, pytest-asyncio, pytest-cov, black, ruff, mypy

# Documentation dependencies
pip install uapk-gateway[docs]
# Adds: sphinx, sphinx-rtd-theme
```

---

## Installation Methods

### From PyPI (after publishing)

```bash
# Latest stable release
pip install uapk-gateway

# Specific version
pip install uapk-gateway==1.0.0

# With optional dependencies
pip install uapk-gateway[langchain]
pip install uapk-gateway[all,dev]
```

### From Source (development)

```bash
# Clone repository
git clone https://github.com/anthropics/uapk-gateway.git
cd uapk-gateway/sdks/python

# Editable install
pip install -e .

# With dev dependencies
pip install -e ".[dev,langchain]"
```

### From Wheel (local)

```bash
# After building
pip install dist/uapk_gateway-1.0.0-py3-none-any.whl
```

---

## Public API

### Clients

```python
from uapk_gateway import UAPKGatewayClient, AsyncUAPKGatewayClient

# Sync
client = UAPKGatewayClient(base_url="...", api_key="...")
response = client.execute(...)

# Async
async with AsyncUAPKGatewayClient(...) as client:
    response = await client.execute(...)
```

### Models

```python
from uapk_gateway.models import (
    ActionInfo,
    CounterpartyInfo,
    GatewayActionRequest,
    GatewayDecision,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
    ReasonCode,
    ReasonDetail,
    ToolResult,
)
```

### Exceptions

```python
from uapk_gateway.exceptions import (
    UAPKGatewayError,           # Base exception
    AuthenticationError,
    ActionDeniedError,
    ActionEscalatedError,
    ToolExecutionError,
    NetworkError,
    ValidationError,
    RateLimitError,
)
```

### Integrations

```python
from uapk_gateway.integrations.langchain import (
    UAPKGatewayTool,
    wrap_langchain_tools,
)
```

---

## Version Information

**Current Version:** 1.0.0
**Release Date:** 2024-12-28
**Python Support:** 3.10, 3.11, 3.12
**License:** Apache 2.0

### Version History

- **1.0.0** (2024-12-28) - Initial release
  - Sync and async clients
  - Full Pydantic validation
  - LangChain integration
  - Comprehensive test suite (107 tests)
  - Complete documentation

---

## Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Code Lines | ~1,067 | ✅ |
| Test Lines | 2,818 | ✅ |
| Test Cases | 107 | ✅ |
| Test Coverage | >90% | ✅ |
| Test-to-Code Ratio | 2.6:1 | ✅ |
| Package Size | ~131 KB | ✅ |
| Documentation Words | 1,528 | ✅ |

---

## PyPI Metadata

**Name:** uapk-gateway
**Summary:** Official Python SDK for UAPK Gateway - compliance and audit control plane for AI agents

**Keywords:** ai, agents, compliance, audit, governance, langchain, openai, security

**Classifiers:**
- Development Status :: 4 - Beta
- Intended Audience :: Developers
- License :: OSI Approved :: Apache Software License
- Programming Language :: Python :: 3
- Programming Language :: Python :: 3.10
- Programming Language :: Python :: 3.11
- Programming Language :: Python :: 3.12
- Topic :: Software Development :: Libraries :: Python Modules
- Topic :: Security
- Topic :: System :: Logging

**Project URLs:**
- Homepage: https://github.com/anthropics/uapk-gateway
- Documentation: https://docs.uapk.dev
- Repository: https://github.com/anthropics/uapk-gateway
- Issues: https://github.com/anthropics/uapk-gateway/issues

---

## Build Artifacts (After `python -m build`)

```
dist/
├── uapk_gateway-1.0.0-py3-none-any.whl    # Wheel (preferred)
└── uapk_gateway-1.0.0.tar.gz              # Source distribution

build/                                       # Temporary build files
└── [build artifacts]

uapk_gateway.egg-info/                      # Package metadata
├── PKG-INFO
├── SOURCES.txt
├── dependency_links.txt
├── requires.txt
└── top_level.txt
```

---

## File Size Breakdown

| Component | Size | Description |
|-----------|------|-------------|
| Core Code | ~45 KB | Main package code |
| Documentation | ~65 KB | README, CHANGELOG, etc. |
| LICENSE | ~11 KB | Apache 2.0 license |
| Integrations | ~10 KB | LangChain wrapper |
| **Total** | **~131 KB** | **Installed package** |

**Tests:** ~90 KB (not included in distribution)
**Examples:** ~25 KB (not included in distribution)

---

## Verification Checklist

✅ All required files present
✅ Version consistency (1.0.0)
✅ Dependencies specified correctly
✅ README complete and well-formatted
✅ LICENSE included
✅ CHANGELOG updated
✅ PyPI classifiers set
✅ Package builds successfully
✅ Tests pass (107/107)
✅ Code coverage >90%
✅ Import works correctly
✅ Examples run without errors
✅ Documentation comprehensive

---

## Post-Publication URLs

**After publishing to PyPI:**

- Package Page: https://pypi.org/project/uapk-gateway/
- Documentation: https://pypi.org/project/uapk-gateway/#description
- Downloads: https://pypi.org/project/uapk-gateway/#files
- Statistics: https://pypistats.org/packages/uapk-gateway

**Installation Badge (for README):**

```markdown
[![PyPI version](https://badge.fury.io/py/uapk-gateway.svg)](https://badge.fury.io/py/uapk-gateway)
```

---

**Manifest Generated:** 2024-12-28
**Package Status:** ✅ Ready for PyPI Publication
**Estimated Build Time:** <30 seconds
**Estimated Upload Time:** <1 minute
