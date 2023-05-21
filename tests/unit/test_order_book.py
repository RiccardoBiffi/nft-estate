from brownie import network, web3, exceptions
from brownie import OrderBook
import brownie
import pytest
from scripts.utilities import get_account, LOCAL_BLOCKCHAIN_ENVIRONMENTS


def test_can_deploy_contract():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    account = get_account()
    book_token = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    price_token = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"

    # Act
    ob = OrderBook.deploy(book_token, price_token, {"from": account})

    # Assert
    assert ob.bookToken() == "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    assert ob.priceToken() == "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
    assert ob.marketPrice() == 0


def test_addBid_success_single(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        bid,
        bid,
        0,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.bookTokenVault() == bid
    assert book_token.balanceOf(order_book) == bid
    assert book_token.balanceOf(account) == supply - bid
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.openBidsStack(0) == price


def test_addAsk_success_single(order_book, price_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        ask,
        ask,
        1,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.priceTokenVault() == ask * price / 10**18
    assert price_token.balanceOf(order_book) == ask * price / 10**18
    assert price_token.balanceOf(account) == supply - (ask * price / 10**18)
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.openAsksStack(0) == price
