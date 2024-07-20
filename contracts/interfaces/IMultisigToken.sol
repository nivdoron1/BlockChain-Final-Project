// SPDX-License-Identifier: MIT

pragma solidity ^0.8.26;


/**
 * Ethereum-compatible signature
 */
struct Signature {
    bytes32 r; // First 32 bytes of signature
    bytes32 s; // Second 32 bytes of signature
    uint8 v; // Final 1 byte of signature
}

/**
 * @dev Interface of tokens supporting 2-out-of-3 multisig accounts.
 */
interface IMultisigToken {
    /**
     * @dev registers a multisig address controlled by the public keys `pk1`, `pk2` and `pk3`.
     * The returned address should always match 
     */
    function registerMultisigAddress(address pk1, address pk2, address pk3) external returns (address);

    /**
     * @dev returns the address controlled by the public keys `pk1`, `pk2` and `pk3`.
     */
    function getMultisigAddress(address pk1, address pk2, address pk3) external pure returns (address);

    /**
     * @dev Moves `amount` tokens from the multisig address `multisigOwner` to `recipient`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     * `multisigOwner` must have been previously registered using `registerMultisigAddress`.
     * `msg.sender` must be one of the public keys controlling `multisigOwner`, and `secondSig` must be a valid signature proving that
     * a second controlling public key approved the transaction as well.
     *
     * `nonce` is used to prevent replay attacks (note that EVM does not allow a contract to access the actual transaction nonce).
     *
     * Emits a {Transfer} event.
     */
    function transfer2of3(address multisigOwner, address recipient, uint256 amount, uint nonce, Signature calldata secondSig) external returns (bool);

}