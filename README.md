
# Final project for Blockchains and Cryptocurrencies Course

## Overview
In this project you will implement an ERC20 Token, and optionally a multisig extension to the token API and/or a Uniswap-like token exchange.
The project will be written in Solidity, with a little bit of python for the client side of the multisig extension. 


## ERC20 Token
This is the main part of the project, in which you will be implementing an ERC20 token. The interface you must implement is in `interfaces/IERC20.sol` (taken from the OpenZeppelin project). 
A skeleton implementation is in `contracts/ru_token.sol`.  

## Multisig Extension
In this part of the project, you will add a "multisig" extension to the ERC20 token. The idea of this extension is to define a new type of "2-out-of-3" multisig address, which are defined by 
*three* public keys. In order to transfer tokens from a multisig address, *two* of the three public-key owners must sign the transfer transaction. 

The Multisig API captures this by adding three functions to the token API. The first two are used to define a multisig address based on the three public keys. 
The multisig address should be defined completely by the three public keys. Given three standard public-key-based addresses `pk1`,`pk2`,`pk3`, the function `getMultisigAddress` 
should return the corresponding multisig address.  Since the multisig address doesn't contain enough information to recover the actual public keys, it must be registered before using it by 
calling `registerMultisigAddress`. 

The most important function is the `transfer2of3` function, which is used to transfer tokens from a multisig address 
(tokens can to transferred *to* a multisig addresss using the standard token functions). This function accepts, in addition to the multisig source address, the destination and the amount to transfer, 
two "special" arguments:

  * `uint nonce` --- this is a nonce value used to prevent "replay" attacks (see below).
  * `Signature calldata secondSig` --- This is a second signature on the transfer transaction (in addition to the transaction sender's signature that's verified implicitly by ethereum). 

The `Signature` type is defined in `IMultisigToken.sol`, as a struct containing three elements: `r`, `s` and `v` (see [here](https://en.bitcoin.it/wiki/Elliptic_Curve_Digital_Signature_Algorithm) for 
information about ECDSA signatures; the `v` element is used to recover the public key from the signature and message).

### Client code
The implementation of the multisig extension also includes implementing client-side code in python that is used to generate the 2-out-of-3 transactions (this can't be done on the blockchain, because it must
involve the secret signing keys).  You must implement the `generate_nonce_and_second_signature_transfer2of3`  function in `scripts/multisig_token.py`. This function accepts a  reference to 
a "live" contract instance `tok`, the secret signing key `sk`, encoded as a hex string with a `0x` prefix (you can convert this into a `PrivateKey` object that can be used by the `keys.ecdsa_sign` function 
by calling `keys.PrivateKey(bytes.fromhex(sk[2:]))`).

This function should return a tuple containing the *nonce* and the *signature* to be used when constructing the `transfer2of3` transaction. 

### Replay attacks
Your multisig token should be resistant to *replay* attacks, in which an honestly-generated transaction is used by an attacker to transfer money that would not be authorized. You should consider
the following types of attacks:

 * Simple replay: sending the same transaction data (i.e., source, destination, amount, and secondSig).
 * Repurposing signature replay: sending modified data, but reusing a previous secondSig.
 * Cross-contract replay: using a signature from one token contract instance to transfer tokens in a different contract instance.
In all of these cases, the transaction should fail.

### Hints
 * One way to define a multisig address based on public keys (securely) is to *hash* the three keys together, for example using the `keccak256` function.
 * Signature verification in solidity is done using the [`ecrecover` function](https://docs.soliditylang.org/en/v0.8.17/solidity-by-example.html#recovering-the-message-signer-in-solidity), that accepts the 
   message hash and the `v`, `r,` and `s` signature parameters and returns the public key corresponding to the signature (every signature and message define *some* public key --- a signature is valid 
   if the recovered public key is the one that's authorized to generate the signature). Note that although the `v` parameter is 0 or 1, solidity's `ecrecover` expects 27 or 28 instead.

### Note
If you choose to implement this part of the project, set `grade_multisig = True` in `scripts/multisig_token.py`. 


## AMM Token Exchance
In this part of the project, you will implenent a Uniswap-like token exchange. The exchange contract only handles trading ERC20 tokens for ETH and back (not tokens for tokens), 
and uses the AMM rule we saw in class: in each swap, the product of the exchange's token blance and ETH balance should remain constant. 
To implement, fill out the skeleton in `contracts/ru_exchange.sol`.

The exchange supports the following operations:

 * Initialization: this can only be done by the sender that deployed the contract. It sets the contract's underlying ERC20 Token, the fee (in percentage of each trade) 
   and the initial supply of tokens and ETH. The initial supply tokens is transferred to the exchange using `transferFrom`, so should be approved by the sender before calling `initialize`.
 * Buying tokens: In this case, the maximum payment amount is given as a parameter --- if more payment is required to buy the given amount of tokens, 
   the transaction should fail.
 * Selling tokens: In this case, the minimum sale price is given as a parameter --- if total sale would result in less than this price, the transaction should fail.
 * Minting liquidity tokens: In this case, the caller should deposit both tokens and ETH in the liquidity pool in return for liquidity tokens. The caller defines the maxmimum amount of tokens/ETH 
   that they are willing to pay for the requested number of liquidity tokens. The amount of tokens/ETH actually paid should maintain
   the existing ratio, and the minted liquidity tokens should reflect the fraction of the total liquidity pool that the newly added tokens/ETH provide.
 * Burning liquidity tokens: In this case, the caller's liquidity tokens are burned (the total supply of liquidity tokens contracts), and the corresponding fraction of the liquidity pool (in both tokens and ETH)
   is returned to the caller. The caller specifies the minimum amount of tokens/ETH for this exchange; below this amount the transaction should fail.
 
In addition to the "exchange-specific" operations, the exchange should support all the standard ERC20 operations when acting as the liquidity token. Thus, it must also implement the `IERC20` interface.

### Fees
When buying an selling tokens, the exchange can charge a fee (if the `feePercent` parameter given to `initialize` is non-zero). In this case, the fee is always taken from both the tokens and 
the ETH involved. When buying, the fee is taken from the ETH paid *before it is traded*, and from the tokens *after the trade occurs*. When selling, the fee is taken from the tokens before the
trade occurs, and from the ETH after the trade. The AMM maintains the constant token/eth product for a trade *before the fees are deposited*. 

For example, if a transaction is selling 2 tokens, and the exchange liquidity consists of 10 tokens and 99 ETH before the transaction is processed, with a fee of 50 percent, the exchange first takes 1 token as fee, then "sells" one token for 9 ETH (this, the product before the transaction is 10x99=990, and after is 11x90 = 990, maintaining the constant). Finally, it takes 5 ETH as a fee (50% of 9, rounded up), and deposits the 5 ETH and 1 token in the liquidity pool. So the exchange ends up with 12 tokens and 95 ETH, and the seller receives 4 ETH. 

The amounts should be as close as possible up to rounding (since the amounts all have to be integers, we allow the constant product invariant to be violated due to rounding errors).

### Note
If you choose to implement this part of the project, set `grade_exchange = True` in `scripts/exchange.py`. 

## Submission Guidelines
* Submission is in pairs.
* Create a git repository for your project on the [course version-control server](https://vcs.ap.runi.ac.il/) by cloning the [project base](https://vcs.ap.runi.ac.il/blockchain/project-base)
  - The name of your repository *must be* ``project-user1-user2``, where ``user1`` and ``user2`` are the usernames of the project participants.

    Note that the project will "belong" to one of the users (you can add the other user as a collaborator)
  - Make sure your repository is private
* Repositories should contain all of the project source code.
* I will run your project by cloning your repository, and running

      docker compose run test

 in the root directory. 
  **Make sure this works** by cloning a clean copy of your project and testing it.
* **Write your own code**. You may talk to fellow students about the project, but **do not copy code**, from them or from the internet. 

## Running Tests and Debugging
The repository you've downloaded is already set up as a [ape](https://docs.apeworx.io/ape/stable/) project, with an extensive series of tests.

If you have python 3 installed and the `python3` binary is in your path, running `setup.sh` should install a python venv with ape. To use it, 
run (on a bash prompt)

    . venv/bin/activate
    ape test

You can also install a python virtual environment in an IDE and use the `requirements.txt` file to install ape.
Once ape is installed, you can compile and test your code by running `ape test` in the project root directly. 

### Alernative network providers
Ape supports different network providers --- that is, different software that will run a local "fake" ethereum node to test against.
By default, this project is configured to use the built-in tester node that doesn't require any additional software. However, this 
provider is limited: in particular, it can't get traces of the actual ethereum contract execution for debugging.

You can change to a different provider by editing the `ape-config.yaml` file. The `ape-foundry` plugin is automatically installed for you
by the `setup.sh` script. In order to use it:
* You need to have an `anvil` local node running. You can run one by running `docker compose up` (this will download and run a 1G+ container image).
* You need to change the `ape-config.yaml` file so that the default network provider is `foundry` rather than `test`. 

### Installing Ape Using Docker
Instead of installing ape locally, you can use the docker compose environment to run tests (this is what we will do for grading, so it's recommended to
check at home as well). To do this:

* Run `docker compose build` in the project root directory
* Run `docker compose up -d` to start the foundry container (this container runs a test ethereum node that listens on port 8545).
* Run `docker compose run ape-console` to get a bash prompt. You can run `ape compile` at the prompt compile your solidity code, `ape test` to run tests, or `ape console` to open a python console.

Running `docker compose run test` will do the same thing as running the `ape-console` service and then `ape test` on the command line.

**Note**: Inside the docker container, ape uses a different configuration file: `ape/ape-config-foundry.yaml`. 


## Grading
The project components will be graded as follows:

* 85 points for the base RUToken implementation.
* 15 points for the first optional extension
* 10 points for the second optional extension

(You can get more than 100 points if you implement both the multisig and the exchange)

Notes:
  * The "multisig extension" includes the client-side python code for generating multisig transactions
  * The automated tests are only part of the grading process --- your code will also be manually inspected. Some errors --- especially security-related ones --- may not be caught by the automated tests. 
In addition to correctness and security, the grade will depend on the clarity of your code. Be sure to document it well.
