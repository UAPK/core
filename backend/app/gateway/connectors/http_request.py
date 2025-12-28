"""HTTP Request connector - generic HTTP requests with domain allowlist."""

import ipaddress
import json
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.gateway.connectors.base import ConnectorConfig, ConnectorResult, ToolConnector


class HttpRequestConnector(ToolConnector):
    """Connector for generic HTTP requests with strict domain allowlist.

    Configuration:
        url: The URL template (can contain {param} placeholders)
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Optional headers
        timeout_seconds: Request timeout
        extra.allowed_domains: List of allowed domains (overrides global setting)

    Security:
        - Only requests to allowlisted domains are permitted
        - SSRF protection: blocks private IP ranges
        - URL is validated before request
    """

    # Private IP ranges to block (SSRF protection)
    BLOCKED_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),  # IPv6 localhost
        ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    def __init__(self, config: ConnectorConfig, secrets: dict[str, str] | None = None) -> None:
        super().__init__(config, secrets)
        self.settings = get_settings()

    def _max_response_bytes(self) -> int:
        # Backwards-compatible: env override or connector extra override
        # Default 1MB
        env_val = getattr(self.settings, "gateway_max_connector_response_bytes", None)
        if isinstance(env_val, int) and env_val > 0:
            base = env_val
        else:
            base = 1_000_000
        extra = self.config.extra.get("max_response_bytes")
        if isinstance(extra, int) and extra > 0:
            return extra
        return base

    def _get_allowed_domains(self) -> list[str]:
        """Get the list of allowed domains."""
        # First check connector-specific allowlist
        if self.config.extra.get("allowed_domains"):
            return self.config.extra["allowed_domains"]
        # Fall back to global setting
        return self.settings.gateway_allowed_webhook_domains

    def _validate_url(self, url: str) -> tuple[bool, str | None, set[str] | None]:
        """Validate URL is in allowed domains and not targeting private IPs.

        Returns (is_valid, error_message, resolved_ips).
        """
        allowed_domains = self._get_allowed_domains()

        # If no domains configured, deny by default for security
        if not allowed_domains:
            return False, "No allowed domains configured", None

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid URL scheme: {parsed.scheme}", None

            # Check hostname is present
            if not parsed.hostname:
                return False, "Missing hostname in URL", None

            domain = parsed.hostname.lower()

            # Check against allowed domains
            domain_allowed = False
            for allowed in allowed_domains:
                allowed = allowed.lower()
                # Exact match or subdomain match
                if domain == allowed or domain.endswith(f".{allowed}"):
                    domain_allowed = True
                    break

            if not domain_allowed:
                return False, f"Domain '{domain}' not in allowlist", None

            # SSRF protection - check for private IP ranges
            try:
                # Get all IP addresses for the hostname
                resolved_ips: set[str] = set()
                addr_info = socket.getaddrinfo(parsed.hostname, None)
                for info in addr_info:
                    ip_str = info[4][0]
                    resolved_ips.add(ip_str)
                    ip_addr = ipaddress.ip_address(ip_str)

                    # Check if IP is in any blocked range
                    for blocked_range in self.BLOCKED_IP_RANGES:
                        if ip_addr in blocked_range:
                            return False, f"Access to private/internal IP {ip_str} blocked (SSRF protection)", None

            except socket.gaierror:
                return False, f"Could not resolve hostname: {parsed.hostname}", None

            return True, None, resolved_ips

        except Exception as e:
            return False, f"Invalid URL: {e}", None

    def _dns_drifted(self, hostname: str, expected_ips: set[str]) -> bool:
        """Best-effort DNS rebinding mitigation: deny if DNS answer changed between validate and request."""
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            current_ips = {info[4][0] for info in addr_info}
            return current_ips != expected_ips
        except Exception:
            return True

    def _build_url(self, params: dict[str, Any]) -> str:
        """Build the final URL, substituting placeholders."""
        url = self.config.url or ""

        # Substitute {param} placeholders
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))

        return url

    async def execute(self, params: dict[str, Any]) -> ConnectorResult:
        """Execute the HTTP request."""
        start_time = time.monotonic()

        # Build and validate URL
        url = self._build_url(params)
        is_valid, error, resolved_ips = self._validate_url(url)

        if not is_valid:
            return ConnectorResult(
                success=False,
                error={
                    "code": "DOMAIN_NOT_ALLOWED",
                    "message": error or "URL validation failed",
                },
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        method = self.config.method.upper()
        headers = self._build_headers()
        timeout = self.config.timeout_seconds
        max_bytes = self._max_response_bytes()

        # Resolve secrets in params
        resolved_params = self._resolve_all_params(params)

        # Remove params that were used in URL template
        body_params = {k: v for k, v in resolved_params.items() if f"{{{k}}}" not in (self.config.url or "")}

        try:
            parsed = urlparse(url)
            if resolved_ips and self._dns_drifted(parsed.hostname or "", resolved_ips):
                return ConnectorResult(
                    success=False,
                    error={
                        "code": "SSRF_DNS_DRIFT",
                        "message": "DNS resolution changed between validation and request (possible DNS rebinding).",
                    },
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                )

            # Never follow redirects (prevents allowlisted domain redirecting to internal targets)
            # Never trust environment proxies (prevents unexpected routing)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                # Stream response to enforce size limit safely
                request_kwargs: dict[str, Any] = {"headers": headers}
                if method in ("GET", "DELETE"):
                    request_kwargs["params"] = body_params if body_params else None
                else:
                    headers.setdefault("Content-Type", "application/json")
                    request_kwargs["json"] = body_params if body_params else None

                async with client.stream(method, url, **request_kwargs) as response:
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > max_bytes:
                            return ConnectorResult(
                                success=False,
                                error={
                                    "code": "RESPONSE_TOO_LARGE",
                                    "message": f"Upstream response exceeded max size ({max_bytes} bytes).",
                                },
                                status_code=response.status_code,
                                duration_ms=int((time.monotonic() - start_time) * 1000),
                            )

                    content = bytes(raw)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if 200 <= response.status_code < 300:
                try:
                    # Parse JSON only if it looks like JSON; otherwise return raw text (bounded)
                    ctype = (response.headers.get("content-type") or "").lower()
                    if "application/json" in ctype or content.strip().startswith((b"{", b"[")):
                        data = json.loads(content.decode("utf-8", errors="replace"))
                    else:
                        data = {"raw_response": content.decode("utf-8", errors="replace")}
                except Exception:
                    data = {"raw_response": content.decode("utf-8", errors="replace")}

                result = ConnectorResult(
                    success=True,
                    data=data,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
                result.result_hash = result.compute_hash()
                return result
            else:
                return ConnectorResult(
                    success=False,
                    error={
                        "code": f"HTTP_{response.status_code}",
                        "message": f"Request returned status {response.status_code}",
                    },
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

        except httpx.TimeoutException:
            return ConnectorResult(
                success=False,
                error={
                    "code": "TIMEOUT",
                    "message": f"Request timed out after {timeout}s",
                },
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        except httpx.RequestError as e:
            return ConnectorResult(
                success=False,
                error={
                    "code": "REQUEST_ERROR",
                    "message": str(e),
                },
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )

        except Exception as e:
            return ConnectorResult(
                success=False,
                error={
                    "code": "UNKNOWN_ERROR",
                    "message": str(e),
                },
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
