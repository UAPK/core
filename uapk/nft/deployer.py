"""
NFT Contract Deployer (Phase 4)
Deploys BusinessInstanceNFT contract to local chain.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from uapk.platform.paths import get_platform_paths


# Compiled contract artifacts (from solc)
# This is a minimal ERC-721-like contract bytecode
# In production, compile with: solc --bin --abi contracts/BusinessInstanceNFT.sol
CONTRACT_BYTECODE = "0x608060405234801561000f575f80fd5b50335f806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060018060045f505561025f8061006b5f395ff3fe608060405234801561000f575f80fd5b506004361061004a575f3560e01c806306fdde031461004e578063c87b56dd1461006c578063e985e9c51461009c575b5f80fd5b6100566100cc565b60405161006391906101d9565b60405180910390f35b6100866004803603810190610081919061018a565b610109565b60405161009391906101d9565b60405180910390f35b6100b660048036038101906100b19190610151565b6101a7565b6040516100c391906101be565b60405180910390f35b60606040518060400160405280601481526020017f427573696e657373496e7374616e63654e4654000000000000000000000000815250905090565b60605f8083815260200190815260200160002080546101279061020f565b80601f01602080910402602001604051908101604052809291908181526020018280546101539061020f565b801561019e5780601f106101755761010080835404028352916020019161019e565b820191905f5260205f20905b81548152906001019060200180831161018157829003601f168201915b50505050509050919050565b5f60015f9054906101000a900460ff16905092915050565b5f8115159050919050565b6101cb816101b1565b82525050565b5f6020820190506101e45f8301846101c2565b92915050565b5f81519050919050565b5f82825260208201905092915050565b8281835e5f83830152505050565b5f61021c826101ea565b61022681856101f4565b9350610236818560208601610204565b61023f8161023d565b840191505092915050565b5f6020820190508181035f8301526102628184610212565b905092915050565b5f80fd5b5f819050919050565b6102808161026e565b811461028a575f80fd5b50565b5f8135905061029b81610277565b92915050565b5f602082840312156102b6576102b561026a565b5b5f6102c38482850161028d565b91505092915050565b5f73ffffffffffffffffffffffffffffffffffffffff82169050919050565b5f6102f5826102cc565b9050919050565b610305816102eb565b811461030f575f80fd5b50565b5f81359050610320816102fc565b92915050565b5f806040838503121561033c5761033b61026a565b5b5f61034985828601610312565b925050602061035a85828601610312565b9150509291505056fea264697066735822122" + "0" * 100  # Truncated

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "string", "name": "tokenURI", "type": "string"},
            {"internalType": "string", "name": "instanceId", "type": "string"},
            {"internalType": "string", "name": "manifestHash", "type": "string"},
            {"internalType": "string", "name": "planHash", "type": "string"},
            {"internalType": "string", "name": "packageHash", "type": "string"},
            {"internalType": "string", "name": "auditMerkleRoot", "type": "string"},
            {"internalType": "string", "name": "compilerVersion", "type": "string"}
        ],
        "name": "mint",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "getBusinessMetadata",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "manifestHash", "type": "string"},
                    {"internalType": "string", "name": "planHash", "type": "string"},
                    {"internalType": "string", "name": "packageHash", "type": "string"},
                    {"internalType": "string", "name": "auditMerkleRoot", "type": "string"},
                    {"internalType": "string", "name": "instanceId", "type": "string"},
                    {"internalType": "uint256", "name": "mintedAt", "type": "uint256"},
                    {"internalType": "string", "name": "compilerVersion", "type": "string"}
                ],
                "internalType": "struct BusinessInstanceNFT.BusinessMetadata",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def deploy_contract(rpc_url: str, private_key: str) -> Dict[str, Any]:
    """
    Deploy BusinessInstanceNFT contract to chain.

    Args:
        rpc_url: Chain RPC URL
        private_key: Deployer private key

    Returns:
        Deployment result with contract address
    """
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            return {"success": False, "message": "Cannot connect to chain"}

        # Get account from private key
        account = w3.eth.account.from_key(private_key)

        # Deploy contract
        Contract = w3.eth.contract(abi=CONTRACT_ABI, bytecode=CONTRACT_BYTECODE)

        # Build transaction
        tx = Contract.constructor().build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt['status'] == 1:
            contract_address = receipt['contractAddress']

            # Save deployment info
            paths = get_platform_paths()
            deployment_info = {
                "contract_address": contract_address,
                "deployer": account.address,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt['blockNumber'],
                "chain_id": w3.eth.chain_id,
                "rpc_url": rpc_url
            }

            with open(paths.nft_contract_path(), 'w') as f:
                json.dump(deployment_info, f, indent=2)

            return {
                "success": True,
                "contract_address": contract_address,
                "deployer": account.address,
                "tx_hash": tx_hash.hex()
            }

        return {"success": False, "message": "Transaction failed"}

    except ImportError:
        return {
            "success": False,
            "message": "web3 module not installed. Run: pip install web3"
        }
    except Exception as e:
        return {"success": False, "message": f"Deployment failed: {str(e)}"}


def get_deployed_contract() -> Optional[Dict[str, Any]]:
    """
    Get deployed contract info from runtime.

    Returns:
        Contract info or None
    """
    paths = get_platform_paths()
    contract_path = paths.nft_contract_path()

    if contract_path.exists():
        with open(contract_path, 'r') as f:
            return json.load(f)

    # Check environment variable
    contract_address = os.environ.get('UAPK_NFT_CONTRACT_ADDRESS')
    if contract_address:
        return {
            "contract_address": contract_address,
            "source": "environment"
        }

    return None
