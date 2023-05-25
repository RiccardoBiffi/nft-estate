from web3 import Web3
import pytest
from brownie import (
    BrickToken,
    MockERC20,
    MockDAI,
    MockWETH,
    AllowTokens,
    TokenValue,
    MockV3Aggregator,
    OrderBook,
)
from scripts.utilities import get_account


@pytest.fixture
def amount():
    return Web3.toWei(10, "ether")


@pytest.fixture
def dai_amount():
    return Web3.toWei(100, "ether")


@pytest.fixture
def eth_amount():
    return Web3.toWei(100, "ether")


@pytest.fixture
def supply():
    return Web3.toWei(1000000, "ether")


@pytest.fixture
def decimals():
    return 18


@pytest.fixture
def account():
    return get_account()


@pytest.fixture
def allow_tokens(account):
    return AllowTokens.deploy({"from": account})


@pytest.fixture
def token_value(account):
    return TokenValue.deploy({"from": account})


@pytest.fixture
def brick_token(
    supply, dai, dai_amount, token_value_DAI, eth, eth_amount, token_value_ETH, account
):
    bt = BrickToken.deploy(supply, {"from": account})
    bt.approve(bt.address, supply, {"from": account})
    dai.approve(bt.address, dai_amount, {"from": account})
    eth.approve(bt.address, eth_amount, {"from": account})
    bt.addAllowedToken(bt.address, {"from": account})
    bt.addAllowedToken(dai.address, {"from": account})
    bt.addAllowedToken(eth.address, {"from": account})
    bt.setTokenPriceFeed(bt.address, token_value_DAI, {"from": account})
    bt.setTokenPriceFeed(dai.address, token_value_DAI, {"from": account})
    bt.setTokenPriceFeed(eth.address, token_value_ETH, {"from": account})
    return bt


# region DAI
@pytest.fixture
def dai(dai_amount, account):
    mock_dai = MockDAI.deploy({"from": account})
    mock_dai.mint(dai_amount, {"from": account})
    return mock_dai


@pytest.fixture
def DAI_price(decimals):
    return 1 * 10**decimals


@pytest.fixture
def token_value_DAI(DAI_price, decimals, account):
    return MockV3Aggregator.deploy(decimals, DAI_price, {"from": account})


# endregion


# region WETH
@pytest.fixture
def eth(eth_amount, account):
    mock_eth = MockWETH.deploy({"from": account})
    mock_eth.mint(eth_amount, {"from": account})
    return mock_eth


@pytest.fixture
def ETH_price(decimals):
    return 1560 * 10**decimals


@pytest.fixture
def token_value_ETH(ETH_price, decimals, account):
    return MockV3Aggregator.deploy(decimals, ETH_price, {"from": account})


# endregion


@pytest.fixture
def token():
    return "0x345f9bFd2468f56CcCCb961c29Cf2a454E0812Cd"


# region OrderBook
@pytest.fixture
def book_token(supply, account):
    mock_erc20 = MockERC20.deploy("Book Token", "BOOK", {"from": account})
    mock_erc20.mint(account, supply, {"from": account})
    mock_erc20.approve(mock_erc20.address, supply, {"from": account})
    return mock_erc20


@pytest.fixture
def price_token(supply, account):
    mock_erc20 = MockERC20.deploy("Price Token", "PRICE", {"from": account})
    mock_erc20.mint(account, supply, {"from": account})
    return mock_erc20


@pytest.fixture
def order_book(book_token, price_token, supply, account):
    order_book = OrderBook.deploy(book_token, price_token, {"from": account})
    book_token.approve(order_book.address, supply, {"from": account})
    price_token.approve(order_book.address, supply, {"from": account})
    return order_book


# endregion
