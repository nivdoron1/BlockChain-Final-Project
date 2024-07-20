// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "./IERC20.sol";

/**
 * @dev Interface of a Uniswap-style exchange.
 */
interface IExchange is IERC20 {
    /**
     * @dev Emitted when tokens are bought or sold with the details of the
     * purchase fees.
     */
    event FeeDetails(uint actualPayment, uint actualEthFee, uint actualTokenFee);

    /**
     * @dev Emitted when tokens are minted or burned.
     */
    event MintBurnDetails(uint numTOK, uint numETH);


    /**
     * @dev initialize the exchange contract and add liquidity.
     * Initialization may be performed only once. 
     * The initial supply of tokens is `initialTOK` (the caller must approve the exchange address to spend this much on their behalf).
     * The initial supply of ETH is `initialETH` (the value sent in the call must be at least this much).
     *
     * The number of liquidity tokens allocated is returned.
     */
    function initialize(IERC20 _RUXtoken, uint8 _feePercent, uint initialTOK, uint initialETH) external payable returns(uint) ;

    /**
     * Returns the current number of tokens in the liquidity pool.
     */
    function tokenBalance() external view returns(uint);

    /**
     * Returns the underlying token contract.
     */
    function getToken() external view returns(IERC20);



    /**
     * @dev Swap ETH for tokens.
     * Buy `amount` tokens as long as the total price is at most `maxPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens 
     * (rounded up) *after* they are bought, and taken from the ETH sent (rounded up) *before* the purchase.
     * Emits a `FeeDetails` event with the actual total value in ETH including the fee, the eth fee and the token fee.
     * @return Returns a tuple with the same information as the `FeeDetails` event.
     */
    function buyTokens(uint amount, uint maxPrice) external payable returns (uint,uint,uint);

    /**
     * @dev Swap tokens for ETH
     * Sell `amount` tokens as long as the total price is at least `minPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens 
     * (rounded up) *before* selling, and taken from the ETH returned (rounded up) *after* selling.
     * Emits a `FeeDetails` event with the actual total value in ETH minus the fee, the eth fee and the token fee.
     * @return Returns a tuple with the same information as the `FeeDetails` event.
     */
    function sellTokens(uint amount, uint minPrice) external returns (uint,uint,uint);

   /**
     * @dev mint `amount` liquidity tokens, as long as the total number of tokens spent is at most `maxTOK`
     * and the total amount of ETH spent is `maxETH`. The token allowance for the exchange address must be at least `maxTOK`,
     * and the msg value at least `maxETH`.
     * Unused funds will be returned to the sender.
     * Emits a `MintBurnDetails` event with the tuple (token_spent, eth_spent)
     * @return returns the same tuple as the `MintBurnDetails` event.
     */
    function mintLiquidityTokens(uint amount, uint maxTOK, uint maxETH) external payable returns (uint,uint);

    /**
     * @dev burn `amount` liquidity tokens, as long as this will result in at least minTOK tokens and at least minETH eth being generated.
     * The resulting tokens and ETH will be credited to the sender.
     * Emits a `MintBurnDetails` event with the tuple (token_credited, eth_credited).
     * @return returns the same tuple as the `MintBurnDetails` event.
     */
    function burnLiquidityTokens(uint amount, uint minTOK, uint minETH) external payable returns (uint,uint);
}
