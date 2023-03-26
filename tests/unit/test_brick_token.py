from brownie import network, exceptions
from brownie import BrickToken
import brownie
import pytest
from scripts.utilities import get_account, LOCAL_BLOCKCHAIN_ENVIRONMENTS


def test_can_deploy_contract():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    account = get_account()
    total_supply = 1_000_000 * 10**18

    # Act
    bt = BrickToken.deploy(total_supply, {"from": account})

    # Assert
    assert bt.name() == "Coincrete"
    assert bt.symbol() == "BRICK"
    assert bt.decimals() == 18
    assert bt.totalSupply() == total_supply
    assert bt.companyBrick() == (total_supply * 8) / 10
    assert bt.buyableTokens() == (total_supply - bt.companyBrick()) / 2
    assert bt.aprBrick() == total_supply - bt.companyBrick() - bt.buyableTokens()
    assert bt.sellSpread() == 2000
    assert bt.balanceOf(bt.address) == bt.buyableTokens() + bt.aprBrick()
    assert bt.balanceOf(account) == bt.companyBrick()


# region buy


def test_buy_success(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    initial_supply = brick_token.balanceOf(brick_token.address, {"from": account})
    account_initial_balance = brick_token.balanceOf(account)
    old_buyable_tokens = brick_token.buyableTokens()

    # Act
    tx = brick_token.buy(amount, dai.address, {"from": account})

    # Assert
    assert dai.balanceOf(account) == 0
    assert dai.balanceOf(brick_token.address) == amount
    assert brick_token.tokenWithDeposits(0) == dai.address
    assert brick_token.token_deposit(dai.address) == amount
    assert brick_token.balanceOf(brick_token.address) == initial_supply - amount
    assert brick_token.balanceOf(account) == amount + account_initial_balance
    assert brick_token.buyableTokens() == old_buyable_tokens - amount
    assert tx.events["Bought"]["from"] == account
    assert tx.events["Bought"]["exchangeToken"] == dai.address
    assert tx.events["Bought"]["amountIn"] == amount
    assert tx.events["Bought"]["amountOut"] == amount


def test_buy_success_double_buy(brick_token, dai, amount, token_value_DAI, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    initial_supply = brick_token.balanceOf(brick_token.address, {"from": account})
    account_initial_balance = brick_token.balanceOf(account)
    old_buyable_tokens = brick_token.buyableTokens()
    half_amount = amount / 2

    # Act
    brick_token.buy(half_amount, dai.address, {"from": account})
    tx = brick_token.buy(half_amount, dai.address, {"from": account})

    # Assert
    assert dai.balanceOf(account) == 0
    assert dai.balanceOf(brick_token.address) == amount
    assert brick_token.tokenWithDeposits(0) == dai.address
    assert brick_token.token_deposit(dai.address) == amount
    assert brick_token.balanceOf(brick_token.address) == initial_supply - amount
    assert brick_token.balanceOf(account) == amount + account_initial_balance
    assert brick_token.buyableTokens() == old_buyable_tokens - amount
    assert tx.events["Bought"]["from"] == account
    assert tx.events["Bought"]["exchangeToken"] == dai.address
    assert tx.events["Bought"]["amountIn"] == half_amount
    assert tx.events["Bought"]["amountOut"] == half_amount


# todo finish tests from here on
def test_buy_fail_token_not_allowed(bet_token, token, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Cannot buy BET with this token"):
        bet_token.buy(amount, token, {"from": account})


def test_buy_fail_amount_is_zero(bet_token, dai, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be more than 0 tokens"):
        bet_token.buy(0, dai.address, {"from": account})


def test_buy_fail_allowance_not_approved(bet_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    dai.approve(bet_token.address, 0, {"from": account})

    # Act

    # Assert
    with brownie.reverts(""):
        bet_token.buy(amount, dai.address, {"from": account})


# endregion

# region cashout


def test_cashout_success(bet_token, dai, amount, token_value_DAI, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bet_token.buy(amount, dai.address, {"from": account})

    # Act
    tx = bet_token.cashOut({"from": account})

    # Assert
    assert dai.balanceOf(account) == amount
    assert dai.balanceOf(bet_token.address) == 0
    # hack check for empty array
    with pytest.raises(exceptions.VirtualMachineError):
        assert bet_token.tokenWithDeposits(0)
    assert bet_token.token_deposit(dai.address) == 0
    assert tx.events["CashOut"]["admin"] == account


def test_cashout_fail_not_owner(bet_token, dai, amount, token_value_DAI, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bet_token.buy(amount, dai.address, {"from": account})
    not_owner = get_account(1)

    # Act

    # Assert
    with brownie.reverts():
        bet_token.cashOut({"from": not_owner})


# endregion
