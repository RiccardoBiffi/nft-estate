from sqlite3 import Time
import time
from brownie import OrderBook, MockERC20
from scripts.deploy import publish_source_policy
from scripts.utilities import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    MockContract,
    get_account,
)

CARLO_ADDRESS = "0x12540A0801d50AF38E10cbf00094c59AEdf632B5"


def deploy_order_book():
    account = get_account()

    book_token = MockERC20.deploy(
        "Book Order Token",
        "BOOK",
        {"from": account},
        publish_source=publish_source_policy(),
    )
    book_token.mint(account, 1000000 * 10**18, {"from": account})
    book_token.mint(
        CARLO_ADDRESS,
        1000000 * 10**18,
        {"from": account},
    )
    price_token = MockERC20.deploy(
        "Price Token",
        "PRICE",
        {"from": account},
        publish_source=publish_source_policy(),
    )
    price_token.mint(account, 1000000 * 10**18, {"from": account})
    price_token.mint(
        CARLO_ADDRESS,
        1000000 * 10**18,
        {"from": account},
    )

    OrderBook.deploy(
        book_token.address,
        price_token.address,
        {"from": account},
        publish_source=publish_source_policy(),
    )


def main():
    deploy_order_book()

    time.sleep(1)


if __name__ == "__main__":
    main()
