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


# region addBid
def test_addBid_success_single(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.bookTokenVault() == bid
    assert book_token.balanceOf(order_book) == bid
    assert book_token.balanceOf(account) == supply - bid
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
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.openBidsStack(0) == price
    assert order_book.bestBidPrice() == price


def test_addBid_success_multiple_same_price(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addBid(price, bid, {"from": account})
    tx = order_book.addBid(price, bid, {"from": account})
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.bookTokenVault() == bid * 3
    assert book_token.balanceOf(order_book) == bid * 3
    assert book_token.balanceOf(account) == supply - bid * 3
    assert order_book.orderID_order(4) == (
        "0x0000000000000000000000000000000000000000",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.price_openBids(price, 1) == 2
    assert order_book.price_openBids(price, 2) == 3
    assert order_book.openBidsStack(0) == price
    assert order_book.bestBidPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(1) == 0


def test_addBid_success_multiple_different_price(
    order_book, book_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18

    # Act
    tx = order_book.addBid(price1, bid, {"from": account})
    tx = order_book.addBid(price3, bid, {"from": account})
    tx = order_book.addBid(price2, bid, {"from": account})

    # Assert
    assert order_book.bookTokenVault() == bid * 3
    assert book_token.balanceOf(order_book) == bid * 3
    assert book_token.balanceOf(account) == supply - bid * 3
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3
    assert order_book.price_openBids(price1, 0) == 1
    assert order_book.price_openBids(price2, 0) == 3
    assert order_book.price_openBids(price3, 0) == 2
    assert order_book.openBidsStack(0) == price1
    assert order_book.openBidsStack(1) == price2
    assert order_book.openBidsStack(2) == price3
    assert order_book.bestBidPrice() == price3


def test_addBid_success_match_ask_complete(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # todo match complete


def test_addBid_success_match_ask_partial(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # todo match partial


def test_addBid_fail_price_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 0

    # Act

    # Assert
    with brownie.reverts("Price must be greater than zero"):
        order_book.addBid(price, bid, {"from": account})


def test_addBid_fail_amount_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 0
    price = 1 * 10**18

    # Act

    # Assert
    with brownie.reverts("Amount must be greater than zero"):
        order_book.addBid(price, bid, {"from": account})


def test_addBid_fail_greater_than_best_ask_price(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18
    order_book.addAsk(price, bid, {"from": account})

    # Act

    # Assert
    with brownie.reverts("Price must be greater or equal than best ask price"):
        order_book.addBid(price - 1, bid, {"from": account})


# endregion

# region addAsk


def test_addAsk_success_single(order_book, price_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.priceTokenVault() == ask * price / 10**18
    assert price_token.balanceOf(order_book) == ask * price / 10**18
    assert price_token.balanceOf(account) == supply - (ask * price / 10**18)
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
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.openAsksStack(0) == price
    assert order_book.bestAskPrice() == price


def test_addAsk_success_multiple_same_price(order_book, price_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})
    tx = order_book.addAsk(price, ask, {"from": account})
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.priceTokenVault() == (ask * price * 3) / 10**18
    assert price_token.balanceOf(order_book) == (ask * price * 3) / 10**18
    assert price_token.balanceOf(account) == supply - (ask * price * 3) / 10**18
    assert order_book.orderID_order(4) == (
        "0x0000000000000000000000000000000000000000",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.price_openAsks(price, 1) == 2
    assert order_book.price_openAsks(price, 2) == 3
    assert order_book.openAsksStack(0) == price
    assert order_book.bestAskPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(1) == 0


def test_addAsk_success_multiple_different_price(
    order_book, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    total = ((ask * price1) + (ask * price2) + (ask * price3)) / 10**18

    # Act
    tx = order_book.addAsk(price1, ask, {"from": account})
    tx = order_book.addAsk(price3, ask, {"from": account})
    tx = order_book.addAsk(price2, ask, {"from": account})

    # Assert
    assert order_book.priceTokenVault() == total
    assert price_token.balanceOf(order_book) == total
    assert price_token.balanceOf(account) == supply - total
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3
    assert order_book.price_openAsks(price1, 0) == 1
    assert order_book.price_openAsks(price3, 0) == 2
    assert order_book.price_openAsks(price2, 0) == 3
    assert order_book.openAsksStack(0) == price3
    assert order_book.openAsksStack(1) == price2
    assert order_book.openAsksStack(2) == price1
    assert order_book.bestAskPrice() == price1


def test_addAsk_success_match_bid_complete(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # todo match complete


def test_addAsk_success_match_bid_partial(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # todo match partial


def test_addAsk_fail_price_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 0

    # Act

    # Assert
    with brownie.reverts("Price must be greater than zero"):
        order_book.addAsk(price, ask, {"from": account})


def test_addAsk_fail_amount_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 0
    price = 1 * 10**18

    # Act

    # Assert
    with brownie.reverts("Amount must be greater than zero"):
        order_book.addAsk(price, ask, {"from": account})


def test_addAsk_fail_lower_than_best_bid_price(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 1 * 10**18
    order_book.addBid(price, ask, {"from": account})

    # Act

    # Assert
    with brownie.reverts("Price must be less or equal than best bid price"):
        order_book.addAsk(price + 1, ask, {"from": account})


# endregion


# region marketBuy
def test_marketBuy_success_single_bid_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    bid = 10 * 10**18
    book_token.mint(bid, {"from": bidder})
    book_token.approve(order_book, bid, {"from": bidder})
    price = 1 * 10**18
    order_book.addBid(price, bid, {"from": bidder})
    buy_amount = price * bid / 10**18

    # Act
    tx = order_book.marketBuy(bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        buy_amount,
        0,
        2,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.marketPrice() == price
    assert order_book.bookTokenVault() == 0
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + bid
    assert book_token.balanceOf(bidder) == 0
    assert order_book.priceTokenVault() == 0
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - buy_amount
    assert price_token.balanceOf(bidder) == buy_amount
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)


# todo test_marketBuy_success_single_bid_partial
# todo test_marketBuy_success_mutiple_bid_same_price
# todo test_marketBuy_success_mutiple_bid_different_price

# endregion

# region marketSell

# endregion

# region cancelOrder

# endregion
