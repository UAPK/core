"""
WebhookConnector (M1.3)
Sends HTTP POST requests to configured webhook URLs with SSRF protection.
"""
import httpx
from typing import Dict, Any

from uapk.connectors.base import ToolConnector
from uapk.connectors.ssrf import is_url_safe, validate_redirect_url


class WebhookConnector(ToolConnector):
    """
    Webhook connector: sends HTTP POST to configured URL.
    Includes SSRF protection and allowlist enforcement.
    """

    def validate_config(self):
        """Validate webhook configuration"""
        if 'url' not in self.config:
            raise ValueError("WebhookConnector requires 'url' in config")

        if 'allowlist' not in self.config:
            raise ValueError("WebhookConnector requires 'allowlist' in config (use ['*'] to allow all, not recommended)")

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute webhook: POST to configured URL.

        Args:
            action: Action identifier (included in payload)
            params: Parameters to send

        Returns:
            {'success': bool, 'data': response_data} or {'success': False, 'error': str}
        """
        url = self.config['url']
        allowlist = self.config.get('allowlist', [])
        timeout = self.config.get('timeout', 30)

        # SSRF protection: check URL safety
        safe, reason = is_url_safe(url, allowlist)
        if not safe:
            return {
                'success': False,
                'error': f'SSRF protection blocked request: {reason}'
            }

        # Construct payload
        payload = {
            'action': action,
            'params': params,
            'timestamp': httpx._utils.utcnow().isoformat() + 'Z'
        }

        # Additional headers
        headers = self.config.get('headers', {})

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                event_hooks={
                    'response': [
                        lambda r: self._check_redirect_safety(r, allowlist)
                    ]
                }
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                return {
                    'success': True,
                    'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                    'status_code': response.status_code
                }

        except httpx.HTTPStatusError as e:
            return {
                'success': False,
                'error': f'HTTP {e.response.status_code}: {e.response.text[:200]}'
            }
        except httpx.RequestError as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Webhook execution failed: {str(e)}'
            }

    def _check_redirect_safety(self, response: httpx.Response, allowlist: List[str]):
        """
        Event hook to validate redirect URLs.
        Raises exception if redirect leads to unsafe URL.
        """
        if response.is_redirect:
            redirect_url = response.headers.get('location', '')
            if redirect_url:
                original_url = str(response.url)
                safe, reason = validate_redirect_url(original_url, redirect_url, allowlist)
                if not safe:
                    raise httpx.RequestError(f'SSRF: {reason}')
