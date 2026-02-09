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
    chain_id: int = 31337
) -> Dict[str, Any]:
    """
    Mint NFT representing the business instance.

    In production, this would:
    1. Connect to local Anvil/Hardhat chain
    2. Deploy ERC-721 contract (if not exists)
    3. Mint token with metadata URI
    4. Return transaction receipt

    For now, we simulate the mint and return a receipt.
    To make this real, uncomment web3 code below.
    """

    # Simulated mint (for when blockchain is not running)
    # In production with Anvil running:
    # from web3 import Web3
    # w3 = Web3(Web3.HTTPProvider(rpc_url))
    # contract = w3.eth.contract(address=contract_address, abi=abi)
    # tx = contract.functions.mint(to=owner, tokenURI=metadata_uri).transact()
    # receipt = w3.eth.wait_for_transaction_receipt(tx)

    # Simulated receipt
    receipt = {
        "contract": "0x5FbDB2315678afecb367f032d93F642f64180aa3",  # First Anvil contract address
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
