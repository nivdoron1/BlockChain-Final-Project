from typing import Tuple
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from ape import project

RUToken = project.RUToken

grade_multisig = False  # Change this to true if you implemented the multisig token.

keys = KeyAPI(NativeECCBackend)


class Signature:
    def __init__(self, r: bytes, s: bytes, v: int) -> None:
        self.r = r
        self.s = s
        self.v = v

    # Encode as a tuple suitable for passing as solidity calldata.
    def encoded(self) -> Tuple[bytes, bytes, int]:
        return (self.r, self.s,
                self.v + 27)  # Add 27 to v just because Bitcoin developers decided to use an arbitrary number, and the Ethereum developers copied them.


# This function should return a nonce and a signature
# that can be passed to transfer2of3.
# Note: The function should *not* change state in any way (e.g., if you call contract methods, call only `view` and `pure` methods`)).
def generate_nonce_and_second_signature_transfer2of3(tok: RUToken, sk, multisigAddr, spender, amount) -> Tuple[
    int, Signature]:
    key = keys.PrivateKey(bytes.fromhex(sk[2:]))  # Can be used with `keys.ecdsa_sign``

    # TODO: Implement
    return (0, Signature(b'\0', b'\0', 0))  # Change this!
