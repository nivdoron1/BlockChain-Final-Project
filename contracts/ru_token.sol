// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "./interfaces/IERC20.sol";
import "./interfaces/IMultisigToken.sol";


/**
 * @dev An implementation of the ERC20 standard for a "Reichman University" Token.
 */
contract RUToken is IERC20, IERC20Metadata, IMultisigToken {

    event Debug (
        bytes32 hashVal,
        address multisig,
        address dest,
        uint amount,
        uint nonce,
        Signature sig
    );

    /**
     * Maximum number of mintable tokens.
     */
    uint private maxTokens;

    /**
     * Price required to mint a token in ETH
     */
    uint public tokenPrice;

    constructor(uint _tokenPrice, uint _maxTokens) {
        tokenPrice = _tokenPrice;
        maxTokens = _maxTokens;
    }

    uint private _totalTokens;

    mapping(address account => mapping(address spender => uint256)) private _permittedAllowances;

    mapping(address account => uint256) private _tokenBalances;

    mapping(bytes32 => address) private _multisigAddresses;

    mapping(address => bool) private _validMultisigs;



    function decimals() external pure override returns (uint8) {
        return 18;
    }

    function name() public pure override returns (string memory) {
        return "Reichman U Token";
    }

    function symbol() public pure override returns (string memory) {
        return "RUX";
    }

    function totalSupply() external view returns (uint256) {
        return _totalTokens;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _tokenBalances[account];
    }


    function transfer(address recipient, uint256 amount) external override returns (bool) {
        // Ensure the sender has enough tokens to transfer
        require(_tokenBalances[msg.sender] >= amount);
    
        // Verify the recipient address is valid
        require(recipient != address(0));
        
        // Deduct the amount from the sender's balance
        _tokenBalances[msg.sender] -= amount;
        
        // Add the amount to the recipient's balance
        _tokenBalances[recipient] += amount;
    
        // Emit a Transfer event to record the transaction
        emit Transfer(msg.sender, recipient, amount);
    
        // Return true to signify the transfer was successful
        return true;
    }

    function allowance(address owner, address spender) external view override returns (uint256) {
        return _permittedAllowances[owner][spender];
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        require(spender != address(0));
        _permittedAllowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }


    function transferFrom(address sender, address recipient, uint256 amount) external override returns (bool) {
        // Validate that the sender and recipient addresses are not zero
        require(sender != address(0));
        require(recipient != address(0));
    
        // Ensure the sender has enough tokens to transfer
        uint256 senderBalance = _tokenBalances[sender];
        require(senderBalance >= amount);
    
        // Check that the allowance is sufficient
        uint256 currentAllowance = _permittedAllowances[sender][msg.sender];
        require(currentAllowance >= amount);
    
        // Update balances and allowance
        _tokenBalances[sender] = senderBalance - amount;
        _tokenBalances[recipient] += amount;
        _permittedAllowances[sender][msg.sender] = currentAllowance - amount;
    
        // Emit a Transfer event
        emit Transfer(sender, recipient, amount);
    
        // Indicate successful transfer
        return true;
    }


    function mint() public payable returns (uint) {
        // Calculate the number of tokens to mint based on the amount of ether sent
        uint amountToMint = msg.value / tokenPrice;
        
        // Ensure minting this amount does not exceed the maximum token supply
        require(_totalTokens + amountToMint <= maxTokens);
    
        // Update the balance of the sender and the total supply of tokens
        _tokenBalances[msg.sender] += amountToMint;
        _totalTokens += amountToMint;
    
        // Emit a Transfer event from the zero address to the sender
        emit Transfer(address(0), msg.sender, amountToMint);
    
        // Return the amount of tokens minted
        return amountToMint;
    }


    function burn(uint amount) public {
        // Ensure the amount to burn does not exceed the total token supply
        require(amount <= _totalTokens);
    
        // Ensure the sender has enough tokens to burn
        require(amount <= _tokenBalances[msg.sender]);
    
        // Decrease the total supply and the sender's balance
        _totalTokens -= amount;
        _tokenBalances[msg.sender] -= amount;
    
        // Emit a Transfer event from the sender to the zero address
        emit Transfer(msg.sender, address(0), amount);
    
        // Calculate the value of the burned tokens in Ether
        uint valueInEth = tokenPrice * amount;
    
        // Send the Ether value to the sender
        (bool success, ) = msg.sender.call{value: valueInEth}("");
        require(success);
    }

    function registerMultisigAddress(address pk1, address pk2, address pk3) external override returns (address) {
        // Encode the addresses and hash them to generate a unique multisig address
        bytes32 encodedHash = keccak256(abi.encode(pk1, pk2, pk3));
        
        // Convert the hash to an address type
        address multisig = address(uint160(uint(encodedHash)));
        
        // Store the multisig address in the mapping
        _multisigAddresses[encodedHash] = multisig;
        
        // Mark the multisig address as valid
        _validMultisigs[multisig] = true;
        
        // Return the generated multisig address
        return multisig;
    }


    function getMultisigAddress(address pk1, address pk2, address pk3) external pure override returns (address) {
        return address(uint160(uint(keccak256(abi.encode(pk1, pk2, pk3)))));
    }

    function transfer2of3(
        address multisigOwner,
        address recipient,
        uint256 amount,
        uint nonce,
        Signature calldata secondSig
    ) external override returns (bool) {
        // Ensure the multisig owner address is valid
        require(_validMultisigs[multisigOwner]);
        
        // Ensure the multisig owner has enough balance
        require(_tokenBalances[multisigOwner] >= amount);
    
        // Create the transaction hash
        bytes32 txHash = keccak256(abi.encodePacked(this, multisigOwner, recipient, amount, nonce));
        
        // Perform the signature verification
        bytes32 fullHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", txHash));
        require(multisigOwner == ecrecover(fullHash, secondSig.v, secondSig.r, secondSig.s));
    
        // Update the balances
        _tokenBalances[multisigOwner] -= amount;
        _tokenBalances[recipient] += amount;
        
        // Emit the Transfer event
        emit Transfer(multisigOwner, recipient, amount);
        
        // Return true to indicate the transfer was successful
        return true;
    }

}