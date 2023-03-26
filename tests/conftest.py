from web3 import Web3
import pytest
from brownie import (
    BrickToken,
    MockDAI,
    MockWETH,
    AllowTokens,
    TokenValue,
    MockV3Aggregator,
)
from scripts.utilities import get_account


@pytest.fixture
def amount():
    return Web3.toWei(1, "ether")


@pytest.fixture
def supply():
    return Web3.toWei(1000, "ether")


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
def brick_token(supply, dai, amount, token_value_DAI, account):
    bt = BrickToken.deploy(supply, {"from": account})
    bt.approve(bt.address, supply, {"from": account})
    dai.approve(bt.address, amount, {"from": account})
    bt.addAllowedToken(dai.address, {"from": account})
    bt.addAllowedToken(bt.address, {"from": account})
    bt.setTokenPriceFeed(dai.address, token_value_DAI, {"from": account})
    bt.setTokenPriceFeed(bt.address, token_value_DAI, {"from": account})
    return bt


# region DAI
@pytest.fixture
def dai(amount, account):
    mock_dai = MockDAI.deploy({"from": account})
    mock_dai.mint(amount, {"from": account})
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
def eth(amount, account):
    mock_eth = MockWETH.deploy({"from": account})
    mock_eth.mint(amount, {"from": account})
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
