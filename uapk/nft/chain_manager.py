"""
Chain Manager (Phase 4)
Manages local Anvil blockchain via docker-compose.
"""
import subprocess
import time
import requests
from pathlib import Path


def start_chain() -> dict:
    """
    Start local Anvil chain via docker-compose.

    Returns:
        Status dict
    """
    compose_file = Path("docker-compose.chain.yml")

    if not compose_file.exists():
        return {"success": False, "message": "docker-compose.chain.yml not found"}

    try:
        # Start chain
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            check=True,
            capture_output=True
        )

        # Wait for chain to be ready
        time.sleep(2)

        # Check if reachable
        try:
            response = requests.post(
                "http://127.0.0.1:8545",
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=5
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Chain started successfully",
                    "rpc": "http://127.0.0.1:8545",
                    "chain_id": 31337
                }
        except:
            pass

        return {"success": True, "message": "Chain started (RPC not yet reachable, wait a few seconds)"}

    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Failed to start chain: {e.stderr.decode()}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to start chain: {str(e)}"}


def stop_chain() -> dict:
    """
    Stop local Anvil chain.

    Returns:
        Status dict
    """
    compose_file = Path("docker-compose.chain.yml")

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down"],
            check=True,
            capture_output=True
        )

        return {"success": True, "message": "Chain stopped successfully"}

    except Exception as e:
        return {"success": False, "message": f"Failed to stop chain: {str(e)}"}


def check_chain_status() -> dict:
    """
    Check if local chain is running.

    Returns:
        Status dict with reachable flag
    """
    try:
        response = requests.post(
            "http://127.0.0.1:8545",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=2
        )

        if response.status_code == 200:
            data = response.json()
            block_number = int(data.get("result", "0x0"), 16)

            return {
                "reachable": True,
                "rpc": "http://127.0.0.1:8545",
                "block_number": block_number
            }

    except Exception as e:
        return {
            "reachable": False,
            "error": str(e)
        }

    return {"reachable": False}
