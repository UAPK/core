"""
SSRF Protection Utilities (M1.3)
Prevents Server-Side Request Forgery attacks in connector framework.
"""
import ipaddress
import socket
from typing import Tuple, List
from urllib.parse import urlparse


# Private IP ranges (RFC 1918 + others)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),          # Class A private
    ipaddress.ip_network('172.16.0.0/12'),        # Class B private
    ipaddress.ip_network('192.168.0.0/16'),       # Class C private
    ipaddress.ip_network('127.0.0.0/8'),          # Loopback
    ipaddress.ip_network('169.254.0.0/16'),       # Link-local
    ipaddress.ip_network('::1/128'),              # IPv6 loopback
    ipaddress.ip_network('fe80::/10'),            # IPv6 link-local
    ipaddress.ip_network('fc00::/7'),             # IPv6 unique local
]


def is_private_ip(ip_str: str) -> bool:
    """Check if IP address is in private range"""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return True  # Err on side of caution


def resolve_hostname(hostname: str) -> List[str]:
    """Resolve hostname to IP addresses"""
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ips = list(set(info[4][0] for info in addr_info))
        return ips
    except (socket.gaierror, socket.timeout):
        return []


def is_url_safe(url: str, allowlist: List[str]) -> Tuple[bool, str]:
    """Check if URL is safe to request (SSRF protection)"""
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme not in ['http', 'https']:
        return False, f"Unsupported scheme: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    if not allowlist:
        return False, "No allowlist configured"

    # Check allowlist
    allowed = False
    for pattern in allowlist:
        if pattern == "*":
            allowed = True
            break
        elif pattern.startswith("*."):
            suffix = pattern[2:]
            if hostname.endswith(suffix) or hostname == suffix:
                allowed = True
                break
        elif pattern == hostname:
            allowed = True
            break

    if not allowed:
        return False, f"Hostname '{hostname}' not in allowlist"

    # Resolve hostname to IPs
    ips = resolve_hostname(hostname)
    if not ips:
        return False, f"Failed to resolve hostname: {hostname}"

    # Check if any IP is private
    for ip in ips:
        if is_private_ip(ip):
            return False, f"Hostname '{hostname}' resolves to private IP: {ip} (SSRF protection)"

    return True, f"URL safe (hostname: {hostname})"


def validate_redirect_url(original_url: str, redirect_url: str, allowlist: List[str]) -> Tuple[bool, str]:
    """Validate a redirect URL (re-apply SSRF checks)"""
    safe, reason = is_url_safe(redirect_url, allowlist)
    if not safe:
        return False, f"Redirect blocked: {reason}"

    # Check for scheme downgrade
    try:
        orig_scheme = urlparse(original_url).scheme
        redir_scheme = urlparse(redirect_url).scheme
        if orig_scheme == "https" and redir_scheme == "http":
            return False, "Redirect scheme downgrade blocked (https → http)"
    except Exception:
        pass

    return True, f"Redirect safe: {reason}"
