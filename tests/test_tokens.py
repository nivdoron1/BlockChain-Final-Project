import pytest

import ape
from ape import accounts as accts, chain
from hypothesis import given, assume, settings, Phase, strategies as st
from hypothesis.strategies import sampled_from

from tests.utils import find_event

default_settings = {'max_examples': 20, 'deadline': None, 'derandomize': True, 'phases': (Phase.explicit, Phase.reuse, Phase.generate,)}

default_source_account = accts.test_accounts[11]


def transfer_direct(tok, src, dst, sender, amount):
    return tok.transfer(dst, amount, sender=sender)


def transfer_byproxy(tok, src, dst, sender, amount):
    return tok.transferFrom(src, dst, amount, sender=sender)


def checkSuccessfulTransfer(accounts, tok, src, dst, sender, amount, transferFunc):
    orig_token_balance = tok.balanceOf(dst, sender=accounts[0])

    tx = transferFunc(tok, src, dst, sender, amount)

    new_token_balance = tok.balanceOf(dst, sender=accounts[0])

    if src != dst:
        assert new_token_balance == orig_token_balance + amount
    else:
        assert new_token_balance == orig_token_balance


    txevent = find_event(tx, 'Transfer')
    assert txevent is not None  # Check that the Transfer event was produced
    assert txevent.get('value') == amount
    if type(src) == str:
        assert txevent.get('from') == src
    else:
        assert txevent.get('from') == src.address
    if type(dst) == str:
        assert txevent.get('to') == dst
    else:
        assert txevent.get('to') == dst.address


def checkFailedTransfer(tok, src, dst, sender, amount, transferFunc):
    with ape.reverts():
        tx = transferFunc(tok, src, dst, sender, amount)


class GenericTokenTest:

    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        return None

        # Must override this function

    # returns a transaction receipt.
    def mint_funds(self, tok, account, amount):
        return None

    def deploy_and_mint(self, accounts, mintamount: int, mintaccount, tokaccount=None):
        if tokaccount is None:
            tokaccount = default_source_account
            accounts[0].transfer(tokaccount, int(1e20))  # Give an initial balance
        tok = self.deploy_tok(tokaccount)
        orig_tok = tok.balanceOf(mintaccount)
        tx = self.mint_funds(tok, mintaccount, mintamount)
        assert tok.balanceOf(mintaccount) == orig_tok + mintamount
        return tok

    # Test that a simple deployment works.
    def test_simple_deploy(self, accounts):
        tok = self.deploy_tok(accounts[0])

    def simple_transfer_testbody(self, accounts, txnum: int, extranum: int, a1, a2):
        assume(a1 != a2)
        totalmint = txnum + extranum

        # if a1 == a2:
        #     return # Transfer must be between different accounts.

        tok = self.deploy_and_mint(accounts, totalmint, a1)
        checkSuccessfulTransfer(accounts, tok, a1, a2, a1, txnum, transfer_direct)

    # Test simple transfer between two accounts.
    @settings(**default_settings)
    @given(
        txnum=st.integers(min_value=0, max_value=100),
        extranum=st.integers(min_value=1, max_value=100),
        a1=sampled_from(accts.test_accounts[0:5]),
        a2=sampled_from(accts.test_accounts[0:5]),
    )
    def test_simple_transfer(self, accounts, txnum, extranum, a1, a2):
        self.simple_transfer_testbody(accounts, txnum, extranum, a1, a2)

    # Test successful zero transfer between two accounts.
    def test_zero_transfer(self, accounts):
        self.simple_transfer_testbody(accounts, 0, 10, accounts[1], accounts[2])

    # Test failed transfer between two accounts.
    def test_insufficent_funds_transfer(self, accounts):
        totalmint = 500
        a1 = accounts[1]
        a2 = accounts[2]

        tok = self.deploy_and_mint(accounts, totalmint, a1)
        a1balance = tok.balanceOf(a1)

        checkFailedTransfer(tok, a1, a2, a1, a1balance + 1, transfer_direct)

    def deploy_mint_approve(self, accounts, totalmint: int, approveamount: int, a1, a2) -> ape.Contract:
        tok = self.deploy_and_mint(accounts, totalmint, a1)

        assert tok.balanceOf(a1) == totalmint

        orig_allowance = tok.allowance(a1, a2)
        assert orig_allowance == 0

        tx = tok.approve(a2, approveamount, sender=a1)
        assert tx.return_value == True
        txevent = find_event(tx, 'Approval')
        assert txevent is not None
        assert txevent.get('owner') == a1.address
        assert txevent.get('spender') == a2.address
        assert txevent.get('value') == approveamount

        new_allowance = tok.allowance(a1, a2)
        assert new_allowance == approveamount

        return tok

    def test_approve_transferFrom(self, accounts):
        totalmint = 500
        approveamount = 200
        transferamount = 100

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(accounts, tok, a1, a3, a2, transferamount, transfer_byproxy)

    def test_approve_multiple_transferFrom(self, accounts):
        transferamount = 100
        totalmint = transferamount * 4
        approveamount = totalmint + 10

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(accounts, tok, a1, a3, a2, transferamount, transfer_byproxy)
        checkSuccessfulTransfer(accounts, tok, a1, a3, a2, transferamount * 2, transfer_byproxy)
        checkSuccessfulTransfer(accounts, tok, a1, a3, a2, transferamount - 10, transfer_byproxy)

    def test_notapproved_transferFrom(self, accounts):
        totalmint = 500
        approveamount = 200
        transferamount = 100

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]
        a4 = accounts[4]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a4, transferamount, transfer_byproxy)

    def test_insufficient_allowance_transferFrom(self, accounts):
        totalmint = 500
        approveamount = 200

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a2, approveamount + 1, transfer_byproxy)

    def test_insufficient_allowance_multiple_transferFrom(self, accounts):
        totalmint = 500
        approveamount = 200

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(accounts, tok, a1, a3, a2, approveamount - 10, transfer_byproxy)
        checkFailedTransfer(tok, a1, a3, a2, 15, transfer_byproxy)

    def test_insufficient_funds_transferFrom(self, accounts):
        totalmint = 500
        approveamount = 600

        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(accounts, totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a2, approveamount, transfer_byproxy)


@pytest.fixture(autouse=True, scope='class')
def default_setup(request, project, chain):
    request.cls.price = 10
    request.cls.maxtok = int(1e6)
    request.cls.RUToken = project.RUToken


def deploy_ru_token(contract, price, maxtok, account):
    return contract.deploy(price, maxtok, sender=account)


def mint_ru_tokens(tok, account, amount):
    price = tok.tokenPrice()
    return tok.mint(sender=account, value=amount * price)


class TestRUToken(GenericTokenTest):

    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        return deploy_ru_token(self.RUToken, self.price, self.maxtok, account)

    # Must override this function
    # returns a transaction receipt.
    def mint_funds(self, tok, account, amount):
        return mint_ru_tokens(tok, account, amount)

    # Test mint-burn sequence from single address
    @settings(**default_settings)
    @given(
        price=sampled_from([100, 3, 22]),
        txnum=st.integers(min_value=1, max_value=100),
        extranum=st.integers(min_value=0, max_value=100),
    )
    def test_mint_burn(self, accounts, price, txnum, extranum):
        self.price = price
        totalmint = txnum + extranum
        self.maxtok = totalmint

        a1 = accounts[1]

        tok = self.deploy_tok(accounts[0])
        tx1 = self.mint_funds(tok, a1, totalmint)

        orig_eth_balance = a1.balance
        tx2 = tok.burn(txnum, sender=a1)
        new_token_balance = tok.balanceOf(a1, sender=accounts[0])
        new_eth_balance = a1.balance
        tx2gas = tx2.gas_price * tx2.gas_used
        assert new_token_balance == extranum
        assert new_eth_balance == orig_eth_balance + txnum * price - tx2gas

    # Test mint-burn-insufficient
    @settings(**default_settings)
    @given(
        price=sampled_from([100, 3, 22]),
        maxtok=st.integers(min_value=1, max_value=100),
    )
    def test_mint_burn_insufficient(self, accounts, price, maxtok):
        self.price = price
        self.maxtok = maxtok
        maxnum = 1000

        a1 = accounts[1]

        tok = self.deploy_tok(a1)
        tx1 = self.mint_funds(tok, a1, maxtok)

        orig_eth_balance = a1.balance
        with ape.reverts():
            tx2 = tok.burn(maxtok + 1, sender=a1)

    # Test mint-transfer-burn sequence.
    @settings(**default_settings)
    @given(
        price=sampled_from([100, 3, 22]),
        txnum=st.integers(min_value=1, max_value=100),
        extranum=st.integers(min_value=0, max_value=100),
    )
    def test_mint_transfer_burn(self, accounts, price, txnum, extranum):
        self.price = price
        self.maxtok = 1000

        a1 = accounts[1]
        a2 = accounts[2]

        totalmint = txnum + extranum

        if a1 == a2:
            return  # Transfer must be between different accounts.

        tok = self.deploy_tok(accounts[0])
        tx1 = self.mint_funds(tok, a1, totalmint)
        checkSuccessfulTransfer(accounts, tok, a1, a2, a1, txnum, transfer_direct)

        orig_eth_balance = a2.balance
        tx3 = tok.burn(txnum, sender=a2)
        new_token_balance = tok.balanceOf(a2, sender=accounts[0])
        new_eth_balance = a2.balance
        tx3gas = tx3.gas_price * tx3.gas_used
        assert new_token_balance == 0
        assert new_eth_balance == orig_eth_balance + txnum * price - tx3gas

    # Test that a single minting call works
    @settings(**default_settings)
    @given(
        price=st.integers(min_value=1, max_value=1000),
        num=st.integers(min_value=1, max_value=100),
        to=sampled_from(accts.test_accounts[0:5]),
    )
    def test_single_mint(self, accounts, price, num, to):
        self.price = price
        self.maxtok = 100
        tok = self.deploy_tok(accounts[0])
        orig_supply = tok.totalSupply()
        assert orig_supply == 0

        orig_token_balance = tok.balanceOf(to, sender=accounts[0])
        orig_eth_balance = to.balance
        assert orig_token_balance == 0

        tx = self.mint_funds(tok, to, num)

        new_supply = tok.totalSupply()
        assert new_supply == num

        new_token_balance = tok.balanceOf(to, sender=accounts[0])
        new_eth_balance = to.balance
        assert new_token_balance == num
        assert new_eth_balance <= orig_eth_balance - price * num

    # Check that the maximum token amount is observed
    def test_max_mint_single(self, accounts):
        self.price = 100
        self.maxtok = 10
        to = accounts[1]

        tok = self.deploy_tok(accounts[0])
        with ape.reverts():
            tx = tok.mint(sender=to, value=self.price * (self.maxtok + 1))

    # Check that maximum token amount is observed when minting in two phases
    def test_max_mint_double_same(self, accounts):
        self.price = 100
        self.maxtok = 10
        to = accounts[1]

        tok = self.deploy_and_mint(accounts, self.maxtok, to)

        with ape.reverts():
            tx = self.mint_funds(tok, to, 1)

    # Check that maximum token amount is observed when minting in two phases with different addresses.
    def test_max_mint_double_different(self, accounts):
        self.price = 100
        self.maxtok = 10
        to1 = accounts[1]
        to2 = accounts[2]

        tok = self.deploy_and_mint(accounts, self.maxtok, to1)

        with ape.reverts():
            tx = self.mint_funds(tok, to2, 1)
