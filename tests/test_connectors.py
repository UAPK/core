"""
Tests for ToolConnector Framework and SSRF Protection (M1.3)
"""
import pytest
from uapk.connectors.ssrf import (
    is_private_ip,
    is_url_safe,
    validate_redirect_url
)
from uapk.connectors.mock import MockConnector

# Skip HTTP tests if httpx not available
try:
    import httpx
    from uapk.connectors.webhook import WebhookConnector
    from uapk.connectors.http import HTTPConnector
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class TestSSRFProtection:
    """Test SSRF protection utilities"""

    def test_is_private_ip_detects_private_ranges(self):
        """Test private IP detection for all ranges"""
        # Private IPv4 ranges
        assert is_private_ip('10.0.0.1') is True
        assert is_private_ip('10.255.255.255') is True
        assert is_private_ip('172.16.0.1') is True
        assert is_private_ip('172.31.255.255') is True
        assert is_private_ip('192.168.0.1') is True
        assert is_private_ip('192.168.255.255') is True

        # Loopback
        assert is_private_ip('127.0.0.1') is True
        assert is_private_ip('127.255.255.255') is True

        # Link-local
        assert is_private_ip('169.254.0.1') is True

        # IPv6 loopback
        assert is_private_ip('::1') is True

        # IPv6 link-local
        assert is_private_ip('fe80::1') is True

    def test_is_private_ip_allows_public_ips(self):
        """Test public IP addresses are allowed"""
        assert is_private_ip('8.8.8.8') is False  # Google DNS
        assert is_private_ip('1.1.1.1') is False  # Cloudflare DNS
        assert is_private_ip('93.184.216.34') is False  # example.com

    def test_is_url_safe_checks_allowlist(self):
        """Test URL allowlist enforcement"""
        allowlist = ['example.com', '*.openai.com']

        # Exact match
        safe, _ = is_url_safe('https://example.com/api', allowlist)
        assert safe is True

        # Wildcard subdomain match
        safe, _ = is_url_safe('https://api.openai.com/v1/chat', allowlist)
        assert safe is True

        # Not in allowlist
        safe, reason = is_url_safe('https://evil.com/callback', allowlist)
        assert safe is False
        assert 'not in allowlist' in reason.lower()

    def test_is_url_safe_blocks_private_ips(self):
        """Test SSRF protection blocks URLs resolving to private IPs"""
        allowlist = ['*']  # Allow all domains (but still check DNS)

        # Direct private IP
        safe, reason = is_url_safe('http://192.168.1.1/admin', allowlist)
        assert safe is False
        assert 'private ip' in reason.lower() or 'not in allowlist' in reason.lower()

        # Localhost
        safe, reason = is_url_safe('http://127.0.0.1:8080/secrets', allowlist)
        assert safe is False

        # Note: Testing DNS resolution to private IP is hard without mock,
        # but the logic is in is_url_safe via resolve_hostname

    def test_is_url_safe_validates_scheme(self):
        """Test only http/https schemes allowed"""
        allowlist = ['example.com']

        # Valid schemes
        safe, _ = is_url_safe('http://example.com', allowlist)
        assert safe is True

        safe, _ = is_url_safe('https://example.com', allowlist)
        assert safe is True

        # Invalid schemes
        safe, reason = is_url_safe('file:///etc/passwd', allowlist)
        assert safe is False
        assert 'scheme' in reason.lower() or 'unsupported' in reason.lower()

        safe, reason = is_url_safe('ftp://example.com/file', allowlist)
        assert safe is False

    def test_validate_redirect_blocks_scheme_downgrade(self):
        """Test redirect validation blocks https→http downgrade"""
        allowlist = ['example.com']

        original = 'https://example.com/secure'
        redirect = 'http://example.com/insecure'

        safe, reason = validate_redirect_url(original, redirect, allowlist)
        assert safe is False
        assert 'downgrade' in reason.lower()

    def test_validate_redirect_allows_safe_redirect(self):
        """Test redirect validation allows safe redirects"""
        allowlist = ['example.com']

        original = 'http://example.com/old'
        redirect = 'https://example.com/new'

        safe, _ = validate_redirect_url(original, redirect, allowlist)
        assert safe is True


class TestMockConnector:
    """Test MockConnector"""

    @pytest.mark.asyncio
    async def test_mock_connector_returns_success(self):
        """Test mock connector returns deterministic response"""
        config = {
            'name': 'test_mock',
            'type': 'mock'
        }

        connector = MockConnector(config)
        result = await connector.execute('test_action', {'key': 'value'})

        assert result['success'] is True
        assert result['mock'] is True
        assert 'data' in result

    @pytest.mark.asyncio
    async def test_mock_connector_with_template(self):
        """Test mock connector with response template"""
        config = {
            'name': 'test_mock',
            'type': 'mock',
            'response_template': {'result': 'custom_response', 'id': 123}
        }

        connector = MockConnector(config)
        result = await connector.execute('test', {})

        assert result['success'] is True
        assert result['data']['result'] == 'custom_response'
        assert result['data']['id'] == 123


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestWebhookConnector:
    """Test WebhookConnector (requires httpx)"""

    def test_webhook_connector_validates_config(self):
        """Test webhook connector requires url and allowlist"""
        # Missing url
        with pytest.raises(ValueError, match="requires 'url'"):
            WebhookConnector({'name': 'test'})

        # Missing allowlist
        with pytest.raises(ValueError, match="requires 'allowlist'"):
            WebhookConnector({'name': 'test', 'url': 'https://example.com'})

        # Valid config
        connector = WebhookConnector({
            'name': 'test',
            'url': 'https://example.com/webhook',
            'allowlist': ['example.com']
        })
        assert connector.name == 'test'

    @pytest.mark.asyncio
    async def test_webhook_connector_blocks_private_ip(self):
        """Test webhook connector blocks private IP URLs"""
        config = {
            'name': 'test',
            'url': 'http://192.168.1.1/admin',
            'allowlist': ['*']  # Even with wildcard, private IPs blocked
        }

        connector = WebhookConnector(config)
        result = await connector.execute('test', {})

        assert result['success'] is False
        assert 'ssrf' in result['error'].lower() or 'private' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_webhook_connector_blocks_non_allowlisted_domain(self):
        """Test webhook connector enforces allowlist"""
        config = {
            'name': 'test',
            'url': 'https://evil.com/callback',
            'allowlist': ['example.com']
        }

        connector = WebhookConnector(config)
        result = await connector.execute('test', {})

        assert result['success'] is False
        assert 'allowlist' in result['error'].lower()


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHTTPConnector:
    """Test HTTPConnector (requires httpx)"""

    def test_http_connector_validates_config(self):
        """Test HTTP connector requires baseUrl/url and allowlist"""
        # Missing URL
        with pytest.raises(ValueError, match="requires 'baseUrl' or 'url'"):
            HTTPConnector({'name': 'test'})

        # Missing allowlist
        with pytest.raises(ValueError, match="requires 'allowlist'"):
            HTTPConnector({'name': 'test', 'baseUrl': 'https://api.example.com'})

        # Valid config
        connector = HTTPConnector({
            'name': 'test',
            'baseUrl': 'https://api.example.com',
            'allowlist': ['*.example.com']
        })
        assert connector.name == 'test'

    def test_http_connector_determines_method(self):
        """Test HTTP method determination from action"""
        config = {
            'name': 'test',
            'baseUrl': 'https://api.example.com',
            'allowlist': ['*.example.com']
        }
        connector = HTTPConnector(config)

        # From action prefix
        assert connector._get_method('GET /users', {}) == 'GET'
        assert connector._get_method('POST /users', {}) == 'POST'
        assert connector._get_method('PUT /users/1', {}) == 'PUT'
        assert connector._get_method('DELETE /users/1', {}) == 'DELETE'

        # From action naming
        assert connector._get_method('get_user', {}) == 'GET'
        assert connector._get_method('create_user', {}) == 'POST'
        assert connector._get_method('update_user', {}) == 'PUT'
        assert connector._get_method('delete_user', {}) == 'DELETE'

        # From params
        assert connector._get_method('custom', {'method': 'PATCH'}) == 'PATCH'

        # Default
        assert connector._get_method('unknown_action', {}) == 'POST'

    @pytest.mark.asyncio
    async def test_http_connector_blocks_private_ip(self):
        """Test HTTP connector blocks private IPs"""
        config = {
            'name': 'test',
            'baseUrl': 'http://127.0.0.1:8080',
            'allowlist': ['*']
        }

        connector = HTTPConnector(config)
        result = await connector.execute('GET /admin', {})

        assert result['success'] is False
        assert 'ssrf' in result['error'].lower() or 'private' in result['error'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
