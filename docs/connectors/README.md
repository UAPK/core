# UAPK Connector Framework (M1.3)

**Feature**: Safe, manifest-driven external tool execution
**Implemented**: Milestone 1.3
**Version**: 2.0.0

---

## Overview

The ToolConnector framework allows agents to execute external tools (APIs, webhooks, services) with:

- **Manifest-driven configuration** (no hardcoded URLs)
- **SSRF protection** (allowlist enforcement + private IP blocking)
- **Multiple connector types** (Webhook, HTTP, Mock)
- **Extensible architecture** (add custom connectors)
- **Policy enforcement** (connectors checked by PolicyEngine before execution)

---

## Connector Types

### WebhookConnector

Sends HTTP POST to configured webhook URL.

**Use case**: Notify external systems, trigger workflows

**Configuration**:
```jsonld
"connectors": {
  "notification": {
    "name": "notification",
    "type": "webhook",
    "url": "https://hooks.example.com/notify",
    "allowlist": ["*.hooks.example.com"],
    "timeout": 30,
    "headers": {
      "X-Custom-Header": "value"
    }
  }
}
```

**Usage**:
```python
from uapk.connectors import WebhookConnector

connector = WebhookConnector(config)
result = await connector.execute('user_signup', {'user_id': 123, 'email': 'user@example.com'})
```

---

### HTTPConnector

Generic HTTP requests (GET, POST, PUT, DELETE).

**Use case**: Call external APIs, integrate with third-party services

**Configuration**:
```jsonld
"connectors": {
  "external_api": {
    "name": "external_api",
    "type": "http",
    "baseUrl": "https://api.example.com",
    "allowlist": ["*.example.com"],
    "timeout": 30,
    "defaultMethod": "POST",
    "authentication": {
      "type": "bearer",
      "secretName": "api_token"  // M1.5: Loaded from UAPK_SECRET_API_TOKEN env var
    }
  }
}
```

**Usage**:
```python
from uapk.connectors import HTTPConnector

connector = HTTPConnector(config)

# GET request
result = await connector.execute('GET /users', {'user_id': 123})

# POST request
result = await connector.execute('create_user', {'name': 'Alice', 'email': 'alice@example.com'})
```

---

### MockConnector

Deterministic mock responses for testing.

**Use case**: Testing without external dependencies

**Configuration**:
```jsonld
"connectors": {
  "mock_llm": {
    "name": "mock_llm",
    "type": "mock",
    "response_template": {
      "content": "This is a mock response",
      "model": "mock-v1"
    }
  }
}
```

---

## SSRF Protection

### Threat Model

**SSRF Attack**: Agent tricks gateway into making requests to internal resources:
- Internal APIs (http://localhost:8080/admin)
- Cloud metadata services (http://169.254.169.254/latest/meta-data/)
- Private network resources (http://192.168.1.100/database)

### Protection Mechanisms

#### 1. Allowlist Enforcement

Only domains/patterns in allowlist are allowed:

```python
allowlist = ['example.com', '*.openai.com']

is_url_safe('https://example.com/api', allowlist)  # ✅ SAFE
is_url_safe('https://api.openai.com/v1', allowlist)  # ✅ SAFE
is_url_safe('https://evil.com/callback', allowlist)  # ❌ BLOCKED
```

#### 2. Private IP Blocking

URLs resolving to private IPs are blocked:

```python
is_url_safe('http://192.168.1.1/admin', ['*'])  # ❌ BLOCKED (private IP)
is_url_safe('http://127.0.0.1:8080/api', ['*'])  # ❌ BLOCKED (loopback)
is_url_safe('http://10.0.0.1/internal', ['*'])  # ❌ BLOCKED (RFC 1918)
```

**Private ranges blocked**:
- 10.0.0.0/8 (Class A private)
- 172.16.0.0/12 (Class B private)
- 192.168.0.0/16 (Class C private)
- 127.0.0.0/8 (Loopback)
- 169.254.0.0/16 (Link-local)
- ::1/128 (IPv6 loopback)
- fe80::/10 (IPv6 link-local)
- fc00::/7 (IPv6 unique local)

#### 3. DNS Resolution Check

Hostname DNS resolution checked:

```python
# example.internal → 192.168.1.100
is_url_safe('https://example.internal/api', ['*.internal'])
# ❌ BLOCKED: "Hostname resolves to private IP: 192.168.1.100"
```

#### 4. Redirect Validation

HTTP redirects re-validated:

```python
# Original: https://example.com/redirect
# Redirects to: http://192.168.1.1/admin
# ❌ BLOCKED: Redirect leads to private IP
```

#### 5. TLS Verification

TLS certificates verified by default (no self-signed certs).

---

## Usage in Agents

### Before M1.3 (Hardcoded)

```python
class FulfillmentAgent:
    def generate_content(self, template: str, context: dict) -> str:
        # Hardcoded logic, no external API calls
        return template.format(**context)
```

### After M1.3 (Connector-Based)

```python
class FulfillmentAgent:
    def __init__(self, agent_id, manifest):
        self.llm_connector = HTTPConnector(manifest.connectors['llm'])

    async def generate_content(self, template: str, context: dict) -> str:
        # Call external LLM via connector
        result = await self.llm_connector.execute('POST /v1/chat/completions', {
            'model': 'gpt-4',
            'messages': [{'role': 'system', 'content': template}, ...]
        })

        if result['success']:
            return result['data']['choices'][0]['message']['content']
        else:
            # Fallback to template
            return template.format(**context)
```

---

## Manifest Configuration

### Connector Definition

```jsonld
{
  "saasModules": {
    "connectors": {
      "llm": {
        "name": "llm",
        "type": "http",
        "baseUrl": "https://api.openai.com/v1",
        "allowlist": ["*.openai.com"],
        "timeout": 30,
        "authentication": {
          "type": "bearer",
          "secretName": "openai_api_key"
        }
      },
      "webhook_notify": {
        "name": "webhook_notify",
        "type": "webhook",
        "url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
        "allowlist": ["hooks.slack.com"]
      },
      "mock_for_testing": {
        "name": "mock_for_testing",
        "type": "mock",
        "response_template": {
          "status": "ok"
        }
      }
    }
  }
}
```

### Secret Management (M1.5)

Connector authentication uses secret references (not values):

```jsonld
"authentication": {
  "type": "bearer",
  "secretName": "openai_api_key"  // NOT secretValue
}
```

Secrets loaded from environment:
```bash
export UAPK_SECRET_OPENAI_API_KEY="sk-..."
```

---

## Testing

### Unit Tests

```bash
pytest tests/test_connectors.py -v
```

**Test cases**:
- SSRF: Private IP detection (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, IPv6)
- SSRF: Allowlist enforcement
- SSRF: DNS resolution to private IP blocked
- SSRF: Redirect validation
- SSRF: Scheme validation (http/https only)
- MockConnector: Deterministic responses
- WebhookConnector: Config validation, private IP blocking
- HTTPConnector: Config validation, method determination, private IP blocking

### Integration Tests (Requires httpx + running services)

```bash
# Test with httpbin.org (public test service)
# Configure webhook connector to httpbin.org
# Execute: should succeed

# Test with localhost
# Configure webhook connector to localhost
# Execute: should fail (SSRF protection)
```

---

## Security Considerations

### Bypass Attempts & Mitigations

| Attack Vector | Mitigation |
|---------------|------------|
| **Direct private IP** | IP range check before request |
| **DNS to private IP** | Resolve hostname, check all IPs |
| **DNS rebinding** | Cache DNS resolution, re-check on redirect |
| **Redirect to private IP** | Re-validate redirect URLs |
| **Scheme downgrade** | Block https → http redirects |
| **Unicode homograph** | Use punycode hostname resolution |
| **Time-of-check-time-of-use (TOCTOU)** | Re-validate immediately before request |

### Production Hardening

1. **Strict allowlists**: Never use `['*']` in production
2. **Monitor connector usage**: Log all connector executions
3. **Rate limiting**: Apply per-connector rate limits
4. **Timeout enforcement**: Set reasonable timeouts (30s default)
5. **Certificate validation**: Enforce TLS verification (no self-signed)

---

## Limitations (M1.3 Scope)

- **No gRPC connector**: Only HTTP/HTTPS (gRPC future enhancement)
- **No database connector**: Use SQLModel ORM directly
- **No file system connector**: Security risk, not implemented
- **No custom connector registration**: Hardcoded types (webhook, http, mock)

---

## Roadmap

**M1.3** (Current):
- ✅ Base ToolConnector class
- ✅ SSRF protection utilities
- ✅ WebhookConnector
- ✅ HTTPConnector
- ✅ MockConnector
- ✅ Refactor one agent (FulfillmentAgent) as example

**Future enhancements**:
- Custom connector plugin system
- gRPC connector
- GraphQL connector
- Connector middleware (logging, retry, circuit breaker)
- Advanced SSRF: Machine learning-based anomaly detection

---

**Related Documentation**:
- `uapk/connectors/base.py` (source code)
- `uapk/connectors/ssrf.py` (SSRF utilities)
- `UAPK_VISION_ALIGNMENT_SCORECARD_DIFF.md` (M1.3 acceptance criteria)
