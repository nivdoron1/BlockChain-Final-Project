from math import ceil
import pytest

from ape import project, accounts as accts
from hypothesis import given, settings, Phase, strategies as st
from hypothesis.strategies import tuples, sampled_from
from tests.test_tokens import deploy_ru_token, mint_ru_tokens, GenericTokenTest
from scripts.exchange import grade_exchange

from tests.utils import find_event

default_settings = {'max_examples': 20, 'deadline': None, 'derandomize': True, 'phases': (Phase.explicit, Phase.reuse, Phase.generate,)}

RUExchange, RUToken = (project.RUExchange, project.RUToken)

pytestmark = pytest.mark.skipif(not grade_exchange,
                                reason="Exchange not implemented! (Set bonus_multisig_token.grade_bonus = True to allow grading)")

# Globals
default_price = 100
default_xfernum = 200
default_totalmint = default_xfernum * 4
default_maxtok = int(1e15)
default_feepercent = 5

default_initial_tokens = 100
default_initial_eth = 200


def deploy_ru_exchange(account) -> RUExchange:
    exch = RUExchange.deploy(sender=account)
    return exch


def initialize_ru_exchange(exch: RUExchange, tok: RUToken, account, fee: int, initial_tokens: int, initial_eth: int):
    mint_ru_tokens(tok, account, initial_tokens)
    tok.approve(exch, initial_tokens, sender=account)
    tx = exch.initialize(tok, fee, initial_tokens, initial_eth, sender=account, value=initial_eth)
    return tx


@pytest.fixture(autouse=True, scope='class')
def default_setup(request, accounts):
    request.cls.price = default_price
    request.cls.maxtok = default_maxtok
    request.cls.token_account = accounts[0]
    request.cls.feePercent = default_feepercent
    request.cls.initial_tokens = default_initial_tokens
    request.cls.initial_eth = default_initial_eth


class TestExchangeSpecifics:
    def deploy_and_init_exchange(self, owner_account) -> RUExchange:
        exch = deploy_ru_exchange(owner_account)
        rutoken = deploy_ru_token(RUToken, default_price, default_maxtok, self.token_account)
        initialize_ru_exchange(exch, rutoken, owner_account, self.feePercent, self.initial_tokens,
                               self.initial_eth)
        return exch

    def buytoken_testbody(self, accounts, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        buytokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])
        rutoken = RUToken.at(exch.getToken())

        orig_exch_balance = exch.balance
        orig_exch_tokenbalance = exch.tokenBalance()

        orig_tokenbalance = rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance

        tx = exch.buyTokens(buytokens, int(1e7), sender=accounts[1], value=int(1e7))

        feedetails = find_event(tx, 'FeeDetails')
        assert feedetails is not None

        actualPayment, actualEthFee, actualTokenFee = feedetails.get('actualPayment'), feedetails.get('actualEthFee'), feedetails.get('actualTokenFee')

        txfees = tx.total_fees_paid

        exactEthFee = self.feePercent * actualPayment / 100
        exactTokenFee = buytokens * self.feePercent / 100

        assert int(exactEthFee) <= actualEthFee <= ceil(exactEthFee)
        assert int(exactTokenFee) <= actualTokenFee <= ceil(exactTokenFee)

        new_exch_balance = exch.balance
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance

        assert new_tokenbalance == orig_tokenbalance + buytokens - actualTokenFee
        assert new_eth_balance == orig_eth_balance - actualPayment - txfees
        assert new_exch_tokenbalance == orig_exch_tokenbalance - buytokens + actualTokenFee
        assert new_exch_balance == orig_exch_balance + actualPayment

        orig_k = orig_exch_tokenbalance * orig_exch_balance
        new_exch_balance_without_fee = new_exch_balance - actualEthFee
        new_exch_tokenbalance_without_fee = new_exch_tokenbalance - actualTokenFee

        # We tolerate off-by-one errors that can occur due to rounding
        assert new_exch_tokenbalance_without_fee * (
                    new_exch_balance_without_fee - 1) <= orig_k <= new_exch_tokenbalance_without_fee * (
                           new_exch_balance_without_fee + 1)

    def test_simple_buy1token(self, accounts):
        self.buytoken_testbody(accounts, 0, 100, (1, 100))

    @settings(**default_settings)
    @given(
        feepercent=st.integers(min_value=0, max_value=95),
        initial_eth=st.integers(min_value=10, max_value=300),
        # tokens_to_buy, initialsupply
        tokdata=tuples(st.integers(min_value=1, max_value=100), st.integers(min_value=2, max_value=100)).map(
            sorted).filter(lambda x: x[0] < x[1]),
    )
    def test_buytokens(self, accounts, feepercent, initial_eth, tokdata):
        self.buytoken_testbody(accounts, feepercent, initial_eth, tokdata)

    def selltoken_testbody(self, accounts, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        sellTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])
        rutoken = RUToken.at(exch.getToken())

        orig_exch_balance = exch.balance
        orig_exch_tokenbalance = exch.tokenBalance()

        tokenprice = rutoken.tokenPrice()
        rutoken.mint(sender=accounts[1], value=sellTokens * tokenprice)

        orig_tokenbalance = rutoken.balanceOf(accounts[1])
        assert orig_tokenbalance >= sellTokens

        orig_eth_balance = accounts[1].balance

        tx0 = rutoken.approve(exch, sellTokens, sender=accounts[1])
        tx1 = exch.sellTokens(sellTokens, 0, sender=accounts[1])


        feedetails = find_event(tx1, 'FeeDetails')
        assert feedetails is not None

        actualPayment, actualEthFee, actualTokenFee = feedetails.get('actualPayment'), feedetails.get('actualEthFee'), feedetails.get('actualTokenFee')

        txfees = tx0.total_fees_paid + tx1.total_fees_paid

        exactEthFee = self.feePercent * (actualPayment + actualEthFee) / 100
        exactTokenFee = sellTokens * self.feePercent / 100

        assert int(exactEthFee) <= actualEthFee <= ceil(exactEthFee)
        assert int(exactTokenFee) <= actualTokenFee <= ceil(exactTokenFee)

        new_exch_balance = exch.balance
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance

        assert new_eth_balance == orig_eth_balance + actualPayment - txfees
        assert new_tokenbalance == orig_tokenbalance - sellTokens
        assert new_exch_tokenbalance == orig_exch_tokenbalance + sellTokens
        assert new_exch_balance == orig_exch_balance - actualPayment

        orig_k = orig_exch_tokenbalance * orig_exch_balance
        new_exch_balance_without_fee = new_exch_balance - actualEthFee
        new_exch_tokenbalance_without_fee = new_exch_tokenbalance - actualTokenFee

        # We tolerate off-by-one errors that can occur due to rounding
        assert new_exch_tokenbalance_without_fee * (
                    new_exch_balance_without_fee - 1) <= orig_k <= new_exch_tokenbalance_without_fee * (
                           new_exch_balance_without_fee + 1)

    def test_simple_sell1token(self, accounts):
        self.selltoken_testbody(accounts, 0, 10, (1, 10))

    @settings(**default_settings)
    @given(
        feepercent=st.integers(min_value=0, max_value=95),
        initial_eth=st.integers(min_value=10, max_value=300),
        # tokens_to_sell, initialsupply
        tokdata=tuples(st.integers(min_value=1, max_value=100), st.integers(min_value=1, max_value=100))
    )
    def test_selltokens(self, accounts, feepercent, initial_eth, tokdata):
        self.selltoken_testbody(accounts, feepercent, initial_eth, tokdata)

    def mintliquidity_testbody(self, accounts, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        mintTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])
        rutoken = RUToken.at(exch.getToken())

        orig_exch_balance = exch.balance

        rutoken.mint(sender=accounts[1], value=int(1e6))

        orig_tokenbalance = rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance
        orig_exch_tokenbalance = exch.tokenBalance()

        orig_lqt_balance = exch.balanceOf(accounts[1])

        tx0 = rutoken.approve(exch, int(1e6), sender=accounts[1])
        tx1 = exch.mintLiquidityTokens(mintTokens, int(1e6), int(1e6), sender=accounts[1], value=int(1e6))
        print(tx1)
        mintburndetails = find_event(tx1, 'MintBurnDetails')
        assert mintburndetails is not None

        numTOK, numETH = mintburndetails.get('numTOK'), mintburndetails.get('numETH')

        txfees = tx0.total_fees_paid + tx1.total_fees_paid

        new_exch_balance = exch.balance
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance
        new_lqt_balance = exch.balanceOf(accounts[1])

        assert new_lqt_balance == orig_lqt_balance + mintTokens
        assert new_exch_balance == orig_exch_balance + numETH
        assert new_exch_tokenbalance == orig_exch_tokenbalance + numTOK
        assert new_eth_balance == orig_eth_balance - numETH - txfees
        assert new_tokenbalance == orig_tokenbalance - numTOK

        newTotalLQT = exch.totalSupply()
        lqtFraction = mintTokens / newTotalLQT

        assert int(new_exch_tokenbalance * lqtFraction) <= numTOK <= ceil(new_exch_tokenbalance * lqtFraction)
        assert int(new_exch_balance * lqtFraction) <= numETH <= ceil(new_exch_balance * lqtFraction)

    def test_simple_mint1token(self, accounts):
        self.mintliquidity_testbody(accounts, 0, 10, (1, 10))

    @settings(**default_settings)
    @given(
        feepercent=st.integers(min_value=0, max_value=95),
        initial_eth=st.integers(min_value=10, max_value=300),
        # tokens_to_mint, initialsupply
        tokdata=tuples(st.integers(min_value=1, max_value=100), st.integers(min_value=1, max_value=100))
    )
    def test_mintliquidity(self, accounts, feepercent, initial_eth, tokdata):
        self.mintliquidity_testbody(accounts, feepercent, initial_eth, tokdata)

    def burnliquidity_testbody(self, accounts, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        burnTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[1])
        rutoken = RUToken.at(exch.getToken())

        orig_exch_balance = exch.balance
        orig_tokenbalance = rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance
        orig_exch_tokenbalance = exch.tokenBalance()
        orig_lqt_balance = exch.balanceOf(accounts[1])

        orig_totalLQT = exch.totalSupply()
        lqtFraction = burnTokens / orig_totalLQT

        tx = exch.burnLiquidityTokens(burnTokens, 0, 0, sender=accounts[1])

        mintburndetails = find_event(tx, 'MintBurnDetails')
        assert mintburndetails is not None

        numTOK, numETH = mintburndetails.get('numTOK'), mintburndetails.get('numETH')

        txfees = tx.total_fees_paid

        new_exch_balance = exch.balance
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance
        new_lqt_balance = exch.balanceOf(accounts[1])

        assert new_lqt_balance == orig_lqt_balance - burnTokens
        assert new_exch_balance == orig_exch_balance - numETH
        assert new_exch_tokenbalance == orig_exch_tokenbalance - numTOK
        assert new_eth_balance == orig_eth_balance + numETH - txfees
        assert new_tokenbalance == orig_tokenbalance + numTOK

        assert int(orig_exch_tokenbalance * lqtFraction) <= numTOK <= ceil(orig_exch_tokenbalance * lqtFraction)
        assert int(orig_exch_balance * lqtFraction) <= numETH <= ceil(orig_exch_balance * lqtFraction)

    def test_simple_burn1token(self, accounts):
        self.mintliquidity_testbody(accounts, 0, 10, (1, 10))


    @settings(**default_settings)
    @given(
        feepercent=st.integers(min_value=0, max_value=95),
        initial_eth=st.integers(min_value=10, max_value=300),
        # tokens_to_burn, initialsupply
        tokdata=tuples(st.integers(min_value=1, max_value=100), st.integers(min_value=2, max_value=100)).map(
            sorted).filter(lambda x: x[0] < x[1]),
    )
    def test_burnliquidity(self, accounts, feepercent, initial_eth, tokdata):
        self.burnliquidity_testbody(accounts, feepercent, initial_eth, tokdata)


class TestExchangeAsToken(GenericTokenTest):
    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        # newacct = accounts.add()
        rutok = deploy_ru_token(RUToken, default_price, default_maxtok, account)
        exch = deploy_ru_exchange(account)
        initialize_ru_exchange(exch, rutok, account, self.feePercent, self.initial_tokens, self.initial_eth)
        return exch

    # Must override this function
    # returns a transaction receipt.
    def mint_funds(self, exch: RUExchange, account, amount):
        curSupply = exch.totalSupply()
        curTok = exch.tokenBalance()
        curEth = exch.balance

        rutoken = RUToken.at(exch.getToken())
        orig_lqt_balance = exch.balanceOf(account)
        orig_rutok_balance = rutoken.balanceOf(account)

        mint_ru_tokens(rutoken, account, int(1e6))
        rutoken.approve(exch, int(1e6), sender=account)
        tx = exch.mintLiquidityTokens(amount, int(1e6), int(1e6), sender=account, value=int(1e6))

        assert exch.balanceOf(account) == orig_lqt_balance + amount
        new_tokenbalance = rutoken.balanceOf(account)
        rutoken.burn(new_tokenbalance - orig_rutok_balance, sender=account)
        return tx
