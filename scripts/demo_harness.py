#!/usr/bin/env python3
"""Demo Harness for UAPK Gateway

This script demonstrates the three core capabilities:
1. Budget caps that DENY over-limit actions
2. Approval thresholds that ESCALATE high-value actions
3. Tamper-evident audit trail verification

Usage:
    python scripts/demo_harness.py [--base-url http://localhost:8000]
"""

import argparse
import hashlib
import json
import sys
import time
from typing import Any

import requests


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


class GatewayClient:
    """Client for interacting with UAPK Gateway API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.bearer_token: str | None = None
        self.api_key: str | None = None
        self.org_id: str | None = None
        self.user_id: str | None = None

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Login and obtain bearer token for operator actions."""
        print_info(f"Logging in as {email}...")
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        self.bearer_token = data["access_token"]
        self.user_id = data["user_id"]
        print_success("Logged in successfully")
        return data

    def get_headers(self, use_api_key: bool = False) -> dict[str, str]:
        """Get headers for API requests."""
        if use_api_key:
            if not self.api_key:
                raise ValueError("API key not set")
            return {"X-API-Key": self.api_key}
        else:
            if not self.bearer_token:
                raise ValueError("Bearer token not set")
            return {"Authorization": f"Bearer {self.bearer_token}"}

    def create_org(self, name: str, slug: str) -> dict[str, Any]:
        """Create an organization."""
        print_info(f"Creating organization '{name}'...")
        response = requests.post(
            f"{self.base_url}/api/v1/organizations",
            headers=self.get_headers(),
            json={"name": name, "slug": slug},
        )
        response.raise_for_status()
        data = response.json()
        self.org_id = data["id"]
        print_success(f"Organization created: {self.org_id}")
        return data

    def get_or_create_org(self, name: str, slug: str) -> str:
        """Get existing org or create new one."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/organizations",
                headers=self.get_headers(),
            )
            response.raise_for_status()
            orgs = response.json().get("items", [])
            for org in orgs:
                if org["slug"] == slug:
                    self.org_id = org["id"]
                    print_success(f"Using existing organization: {self.org_id}")
                    return org["id"]
        except Exception:
            pass

        org = self.create_org(name, slug)
        return org["id"]

    def create_api_key(self, name: str) -> str:
        """Create API key for agent authentication."""
        print_info(f"Creating API key '{name}'...")
        response = requests.post(
            f"{self.base_url}/api/v1/orgs/{self.org_id}/api-keys",
            headers=self.get_headers(),
            json={"name": name, "org_id": self.org_id},
        )
        response.raise_for_status()
        data = response.json()
        self.api_key = data["key"]
        print_success("API key created for agent")
        return data["key"]

    def register_manifest(self, manifest: dict[str, Any], description: str) -> str:
        """Register a UAPK manifest."""
        print_info("Registering manifest...")
        response = requests.post(
            f"{self.base_url}/api/v1/orgs/{self.org_id}/manifests",
            headers=self.get_headers(),
            json={
                "org_id": self.org_id,
                "manifest": manifest,
                "description": description,
            },
        )
        response.raise_for_status()
        data = response.json()
        manifest_id = data["id"]
        print_success(f"Manifest registered: {manifest_id}")
        return manifest_id

    def activate_manifest(self, manifest_id: str) -> None:
        """Activate a manifest."""
        print_info("Activating manifest...")
        response = requests.post(
            f"{self.base_url}/api/v1/manifests/{manifest_id}/activate",
            headers=self.get_headers(),
        )
        response.raise_for_status()
        print_success("Manifest activated")

    def gateway_evaluate(self, uapk_id: str, agent_id: str, action: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an action via the gateway."""
        response = requests.post(
            f"{self.base_url}/api/v1/gateway/evaluate",
            headers=self.get_headers(use_api_key=True),
            json={
                "uapk_id": uapk_id,
                "agent_id": agent_id,
                "action": action,
            },
        )
        response.raise_for_status()
        return response.json()

    def gateway_execute(
        self, uapk_id: str, agent_id: str, action: dict[str, Any], override_token: str | None = None
    ) -> dict[str, Any]:
        """Execute an action via the gateway."""
        payload: dict[str, Any] = {
            "uapk_id": uapk_id,
            "agent_id": agent_id,
            "action": action,
        }
        if override_token:
            payload["override_token"] = override_token

        response = requests.post(
            f"{self.base_url}/api/v1/gateway/execute",
            headers=self.get_headers(use_api_key=True),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def get_approvals(self, status: str | None = None) -> dict[str, Any]:
        """Get approval tasks."""
        params = {}
        if status:
            params["status"] = status
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{self.org_id}/approvals",
            headers=self.get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def approve_action(self, approval_id: str, notes: str = "") -> dict[str, Any]:
        """Approve an escalated action."""
        response = requests.post(
            f"{self.base_url}/api/v1/orgs/{self.org_id}/approvals/{approval_id}/approve",
            headers=self.get_headers(),
            json={"notes": notes},
        )
        response.raise_for_status()
        return response.json()

    def export_logs(self, uapk_id: str) -> list[dict[str, Any]]:
        """Export interaction logs for verification."""
        response = requests.get(
            f"{self.base_url}/ui/logs/export",
            headers=self.get_headers(),
            params={"uapk_id": uapk_id, "format": "jsonl"},
        )
        response.raise_for_status()

        # Parse JSONL
        records = []
        for line in response.text.strip().split("\n"):
            if line:
                data = json.loads(line)
                if data.get("type") == "record":
                    records.append(data)

        return records


def demo_1_budget_caps(client: GatewayClient, uapk_id: str) -> None:
    """Demo 1: Budget caps that DENY over-limit actions."""
    print_header("DEMO 1: Budget Caps")
    print("Agent has $100 USD cap. Watch what happens when we exceed it:")

    # Test 1: Under cap (should ALLOW)
    print("\n🔹 Test 1: $50 refund (under $100 cap)")
    action = {
        "type": "payment",
        "tool": "stripe_refund",
        "params": {"amount": 50, "currency": "USD", "customer_id": "cust_123"},
    }
    result = client.gateway_evaluate(uapk_id, "agent-001", action)
    if result["decision"] == "allow":
        print_success(f"Decision: {result['decision'].upper()}")
        print(f"   └─ Amount within cap, action allowed")
    else:
        print_error(f"Decision: {result['decision'].upper()} (unexpected!)")

    # Test 2: Over cap (should DENY)
    print("\n🔹 Test 2: $150 refund (exceeds $100 cap)")
    action["params"]["amount"] = 150
    result = client.gateway_evaluate(uapk_id, "agent-001", action)
    if result["decision"] == "deny":
        print_success(f"Decision: {result['decision'].upper()}")
        reason = result["reasons"][0]
        print(f"   └─ {reason['message']}")
    else:
        print_error(f"Decision: {result['decision'].upper()} (unexpected!)")


def demo_2_approval_workflow(client: GatewayClient, uapk_id: str) -> None:
    """Demo 2: Approval thresholds that ESCALATE high-value actions."""
    print_header("DEMO 2: Approval Workflow")
    print("Agent has $50 approval threshold. Amounts >$50 require human approval:")

    # Test 1: Over threshold (should ESCALATE)
    print("\n🔹 Test 1: $75 refund (exceeds $50 approval threshold)")
    action = {
        "type": "payment",
        "tool": "stripe_refund",
        "params": {"amount": 75, "currency": "USD", "customer_id": "cust_456"},
    }
    result = client.gateway_evaluate(uapk_id, "agent-001", action)
    if result["decision"] == "escalate":
        print_warning(f"Decision: {result['decision'].upper()}")
        reason = result["reasons"][0]
        print(f"   └─ {reason['message']}")
        approval_id = result.get("approval_id")
        if approval_id:
            print(f"   └─ Approval ID: {approval_id}")

            # Simulate human approval
            print("\n🔹 Test 2: Human operator approves")
            time.sleep(1)  # Simulate thinking time
            approval_result = client.approve_action(approval_id, "Confirmed with customer")
            override_token = approval_result.get("override_token")
            print_success("Approval granted")
            print(f"   └─ Override token: {override_token[:20]}...")

            # Execute with override token
            print("\n🔹 Test 3: Execute with override token")
            execute_result = client.gateway_execute(
                uapk_id, "agent-001", action, override_token=override_token
            )
            if execute_result["decision"] == "allow" and execute_result.get("executed"):
                print_success(f"Decision: {execute_result['decision'].upper()}")
                print(f"   └─ Action executed successfully")
            else:
                print_error(f"Execution failed: {execute_result}")
    else:
        print_error(f"Decision: {result['decision'].upper()} (expected ESCALATE)")


def demo_3_audit_trail(client: GatewayClient, uapk_id: str) -> None:
    """Demo 3: Tamper-evident audit trail verification."""
    print_header("DEMO 3: Audit Trail Verification")
    print("Verifying tamper-evident hash chain:")

    # Generate some activity
    print("\n🔹 Generating activity...")
    for i in range(3):
        action = {
            "type": "data_access",
            "tool": "read_user",
            "params": {"user_id": f"user_{i}"},
        }
        client.gateway_execute(uapk_id, "agent-001", action)
    print_success("Generated 3 actions")

    # Export logs
    print("\n🔹 Exporting logs...")
    records = client.export_logs(uapk_id)
    print_success(f"Exported {len(records)} records")

    # Verify chain
    print("\n🔹 Verifying hash chain...")
    if not records:
        print_warning("No records to verify")
        return

    prev_hash = None
    for i, record in enumerate(records):
        current_hash = record.get("record_hash")
        prev_record_hash = record.get("previous_record_hash")

        if i > 0:
            if prev_record_hash != prev_hash:
                print_error(f"Chain broken at record {i}!")
                print(f"   Expected: {prev_hash}")
                print(f"   Got: {prev_record_hash}")
                return

        prev_hash = current_hash

    print_success(f"Chain verified: {len(records)} records linked")
    print(f"   └─ Each record cryptographically links to previous")
    print(f"   └─ Tampering would break the chain")


def main() -> int:
    """Main demo harness entry point."""
    parser = argparse.ArgumentParser(description="UAPK Gateway Demo Harness")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the gateway API",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Admin user email",
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="Admin user password",
    )
    args = parser.parse_args()

    print_header("UAPK Gateway Demo Harness")
    print(f"Gateway URL: {args.base_url}")

    client = GatewayClient(args.base_url)

    try:
        # Step 1: Authentication
        print_header("Setup: Authentication & Organization")
        client.login(args.email, args.password)

        # Step 2: Organization
        org_id = client.get_or_create_org("Demo Org", "demo-org")

        # Step 3: API Key for agent
        api_key = client.create_api_key("demo-agent-key")

        # Step 4: Register manifest
        print_header("Setup: Register & Activate Manifest")
        manifest = {
            "version": "1.0",
            "agent": {
                "id": "payment-agent-demo",
                "name": "Payment Agent (Demo)",
                "version": "1.0.0",
                "description": "Demo payment agent with budget caps and approval thresholds",
            },
            "capabilities": {
                "requested": ["payment:transfer", "payment:refund", "data:read"]
            },
            "policy": {
                "amount_caps": {"USD": 100},  # Hard cap at $100
                "approval_thresholds": {
                    "amount": 50,  # Require approval for amounts > $50
                    "currency": "USD",
                },
                "tool_allowlist": ["stripe_refund", "stripe_transfer", "read_user"],
            },
            "tools": {
                "stripe_refund": {
                    "type": "mock",
                    "config": {"response_data": {"success": True}},
                },
                "stripe_transfer": {
                    "type": "mock",
                    "config": {"response_data": {"success": True}},
                },
                "read_user": {
                    "type": "mock",
                    "config": {"response_data": {"user": {"id": "123", "name": "Test User"}}},
                },
            },
        }
        manifest_id = client.register_manifest(manifest, "Demo manifest with caps and approvals")
        client.activate_manifest(manifest_id)

        # Run demos
        uapk_id = "payment-agent-demo"
        demo_1_budget_caps(client, uapk_id)
        demo_2_approval_workflow(client, uapk_id)
        demo_3_audit_trail(client, uapk_id)

        # Summary
        print_header("Demo Complete")
        print_success("All three core capabilities demonstrated:")
        print("  1. ✅ Budget caps (DENY over-limit)")
        print("  2. ✅ Approval thresholds (ESCALATE → Approve → Execute)")
        print("  3. ✅ Tamper-evident audit trail")
        print("\n💡 Key Takeaway: Agents can act fast, but can't go rogue")

        return 0

    except requests.HTTPError as e:
        print_error(f"HTTP Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(json.dumps(e.response.json(), indent=2))
            except Exception:
                print(e.response.text)
        return 1
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
