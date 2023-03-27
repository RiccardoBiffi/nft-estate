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
    assert bt.sellSpread() == 2500
    assert bt.balanceOf(bt.address) == bt.buyableTokens() + bt.aprBrick()
    assert bt.balanceOf(account) == bt.companyBrick()


# region buy
def test_buy_success(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    initial_supply = brick_token.balanceOf(brick_token.address, {"from": account})
    account_initial_balance = brick_token.balanceOf(account)
    old_dai_balance = dai.balanceOf(account)
    old_buyable_tokens = brick_token.buyableTokens()

    # Act
    tx = brick_token.buy(amount, dai.address, {"from": account})

    # Assert
    assert dai.balanceOf(account) == old_dai_balance - amount
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


def test_buy_success_double_buy(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    initial_supply = brick_token.balanceOf(brick_token.address, {"from": account})
    account_initial_balance = brick_token.balanceOf(account)
    old_dai_balance = dai.balanceOf(account)
    old_buyable_tokens = brick_token.buyableTokens()

    # Act
    brick_token.buy(amount, dai.address, {"from": account})
    tx = brick_token.buy(amount, dai.address, {"from": account})

    # Assert
    assert dai.balanceOf(account) == old_dai_balance - (amount * 2)
    assert dai.balanceOf(brick_token.address) == amount * 2
    assert brick_token.tokenWithDeposits(0) == dai.address
    assert brick_token.token_deposit(dai.address) == amount * 2
    assert brick_token.balanceOf(brick_token.address) == initial_supply - (amount * 2)
    assert brick_token.balanceOf(account) == (amount * 2) + account_initial_balance
    assert brick_token.buyableTokens() == old_buyable_tokens - (amount * 2)
    assert tx.events["Bought"]["from"] == account
    assert tx.events["Bought"]["exchangeToken"] == dai.address
    assert tx.events["Bought"]["amountIn"] == amount
    assert tx.events["Bought"]["amountOut"] == amount


def test_buy_fail_amount_is_not_enought(brick_token, dai, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount bought must be more than 10$"):
        brick_token.buy(0, dai.address, {"from": account})


def test_buy_fail_token_not_allowed(brick_token, token, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Cannot buy with this token"):
        brick_token.buy(amount, token, {"from": account})


def test_buy_fail_not_enought_available_tokens(brick_token, dai, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be lower than available tokens"):
        brick_token.buy(supply, dai, {"from": account})


def test_buy_fail_allowance_not_approved(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    dai.approve(brick_token.address, 0, {"from": account})

    # Act

    # Assert
    with brownie.reverts(""):
        brick_token.buy(amount, dai.address, {"from": account})


# endregion

# region cashout
def test_cashout_success(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    old_dai_balance = dai.balanceOf(account)
    brick_token.buy(amount, dai.address, {"from": account})

    # Act
    tx = brick_token.cashOut({"from": account})

    # Assert
    assert dai.balanceOf(account) == old_dai_balance
    assert dai.balanceOf(brick_token.address) == 0
    with pytest.raises(exceptions.VirtualMachineError):
        assert brick_token.tokenWithDeposits(0)
    assert brick_token.token_deposit(dai.address) == 0
    assert tx.events["CashedOut"]["admin"] == account


def test_cashout_fail_not_owner(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    brick_token.buy(amount, dai.address, {"from": account})
    not_owner = get_account(1)

    # Act

    # Assert
    with brownie.reverts("Ownable: caller is not the owner"):
        brick_token.cashOut({"from": not_owner})


# endregion

# region sell

def test_sell_success(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    brick_token.buy(amount, dai.address, {"from": account})
    old_dai_balance = dai.balanceOf(account)
    old_brick_balance = brick_token.balanceOf(account)

    # Act
    tx = brick_token.sell(amount, dai.address {"from": account})

    # Assert
    assert dai.balanceOf(account) == old_dai_balance + amount
    assert dai.balanceOf(brick_token.address) == 0
    with pytest.raises(exceptions.VirtualMachineError):
        assert brick_token.tokenWithDeposits(0)
    assert brick_token.token_deposit(dai.address) == 0
    assert brick_token.balanceOf(account) == old_brick_balance - amount
    assert tx.events["Sold"]["from"] == account
    assert tx.events["Sold"]["amountIn"] == amount
    assert tx.events["Sold"]["exchangeToken"] == dai.address
    assert tx.events["Sold"]["amountOut"] == amount

# endregion