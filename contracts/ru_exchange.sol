// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "./interfaces/IERC20.sol";
import "./interfaces/IExchange.sol";

contract RUExchange is IExchange {
    bool private isInitialized;
    IERC20 private exchangeToken;
    uint8 private exchangeFeePercent;
    uint private tokenReserve;
    uint private ethReserve;
    uint256 public totalLiquidityShares;
    mapping(address => uint256) private userShares;
    mapping(address => mapping (address => uint256)) private userAllowances;
    constructor() {
    }

    function grade_exchange() pure public returns (bool) {
        return true;
    }

    function getToken() override external view returns(IERC20) {
        return exchangeToken;
    }

    function initialize(IERC20 _RUXtoken, uint8 _feePercent, uint initialTOK, uint initialETH) override public payable returns(uint) {
        require(!isInitialized, "Already initialized");
        require(msg.value >= initialETH, "Insufficient ETH");
        require(_feePercent >= 0, "Invalid fee percent");

        exchangeToken = _RUXtoken;
        exchangeFeePercent = _feePercent;
        tokenReserve = initialTOK;
        ethReserve = initialETH;
        totalLiquidityShares = 1000 * exchangeToken.totalSupply();
        userShares[msg.sender] = totalLiquidityShares;

        require(exchangeToken.transferFrom(msg.sender, address(this), tokenReserve), "Token transfer failed");
        isInitialized = true;
        return tokenReserve;
    }
    
    /**
     * @dev Swap ETH for tokens.
     * Buy `amount` tokens as long as the total price is at most `maxPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens
     * (rounded up) *after* they are bought, and taken from the ETH sent (rounded up) *before* the purchase.
     * @return Returns the actual total cost in ETH including fee.
     */
    function buyTokens(uint tokenAmount, uint256 maxEthAmount) override public payable returns (uint, uint, uint) {
        require(tokenAmount > 0, "Token amount must be greater than 0");
        require(maxEthAmount > 0, "Max ETH amount must be greater than 0");
        require(tokenAmount < tokenReserve, "Insufficient token pool");
        require(msg.value >= maxEthAmount, "Insufficient ETH sent");

        uint invariantProduct = tokenReserve * ethReserve;
        uint newTokenReserve = tokenReserve - tokenAmount;
        uint calculatedEthAmount = (invariantProduct - newTokenReserve * ethReserve) * 100 / (newTokenReserve * (100 - exchangeFeePercent));
        if ((invariantProduct - newTokenReserve * ethReserve) * 100 % (newTokenReserve * (100 - exchangeFeePercent)) != 0) {
            calculatedEthAmount++;
        }
        uint ethFee = (calculatedEthAmount * exchangeFeePercent + 99) / 100;

        require(calculatedEthAmount <= maxEthAmount, "Calculated ETH amount exceeds max ETH amount");

        uint tokenFee = (tokenAmount * exchangeFeePercent + 99) / 100;
        tokenReserve = tokenReserve - tokenAmount + tokenFee;
        ethReserve += calculatedEthAmount;

        uint ethRefund = msg.value - calculatedEthAmount;
        if (ethRefund > 0) {
            payable(msg.sender).transfer(ethRefund);
        }

        require(exchangeToken.transfer(msg.sender, tokenAmount - tokenFee), "Token transfer failed");
        emit FeeDetails(calculatedEthAmount, ethFee, tokenFee);

        return (calculatedEthAmount, ethFee, tokenFee);
    }
    /**
     * @dev Swap tokens for ETH
     * Sell `amount` tokens as long as the total price is at least `minPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens
     * (rounded up) *before* selling, and taken from the ETH returned (rounded up) *after* selling.
     * @return Returns a tuple with the actual total value in ETH minus the fee, the eth fee and the token fee.
     */
    function sellTokens(uint amount, uint minPrice) override public returns (uint, uint, uint) {
        require(amount > 0, "Token amount must be greater than 0");
        require(minPrice >= 0, "Min ETH amount must be non-negative");
    
        uint invariantProduct = tokenReserve * ethReserve;
        uint tokenFee = (amount * exchangeFeePercent) / 100;
        uint newTokenReserve = tokenReserve + amount;
        uint newEthReserve = invariantProduct / (newTokenReserve - tokenFee);
        uint ethOut = ethReserve - newEthReserve;
        uint ethFee = (ethOut * exchangeFeePercent) / 100;
    
        uint netEthOut = ethOut - ethFee;
        require(netEthOut >= minPrice, "ETH out is less than min price");
    
        ethReserve = newEthReserve + ethFee;
        tokenReserve = newTokenReserve;
    
        require(exchangeToken.transferFrom(msg.sender, address(this), amount), "Token transfer failed");
    
        payable(msg.sender).transfer(netEthOut);
    
        emit FeeDetails(netEthOut, ethFee, tokenFee);
        return (netEthOut, ethFee, tokenFee);
    }
    
    /**
     * Returns the current number of tokens in the liquidity pool.
     */
    function tokenBalance() external view returns(uint) {
        return tokenReserve;
    }
    
    /**
     * @dev mint `amount` liquidity tokens, as long as the total number of tokens spent is at most `maxTOK`
     * and the total amount of ETH spent is `maxETH`. The token allowance for the exchange address must be at least `maxTOK`,
     * and the msg value at least `maxETH`.
     * Unused funds will be returned to the sender.
     * @return returns a tuple consisting of (token_spent, eth_spent).
     */
    
    function mintLiquidityTokens(uint amount, uint maxTOK, uint maxETH) public payable returns (uint, uint) {
        require(msg.value >= maxETH, "Insufficient ETH sent");
        require(amount > 0, "Share amount must be greater than 0");
        require(msg.value > 0, "Insufficient ETH sent");
        require(exchangeToken.allowance(msg.sender, address(this)) >= maxTOK, "Token allowance too low");
    
        // Calculate the required ETH and tokens for the liquidity shares
        uint requiredEth = (amount * ethReserve + totalLiquidityShares - 1) / totalLiquidityShares;
        uint requiredTokens = (amount * tokenReserve + totalLiquidityShares - 1) / totalLiquidityShares;
    
        // Ensure the required amounts do not exceed the maximum allowed
        require(requiredEth <= maxETH, "Required ETH exceeds max ETH");
        require(requiredTokens <= maxTOK, "Required tokens exceed max token reserve");
    
        // Update user shares and reserves
        userShares[msg.sender] += amount;
        totalLiquidityShares += amount;
        ethReserve += requiredEth;
        tokenReserve += requiredTokens;
    
        // Refund any excess ETH sent
        uint ethRefund = msg.value - requiredEth;
        if (ethRefund > 0) {
            payable(msg.sender).transfer(ethRefund);
        }
        
        // Transfer the required tokens from the user to the contract
        require(exchangeToken.transferFrom(msg.sender, address(this), requiredTokens), "Token transfer failed");
        
        emit MintBurnDetails(requiredTokens, requiredEth);
        return (requiredTokens, requiredEth);
    }
    
    /**
     * @dev burn `amount` liquidity tokens, as long as this will result in at least minTOK tokens and at least minETH eth being generated.
     * The resulting tokens and ETH will be credited to the sender.
     * @return Returns a tuple consisting of (token_credited, eth_credited).
     */
    function burnLiquidityTokens(uint amount, uint minTOK, uint minETH) override public payable returns (uint, uint) {
        require(amount > 0, "Share amount must be greater than 0");
        require(minTOK >= 0, "Min token reserve must be non-negative");
        require(minETH >= 0, "Min ETH reserve must be non-negative");
    
        uint withdrawnEth = (amount * ethReserve + totalLiquidityShares - 1) / totalLiquidityShares;
        require(withdrawnEth >= minETH, "Withdrawn ETH less than min ETH");
    
        uint withdrawnTokens = (amount * tokenReserve + totalLiquidityShares - 1) / totalLiquidityShares;
        require(withdrawnTokens >= minTOK, "Withdrawn tokens less than min token reserve");
    
        userShares[msg.sender] -= amount;
        totalLiquidityShares -= amount;
        ethReserve -= withdrawnEth;
        tokenReserve -= withdrawnTokens;
    
        payable(msg.sender).transfer(withdrawnEth);
        require(exchangeToken.transfer(msg.sender, withdrawnTokens), "Token transfer failed");
        emit MintBurnDetails(withdrawnTokens, withdrawnEth);
    
        return (withdrawnTokens, withdrawnEth);
    }
    
    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256) {
        return totalLiquidityShares;
    }
    
    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address account) public view override returns (uint256) {
        return userShares[account];
    }
    
    /**
     * @dev Moves `amount` tokens from the caller's account to `recipient`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address recipient, uint256 amount) external override returns (bool) {
        address sender = msg.sender;
    
        // Ensure the sender has enough balance to transfer the specified amount
        require(amount <= userShares[sender], "Transfer amount exceeds balance");
    
        // Update the sender's and recipient's shares
        userShares[sender] -= amount;
        userShares[recipient] += amount;
    
        // Emit the Transfer event
        emit Transfer(sender, recipient, amount);
    
        return true;
    }

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view override returns (uint256) {
        return userAllowances[owner][spender];
    }
    /**
     * @dev Sets `amount` as the allowance of `spender` over the caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 amount) external override returns (bool) {
        userAllowances[msg.sender][spender] = amount;

        emit Approval(msg.sender, spender, amount);

        return true;
    }
    
    /**
     * @dev Moves `amount` tokens from `sender` to `recipient` using the
     * allowance mechanism. `amount` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address sender, address recipient, uint256 amount) external override returns (bool) {
        address spender = msg.sender;
    
        require(amount <= userAllowances[sender][spender], "Transfer amount exceeds allowance");
        require(amount <= userShares[sender], "Transfer amount exceeds balance");
    
        // Update the sender's allowance for the spender
        userAllowances[sender][spender] -= amount;
        // Update the sender's and recipient's shares
        userShares[sender] -= amount;
        userShares[recipient] += amount;
    
        // Emit the Transfer event
        emit Transfer(sender, recipient, amount);
    
        return true;
    }

}
