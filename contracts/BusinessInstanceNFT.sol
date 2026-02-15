// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BusinessInstanceNFT
 * @dev ERC-721 NFT representing UAPK business instances.
 * Each token represents a cryptographically-verified business instance
 * with manifest, plan, and audit trail.
 */
contract BusinessInstanceNFT {
    // Token ID counter
    uint256 private _nextTokenId;

    // Contract owner (minter)
    address public owner;

    // Token metadata
    struct BusinessMetadata {
        string manifestHash;
        string planHash;
        string packageHash;
        string auditMerkleRoot;
        string instanceId;
        uint256 mintedAt;
        string compilerVersion;
    }

    // Mappings
    mapping(uint256 => address) private _owners;
    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => BusinessMetadata) public businessMetadata;
    mapping(address => uint256) private _balances;

    // Events
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event BusinessInstanceMinted(
        uint256 indexed tokenId,
        string instanceId,
        string manifestHash,
        string tokenURI
    );

    constructor() {
        owner = msg.sender;
        _nextTokenId = 1;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    /**
     * @dev Mint a new business instance NFT
     */
    function mint(
        address to,
        string memory tokenURI,
        string memory instanceId,
        string memory manifestHash,
        string memory planHash,
        string memory packageHash,
        string memory auditMerkleRoot,
        string memory compilerVersion
    ) public onlyOwner returns (uint256) {
        require(to != address(0), "Invalid address");
        require(bytes(instanceId).length > 0, "instanceId required");
        require(bytes(manifestHash).length > 0, "manifestHash required");

        uint256 tokenId = _nextTokenId++;

        _owners[tokenId] = to;
        _tokenURIs[tokenId] = tokenURI;
        _balances[to] += 1;

        businessMetadata[tokenId] = BusinessMetadata({
            manifestHash: manifestHash,
            planHash: planHash,
            packageHash: packageHash,
            auditMerkleRoot: auditMerkleRoot,
            instanceId: instanceId,
            mintedAt: block.timestamp,
            compilerVersion: compilerVersion
        });

        emit Transfer(address(0), to, tokenId);
        emit BusinessInstanceMinted(tokenId, instanceId, manifestHash, tokenURI);

        return tokenId;
    }

    /**
     * @dev Get token URI
     */
    function tokenURI(uint256 tokenId) public view returns (string memory) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return _tokenURIs[tokenId];
    }

    /**
     * @dev Get business metadata
     */
    function getBusinessMetadata(uint256 tokenId) public view returns (BusinessMetadata memory) {
        require(_owners[tokenId] != address(0), "Token does not exist");
        return businessMetadata[tokenId];
    }

    /**
     * @dev Get owner of token
     */
    function ownerOf(uint256 tokenId) public view returns (address) {
        address tokenOwner = _owners[tokenId];
        require(tokenOwner != address(0), "Token does not exist");
        return tokenOwner;
    }

    /**
     * @dev Get balance of address
     */
    function balanceOf(address tokenOwner) public view returns (uint256) {
        require(tokenOwner != address(0), "Invalid address");
        return _balances[tokenOwner];
    }

    /**
     * @dev Get total supply
     */
    function totalSupply() public view returns (uint256) {
        return _nextTokenId - 1;
    }
}
