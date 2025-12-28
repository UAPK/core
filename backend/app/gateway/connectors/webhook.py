"""Webhook connector - POST to configured URL."""

import ipaddress
import json
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.gateway.connectors.base import ConnectorConfig, ConnectorResult, ToolConnector


class WebhookConnector(ToolConnector):
    """Connector that POSTs to a configured webhook URL.

    Configuration:
        url: The webhook URL to POST to
        headers: Optional headers to include
        timeout_seconds: Request timeout (default 30s)
        secret_refs: Map of header names to secret names for auth

    No retries are performed (retries=0 as per spec).
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
        if not config.url:
            raise ValueError("WebhookConnector requires a 'url' in config")
        self.settings = get_settings()

    def _get_allowed_domains(self) -> list[str]:
        """Get the list of allowed domains.

        Prefer connector-specific allowlist, otherwise fall back to global.
        """
        if self.config.extra.get("allowed_domains"):
            return self.config.extra["allowed_domains"]
        return self.settings.gateway_allowed_webhook_domains

    def _max_response_bytes(self) -> int:
        env_val = getattr(self.settings, "gateway_max_connector_response_bytes", None)
        base = env_val if isinstance(env_val, int) and env_val > 0 else 1_000_000
        extra = self.config.extra.get("max_response_bytes")
        return extra if isinstance(extra, int) and extra > 0 else base

    def _validate_url(self, url: str) -> tuple[bool, str | None, set[str] | None]:
        """Validate URL against SSRF attacks.

        Returns (is_valid, error_message, resolved_ips).

        Blocks:
        - Private IP ranges (RFC 1918, loopback, link-local)
        - Invalid URLs
        - Non-HTTP(S) schemes

        Enforces allowed_domains if configured.
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid URL scheme: {parsed.scheme}", None

            # Check hostname is present
            if not parsed.hostname:
                return False, "Missing hostname in URL", None

            # Check allowed_domains (deny-by-default for security)
            allowed_domains = self._get_allowed_domains()
            if not allowed_domains:
                return False, "No allowed domains configured for webhook", None

            hostname = parsed.hostname.lower()
            # Check for exact match OR subdomain (with dot prefix) to prevent suffix bypass
            # e.g., "example.com" allows "example.com" and "sub.example.com" but NOT "evilexample.com"
            if not any(
                hostname == domain.lower() or hostname.endswith(f".{domain.lower()}")
                for domain in allowed_domains
            ):
                return False, f"Domain '{parsed.hostname}' not in allowlist", None

            # Resolve hostname to IP and check against blocked ranges
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
            return False, f"Invalid URL: {str(e)}", None

    def _dns_drifted(self, hostname: str, expected_ips: set[str]) -> bool:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            current_ips = {info[4][0] for info in addr_info}
            return current_ips != expected_ips
        except Exception:
            return True

    async def execute(self, params: dict[str, Any]) -> ConnectorResult:
        """Execute the webhook by POSTing params to the configured URL."""
        start_time = time.monotonic()

        url = self.config.url

        # SSRF protection - validate URL before making request
        is_valid, error_msg, resolved_ips = self._validate_url(url)
        if not is_valid:
            return ConnectorResult(
                success=False,
                error={
                    "code": "SSRF_BLOCKED",
                    "message": error_msg,
                },
                duration_ms=0,
            )

        headers = self._build_headers()
        headers.setdefault("Content-Type", "application/json")
        timeout = self.config.timeout_seconds
        max_bytes = self._max_response_bytes()

        # Resolve any secrets in params
        resolved_params = self._resolve_all_params(params)

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

            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST", url, json=resolved_params, headers=headers) as response:
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > max_bytes:
                            return ConnectorResult(
                                success=False,
                                error={
                                    "code": "RESPONSE_TOO_LARGE",
                                    "message": f"Webhook response exceeded max size ({max_bytes} bytes).",
                                },
                                status_code=response.status_code,
                                duration_ms=int((time.monotonic() - start_time) * 1000),
                            )
                    content = bytes(raw)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if response.status_code >= 200 and response.status_code < 300:
                try:
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
                        "message": f"Webhook returned status {response.status_code}",
                    },
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

        except httpx.TimeoutException:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "TIMEOUT",
                    "message": f"Webhook request timed out after {timeout}s",
                },
                duration_ms=duration_ms,
            )

        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "REQUEST_ERROR",
                    "message": str(e),
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "UNKNOWN_ERROR",
                    "message": str(e),
                },
                duration_ms=duration_ms,
            )
