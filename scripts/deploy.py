from sqlite3 import Time
import time
from brownie import accounts, network, config
from brownie import BrickToken
from scripts.utilities import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    MockContract,
    get_account,
    get_contract,
)


BRICK_TOTAL_SUPPLY = 1000000 * 10**18


def publish_source_policy():
    return config["networks"][network.show_active()].get("verify", False)


def deploy():
    account = get_account()

    brick_token = BrickToken.deploy(
        BRICK_TOTAL_SUPPLY,
        {"from": account},
        publish_source=publish_source_policy(),
    )

    fau_token = get_contract(MockContract.FAU_TOKEN)
    weth_token = get_contract(MockContract.WETH_TOKEN)

    bt_allowed_token_addresses_and_feeds = {
        brick_token: get_contract(MockContract.DAI_USD_FEED),
        fau_token: get_contract(MockContract.DAI_USD_FEED),
        weth_token: get_contract(MockContract.ETH_USD_FEED),
    }

    add_allowed_tokens(brick_token, bt_allowed_token_addresses_and_feeds, account)
    add_allowed_tokens(brick_token, bt_allowed_token_addresses_and_feeds, account)

    return account


def add_allowed_tokens(contract, allowed_tokens_price_feeds, account):
    for token in allowed_tokens_price_feeds:
        contract.addAllowedToken(token.address, {"from": account})
        contract.setTokenPriceFeed(
            token.address, allowed_tokens_price_feeds[token], {"from": account}
        )

    return contract


def main():
    deploy()

    time.sleep(1)


if __name__ == "__main__":
    main()
