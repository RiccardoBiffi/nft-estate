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
def test_buy_success_dai(brick_token, dai, amount, account):
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


def test_buy_success_eth(brick_token, eth, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    initial_supply = brick_token.balanceOf(brick_token.address, {"from": account})
    account_initial_balance = brick_token.balanceOf(account)
    old_dai_balance = eth.balanceOf(account)
    old_buyable_tokens = brick_token.buyableTokens()

    # Act
    tx = brick_token.buy(amount, eth.address, {"from": account})

    # Assert
    assert eth.balanceOf(account) == old_dai_balance - amount
    assert eth.balanceOf(brick_token.address) == amount
    assert brick_token.tokenWithDeposits(0) == eth.address
    assert brick_token.token_deposit(eth.address) == amount
    assert (
        brick_token.balanceOf(brick_token.address)
        == initial_supply - tx.events["Bought"]["amountOut"]
    )
    assert (
        brick_token.balanceOf(account)
        == account_initial_balance + tx.events["Bought"]["amountOut"]
    )
    assert (
        brick_token.buyableTokens()
        == old_buyable_tokens - tx.events["Bought"]["amountOut"]
    )
    assert tx.events["Bought"]["from"] == account
    assert tx.events["Bought"]["exchangeToken"] == eth.address
    assert tx.events["Bought"]["amountIn"] == amount
    assert tx.events["Bought"]["amountOut"] == amount * 1560


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


def test_sell_success_dai(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    brick_token.buy(amount, dai.address, {"from": account})
    old_buyable_tokens = brick_token.buyableTokens()
    old_dai_balance = dai.balanceOf(account)
    old_contract_dai_balance = dai.balanceOf(brick_token.address)
    old_brick_balance = brick_token.balanceOf(account)
    amount_sold = amount * 75 // 100

    # Act
    tx = brick_token.sell(amount, dai.address, {"from": account})

    # Assert
    assert dai.balanceOf(account) == old_dai_balance + amount_sold
    assert dai.balanceOf(brick_token.address) == old_contract_dai_balance - amount_sold
    assert (
        brick_token.token_deposit(dai.address) == old_contract_dai_balance - amount_sold
    )
    assert brick_token.buyableTokens() == old_buyable_tokens + amount
    assert brick_token.balanceOf(account) == old_brick_balance - amount
    assert brick_token.tokenWithDeposits(0) == dai.address
    assert brick_token.token_deposit(dai.address) == amount - amount_sold
    assert tx.events["Sold"]["from"] == account
    assert tx.events["Sold"]["amountIn"] == amount_sold
    assert tx.events["Sold"]["exchangeToken"] == dai.address
    assert tx.events["Sold"]["amountOut"] == amount_sold


def test_sell_success_eth(brick_token, eth, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    txb = brick_token.buy(amount, eth.address, {"from": account})
    amount_bought = txb.events["Bought"]["amountOut"]
    old_buyable_tokens = brick_token.buyableTokens()
    old_eth_balance = eth.balanceOf(account)
    old_contract_eth_balance = eth.balanceOf(brick_token.address)
    old_brick_balance = brick_token.balanceOf(account)
    amount_sold = amount * 75 // 100

    # Act
    tx = brick_token.sell(amount_bought, eth.address, {"from": account})

    # Assert
    assert eth.balanceOf(account) == old_eth_balance + amount_sold
    assert eth.balanceOf(brick_token.address) == old_contract_eth_balance - amount_sold
    assert (
        brick_token.token_deposit(eth.address) == old_contract_eth_balance - amount_sold
    )
    assert brick_token.buyableTokens() == old_buyable_tokens + amount_bought
    assert brick_token.balanceOf(account) == old_brick_balance - amount_bought
    assert brick_token.tokenWithDeposits(0) == eth.address
    assert brick_token.token_deposit(eth.address) == amount - amount_sold
    assert tx.events["Sold"]["from"] == account
    assert tx.events["Sold"]["amountIn"] == amount_bought - (amount_bought * 25 // 100)
    assert tx.events["Sold"]["exchangeToken"] == eth.address
    assert tx.events["Sold"]["amountOut"] == amount_sold


def test_sell_fail_token_not_allowed(brick_token, token, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Cannot sell to this token"):
        brick_token.sell(amount, token, {"from": account})


def test_sell_fail_amount_is_not_enought(brick_token, dai, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be more than 0 tokens"):
        brick_token.sell(0, dai, {"from": account})


def test_sell_fail_token_no_tokens_available(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("There are not enought available tokens to sell"):
        brick_token.sell(amount, dai, {"from": account})


# endregion

# region fillUp


def test_fillUp_success_dai(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    old_dai_balance = dai.balanceOf(account)
    old_contract_dai_balance = dai.balanceOf(brick_token)

    # Act
    tx = brick_token.fillUp(amount, dai.address, {"from": account})

    # Assert
    assert brick_token.tokenWithDeposits(0) == dai.address
    assert brick_token.token_deposit(dai.address) == old_contract_dai_balance + amount
    assert dai.balanceOf(account.address) == old_dai_balance - amount
    assert dai.balanceOf(brick_token.address) == old_contract_dai_balance + amount
    assert tx.events["FilledUp"]["amount"] == amount
    assert tx.events["FilledUp"]["token"] == dai.address


def test_fillUp_success_brick(brick_token, dai, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    brick_token.buy(amount, dai.address, {"from": account})
    old_contract_tokens = brick_token.buyableTokens()
    old_brick_balance = brick_token.balanceOf(account)

    # Act
    tx = brick_token.fillUp(amount, brick_token.address, {"from": account})

    # Assert
    assert brick_token.buyableTokens() == old_contract_tokens + amount
    assert brick_token.balanceOf(account) == old_brick_balance - amount
    assert tx.events["FilledUp"]["amount"] == amount
    assert tx.events["FilledUp"]["token"] == brick_token.address


def test_fillUp_fail_token_not_allowed(brick_token, token, amount, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Cannot fill up reserves with this token"):
        brick_token.fillUp(amount, token, {"from": account})


def test_fillUp_fail_amount_is_not_enought(brick_token, dai, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be more than 0 tokens"):
        brick_token.fillUp(0, dai, {"from": account})


# endregion
