"""
NFT Minting Module
Mints business instance as NFT on local blockchain (Anvil/Hardhat).
"""
from typing import Dict, Any, Optional
from datetime import datetime


def mint_business_nft(
    metadata_uri: str,
    manifest_hash: str,
    plan_hash: str,
    merkle_root: str,
    rpc_url: str = "http://localhost:8545",
    chain_id: int = 31337,
    contract_address: Optional[str] = None,
    private_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mint NFT representing the business instance.

    This connects to a local Anvil/Hardhat chain and:
    1. Connects to the blockchain via web3
    2. Uses the deployed ERC-721 contract
    3. Mints token with metadata URI
    4. Returns transaction receipt

    Falls back to simulation if web3 is not available or chain is not running.
    """

    # Try real minting first
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            raise ConnectionError("Cannot connect to chain")

        if not contract_address:
            raise ValueError("Contract address required for minting")

        if not private_key:
            raise ValueError("Private key required for minting")

        # Get account from private key
        account = w3.eth.account.from_key(private_key)

        # Get contract instance
        abi = get_nft_contract_abi()
        contract = w3.eth.contract(address=contract_address, abi=abi)

        # Build mint transaction
        tx = contract.functions.mint(
            account.address,
            metadata_uri
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if tx_receipt['status'] == 1:
            # Extract token ID from logs (assuming Transfer event)
            token_id = tx_receipt['logs'][0]['topics'][3].hex() if tx_receipt['logs'] else 1

            receipt = {
                "contract": contract_address,
                "tokenId": int(token_id, 16) if isinstance(token_id, str) else token_id,
                "chainId": chain_id,
                "metadataURI": metadata_uri,
                "manifestHash": manifest_hash,
                "planHash": plan_hash,
                "merkleRoot": merkle_root,
                "mintedAt": datetime.utcnow().isoformat() + "Z",
                "transactionHash": tx_hash.hex(),
                "blockNumber": tx_receipt['blockNumber'],
                "status": "confirmed"
            }

            return receipt
        else:
            raise Exception("Transaction failed")

    except ImportError:
        pass  # Fall through to simulation
    except Exception as e:
        # Log error and fall through to simulation
        print(f"Real minting failed: {e}. Using simulation mode.")

    # Simulated mint (fallback when blockchain is not available)
    receipt = {
        "contract": contract_address or "0x5FbDB2315678afecb367f032d93F642f64180aa3",
        "tokenId": 1,  # Would increment in production
        "chainId": chain_id,
        "metadataURI": metadata_uri,
        "manifestHash": manifest_hash,
        "planHash": plan_hash,
        "merkleRoot": merkle_root,
        "mintedAt": datetime.utcnow().isoformat() + "Z",
        "transactionHash": "0x" + "0" * 64,  # Simulated tx hash
        "blockNumber": 1,
        "status": "simulated"  # Would be "confirmed" in production
    }

    return receipt


def get_nft_contract_abi() -> list:
    """
    Return ERC-721 contract ABI.
    Minimal ABI for minting.
    """
    return [
        {
            "inputs": [
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "string", "name": "tokenURI", "type": "string"}
            ],
            "name": "mint",
            "outputs": [
                {"internalType": "uint256", "name": "", "type": "uint256"}
            ],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
            ],
            "name": "tokenURI",
            "outputs": [
                {"internalType": "string", "name": "", "type": "string"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]


def get_nft_contract_bytecode() -> str:
    """
    Solidity contract for OpsPilotOS Business Instance NFT.

    Minimal ERC-721 implementation.
    In production, deploy this or use OpenZeppelin.
    """
    # This is placeholder. Real bytecode would come from:
    # solc --bin --abi contracts/OpsPilotOSBusinessInstance.sol
    return "0x608060405234801561001057600080fd5b50..."  # Truncated for brevity


# Solidity source (for reference)
SOLIDITY_SOURCE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract OpsPilotOSBusinessInstance is ERC721URIStorage, Ownable {
    uint256 private _tokenIdCounter;

    struct BusinessMetadata {
        string manifestHash;
        string planHash;
        string auditMerkleRoot;
        uint256 mintedAt;
    }

    mapping(uint256 => BusinessMetadata) public businessMetadata;

    constructor() ERC721("OpsPilotOS Business Instance", "OPSOS") {}

    function mint(
        address to,
        string memory tokenURI,
        string memory manifestHash,
        string memory planHash,
        string memory auditMerkleRoot
    ) public onlyOwner returns (uint256) {
        uint256 tokenId = _tokenIdCounter++;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);

        businessMetadata[tokenId] = BusinessMetadata({
            manifestHash: manifestHash,
            planHash: planHash,
            auditMerkleRoot: auditMerkleRoot,
            mintedAt: block.timestamp
        });

        return tokenId;
    }

    function getBusinessMetadata(uint256 tokenId)
        public
        view
        returns (BusinessMetadata memory)
    {
        return businessMetadata[tokenId];
    }
}
"""
