"""
HTTPConnector (M1.3)
Generic HTTP connector supporting GET, POST, PUT, DELETE with SSRF protection.
"""
import httpx
from typing import Dict, Any

from uapk.connectors.base import ToolConnector
from uapk.connectors.ssrf import is_url_safe, validate_redirect_url


class HTTPConnector(ToolConnector):
    """
    Generic HTTP connector for API calls.
    Supports GET, POST, PUT, DELETE methods with SSRF protection.
    """

    def validate_config(self):
        """Validate HTTP connector configuration"""
        if 'baseUrl' not in self.config and 'url' not in self.config:
            raise ValueError("HTTPConnector requires 'baseUrl' or 'url' in config")

        if 'allowlist' not in self.config:
            raise ValueError("HTTPConnector requires 'allowlist' in config")

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute HTTP request.

        Args:
            action: HTTP method or action identifier (e.g., "GET /users", "create_user")
            params: Parameters (become query params for GET, body for POST/PUT)

        Returns:
            {'success': bool, 'data': response} or {'success': False, 'error': str}
        """
        # Determine URL
        base_url = self.config.get('baseUrl') or self.config.get('url')
        url = self._build_url(base_url, action, params)

        # Determine HTTP method
        method = self._get_method(action, params)

        # SSRF protection
        allowlist = self.config.get('allowlist', [])
        safe, reason = is_url_safe(url, allowlist)
        if not safe:
            return {
                'success': False,
                'error': f'SSRF protection blocked request: {reason}'
            }

        # Build request
        headers = self._build_headers()
        timeout = self.config.get('timeout', 30)

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                event_hooks={'response': [lambda r: self._check_redirect_safety(r, allowlist)]}
            ) as client:

                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=params)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {'success': False, 'error': f'Unsupported method: {method}'}

                response.raise_for_status()

                # Parse response
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                else:
                    data = response.text

                return {
                    'success': True,
                    'data': data,
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }

        except httpx.HTTPStatusError as e:
            return {
                'success': False,
                'error': f'HTTP {e.response.status_code}: {e.response.text[:200]}',
                'status_code': e.response.status_code
            }
        except httpx.RequestError as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'HTTP connector execution failed: {str(e)}'
            }

    def _build_url(self, base_url: str, action: str, params: Dict[str, Any]) -> str:
        """Build full URL from base URL and action"""
        # If action looks like a path (starts with /), append to base
        if action.startswith('/'):
            return base_url.rstrip('/') + action

        # If action has URL pattern, use url_template from config
        url_template = self.config.get('url_template')
        if url_template:
            # Simple substitution (e.g., "https://api.example.com/{action}")
            return url_template.format(action=action, **params)

        # Default: use base_url as-is
        return base_url

    def _get_method(self, action: str, params: Dict[str, Any]) -> str:
        """Determine HTTP method from action or params"""
        # Check params for explicit method
        if 'method' in params:
            return params['method'].upper()

        # Check if action specifies method (e.g., "GET /users")
        if action.startswith('GET ') or action.startswith('get_'):
            return 'GET'
        elif action.startswith('POST ') or action.startswith('create_') or action.startswith('post_'):
            return 'POST'
        elif action.startswith('PUT ') or action.startswith('update_') or action.startswith('put_'):
            return 'PUT'
        elif action.startswith('DELETE ') or action.startswith('delete_'):
            return 'DELETE'

        # Default from config or POST
        return self.config.get('defaultMethod', 'POST').upper()

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers including authentication"""
        headers = self.config.get('headers', {}).copy()

        # Add authentication
        auth = self.config.get('authentication', {})
        auth_type = auth.get('type')

        if auth_type == 'bearer':
            # Bearer token (load from secret)
            secret_name = auth.get('secretName')
            if secret_name:
                # TODO M1.5: Load from env var via get_secret()
                # For now, use placeholder
                token = auth.get('secretValue', 'placeholder-token')
                headers['Authorization'] = f'Bearer {token}'

        elif auth_type == 'basic':
            # Basic auth (not implemented in M1.3)
            pass

        elif auth_type == 'apikey':
            # API key in header
            key_name = auth.get('headerName', 'X-API-Key')
            secret_name = auth.get('secretName')
            if secret_name:
                # TODO M1.5: Load from env var
                api_key = auth.get('secretValue', 'placeholder-key')
                headers[key_name] = api_key

        return headers

    def _check_redirect_safety(self, response: httpx.Response, allowlist: list):
        """Validate redirect URLs for SSRF protection"""
        if response.is_redirect:
            redirect_url = response.headers.get('location', '')
            if redirect_url:
                original_url = str(response.url)
                safe, reason = validate_redirect_url(original_url, redirect_url, allowlist)
                if not safe:
                    raise httpx.RequestError(f'SSRF: {reason}')
