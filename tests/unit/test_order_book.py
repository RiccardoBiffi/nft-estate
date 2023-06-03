from brownie import network, web3, exceptions
from brownie import OrderBook
import brownie
import pytest
from scripts.utilities import get_account, LOCAL_BLOCKCHAIN_ENVIRONMENTS

EMPTY_ORDER = (
    "0x0000000000000000000000000000000000000000",
    0,
    0,
    0,
    0,
    0,
    0,
    0,
)
EMPTY_MATCH = (
    0,
    0,
)


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
    assert ob.bestAskPrice() == 2**256 - 1
    assert ob.bestBidPrice() == 0


# region addBid
def test_addBid_success_single(order_book, price_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert price_token.balanceOf(order_book) == bid
    assert price_token.balanceOf(account) == supply - bid
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        bid,
        bid,
        0,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.openBidsStack(0) == price
    assert order_book.bestBidPrice() == price
    assert order_book.orderID_matches(1, 0) == EMPTY_MATCH


def test_addBid_success_multiple_same_price(order_book, price_token, supply, account):
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
    assert price_token.balanceOf(order_book) == 3 * bid * price // 10**18
    assert price_token.balanceOf(account) == supply - 3 * bid * price // 10**18
    assert order_book.orderID_order(4) == EMPTY_ORDER
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
    order_book, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bid = 10 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    total = (price1 * bid + price2 * bid + price3 * bid) // 10**18

    # Act
    tx = order_book.addBid(price1, bid, {"from": account})
    tx = order_book.addBid(price3, bid, {"from": account})
    tx = order_book.addBid(price2, bid, {"from": account})

    # Assert
    assert price_token.balanceOf(order_book) == total
    assert price_token.balanceOf(account) == supply - total
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


def test_addBid_success_match_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    ask = 10 * 10**18
    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    bid = 10 * 10**18
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_matches(1, 0) == (
        ask,
        order_book.orderID_matches(1, 0)[1],
    )
    assert order_book.orderID_matches(1, 0)[1] > 0
    assert order_book.orderID_matches(2, 0) == (
        bid,
        order_book.orderID_matches(2, 0)[1],
    )
    assert order_book.orderID_matches(2, 0)[1] > 0
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask
    assert book_token.balanceOf(asker) == supply - bid
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - bid * price // 10**18
    assert price_token.balanceOf(asker) == supply + ask * price // 10**18
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addBid_success_match_partial_bid(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 7 * 10**18
    bid = 10 * 10**18
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        3 * 10**18,
        0,
        0,
        order_book.orderID_order(2)[6],
        0,
    )
    assert order_book.orderID_matches(1, 0) == (
        ask,
        order_book.orderID_matches(1, 0)[1],
    )
    assert order_book.orderID_matches(1, 0)[1] > 0
    assert order_book.orderID_matches(2, 0) == (
        ask,
        order_book.orderID_matches(2, 0)[1],
    )
    assert order_book.orderID_matches(2, 0)[1] > 0
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask
    assert book_token.balanceOf(asker) == supply - ask
    assert price_token.balanceOf(order_book) == price * (bid - ask) // 10**18
    assert price_token.balanceOf(account) == supply - ((bid * price) // 10**18)
    assert price_token.balanceOf(asker) == supply + ((ask * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openBids(price, 0) == 2
    assert order_book.openBidsStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addBid_success_match_partial_ask(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    bid = 7 * 10**18
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        3 * 10**18,
        1,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert book_token.balanceOf(order_book) == ask - bid
    assert book_token.balanceOf(account) == supply + bid
    assert book_token.balanceOf(asker) == supply - ask
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - ((bid * price) // 10**18)
    assert price_token.balanceOf(asker) == supply + ((bid * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addBid_success_match_multiple_ask_same_price_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    bid = 20 * 10**18
    tx = order_book.addAsk(price, ask, {"from": asker})
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_matches(1, 0) == (
        ask,
        order_book.orderID_matches(1, 0)[1],
    )
    assert order_book.orderID_matches(1, 0)[1] > 0
    assert order_book.orderID_matches(2, 0) == (
        ask,
        order_book.orderID_matches(2, 0)[1],
    )
    assert order_book.orderID_matches(2, 0)[1] > 0
    assert order_book.orderID_matches(3, 0) == (
        ask,
        order_book.orderID_matches(3, 0)[1],
    )
    assert order_book.orderID_matches(3, 1) == (
        ask,
        order_book.orderID_matches(3, 1)[1],
    )
    assert order_book.orderID_matches(3, 0)[1] > 0
    assert order_book.orderID_matches(3, 1)[1] > 0
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask * 2
    assert book_token.balanceOf(asker) == supply - ask * 2
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - ((bid * price) // 10**18)
    assert price_token.balanceOf(asker) == supply + ((bid * price) // 10**18)
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_addBid_success_match_multiple_ask_same_price_partial_bid(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    bid = 25 * 10**18
    tx = order_book.addAsk(price, ask, {"from": asker})
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        5 * 10**18,
        0,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.orderID_matches(1, 0) == (
        ask,
        order_book.orderID_matches(1, 0)[1],
    )
    assert order_book.orderID_matches(1, 0)[1] > 0
    assert order_book.orderID_matches(2, 0) == (
        ask,
        order_book.orderID_matches(2, 0)[1],
    )
    assert order_book.orderID_matches(2, 0)[1] > 0
    assert order_book.orderID_matches(3, 0) == (
        ask,
        order_book.orderID_matches(3, 0)[1],
    )
    assert order_book.orderID_matches(3, 1) == (
        ask,
        order_book.orderID_matches(3, 1)[1],
    )
    assert order_book.orderID_matches(3, 0)[1] > 0
    assert order_book.orderID_matches(3, 1)[1] > 0
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask * 2
    assert book_token.balanceOf(asker) == supply - ask * 2
    assert price_token.balanceOf(order_book) == 5 * 10**18
    assert price_token.balanceOf(account) == supply - ((bid * price) // 10**18)
    assert price_token.balanceOf(asker) == supply + ((2 * ask * price) // 10**18)
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0) == price
    assert order_book.price_openBids(price, 0) == 3
    assert order_book.openBidsStack(0) == price
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_addBid_success_match_multiple_ask_same_price_partial_ask(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    bid = 15 * 10**18
    tx = order_book.addAsk(price, ask, {"from": asker})
    tx = order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.addBid(price, bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        5 * 10**18,
        1,
        0,
        order_book.orderID_order(2)[6],
        0,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_matches(1, 0) == (
        ask,
        order_book.orderID_matches(1, 0)[1],
    )
    assert order_book.orderID_matches(1, 0)[1] > 0
    assert order_book.orderID_matches(2, 0) == (
        bid - ask,
        order_book.orderID_matches(2, 0)[1],
    )
    assert order_book.orderID_matches(2, 0)[1] > 0
    assert order_book.orderID_matches(3, 0) == (
        ask,
        order_book.orderID_matches(3, 0)[1],
    )
    assert order_book.orderID_matches(3, 1) == (
        bid - ask,
        order_book.orderID_matches(3, 1)[1],
    )
    assert order_book.orderID_matches(3, 0)[1] > 0
    assert order_book.orderID_matches(3, 1)[1] > 0
    assert book_token.balanceOf(order_book) == 5 * 10**18
    assert book_token.balanceOf(account) == supply + bid
    assert book_token.balanceOf(asker) == supply - ask * 2
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - ((bid * price) // 10**18)
    assert price_token.balanceOf(asker) == supply + ((bid * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openAsks(price, 0) == 2
    assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


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
    with brownie.reverts("Price must be less or equal than best ask price"):
        order_book.addBid(price + 1, bid, {"from": account})


# endregion

# region addAsk


def test_addAsk_success_single(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price = 1 * 10**18

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert book_token.balanceOf(order_book) == ask * price // 10**18
    assert book_token.balanceOf(account) == supply - (ask * price // 10**18)
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        ask,
        ask,
        1,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.openAsksStack(0) == price
    assert order_book.bestAskPrice() == price


def test_addAsk_success_multiple_same_price(order_book, book_token, supply, account):
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
    assert book_token.balanceOf(order_book) == (ask * price * 3) // 10**18
    assert book_token.balanceOf(account) == supply - (ask * price * 3) // 10**18
    assert order_book.orderID_order(4) == EMPTY_ORDER
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
    order_book, book_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    ask = 10 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    total = ask * 3

    # Act
    tx = order_book.addAsk(price1, ask, {"from": account})
    tx = order_book.addAsk(price3, ask, {"from": account})
    tx = order_book.addAsk(price2, ask, {"from": account})

    # Assert
    assert book_token.balanceOf(order_book) == total
    assert book_token.balanceOf(account) == supply - total
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


def test_addAsk_success_match_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    bid = 10 * 10**18
    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    ask = 10 * 10**18
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + bid
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + ask * price // 10**18
    assert price_token.balanceOf(bidder) == supply - bid * price // 10**18
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addAsk_success_match_partial_bid(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    ask = 7 * 10**18
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        3 * 10**18,
        0,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + ask
    assert price_token.balanceOf(order_book) == price * (bid - ask) // 10**18
    assert price_token.balanceOf(account) == supply + ((ask * price) // 10**18)
    assert price_token.balanceOf(bidder) == supply - ((bid * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.openBidsStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addAsk_success_match_partial_ask(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 7 * 10**18
    ask = 10 * 10**18
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        3 * 10**18,
        1,
        0,
        order_book.orderID_order(2)[6],
        0,
    )
    assert book_token.balanceOf(order_book) == ask - bid
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + bid
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + ((bid * price) // 10**18)
    assert price_token.balanceOf(bidder) == supply - ((bid * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openAsks(price, 0) == 2
    assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2


def test_addAsk_success_match_multiple_bid_same_price_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    ask = 20 * 10**18
    tx = order_book.addBid(price, bid, {"from": bidder})
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + ask
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + ((2 * bid * price) // 10**18)
    assert price_token.balanceOf(bidder) == supply - ((2 * bid * price) // 10**18)
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_addAsk_success_match_multiple_bid_different_price_partial_bid(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    ask = 15 * 10**18
    tx = order_book.addBid(price, bid, {"from": bidder})
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        5 * 10**18,
        0,
        0,
        order_book.orderID_order(2)[6],
        0,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + ask
    assert price_token.balanceOf(order_book) == 5 * 10**18
    assert price_token.balanceOf(account) == supply + ((ask * price) // 10**18)
    assert price_token.balanceOf(bidder) == supply - ((2 * bid * price) // 10**18)
    assert order_book.marketPrice() == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0) == price
    assert order_book.price_openBids(price, 0) == 2
    assert order_book.openBidsStack(0) == price
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_addAsk_success_match_multiple_bid_different_price_partial_ask(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    ask = 25 * 10**18
    tx = order_book.addBid(price, bid, {"from": bidder})
    tx = order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.addAsk(price, ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        5 * 10**18,
        1,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert book_token.balanceOf(order_book) == 5 * 10**18
    assert book_token.balanceOf(account) == supply - ask
    assert book_token.balanceOf(bidder) == supply + bid * 2
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + ((2 * bid * price) // 10**18)
    assert price_token.balanceOf(bidder) == supply - ((2 * bid * price) // 10**18)
    assert order_book.marketPrice() == price
    assert order_book.price_openAsks(price, 0) == 3
    assert order_book.openAsksStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


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
    with brownie.reverts("Price must be greater or equal than best bid price"):
        order_book.addAsk(price - 1, ask, {"from": account})


# endregion


# region marketBuy
def test_marketBuy_success_single_ask_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.marketBuy(ask, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        0,
        2,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask
    assert book_token.balanceOf(asker) == supply - ask
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - ask * price // 10**18
    assert price_token.balanceOf(asker) == supply + ask * price // 10**18
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.user_ordersId(account, 1) == 0


def test_marketBuy_success_single_ask_partial(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    buy = 15 * 10**18
    order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.marketBuy(buy, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        buy,
        5 * 10**18,
        2,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        5 * 10**18,
        5 * 10**18,
        0,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask
    assert book_token.balanceOf(asker) == supply - ask
    assert price_token.balanceOf(order_book) == 5 * 10**18
    assert price_token.balanceOf(account) == supply - buy * price // 10**18
    assert price_token.balanceOf(asker) == supply + ask * price // 10**18
    assert order_book.price_openBids(price, 0) == 3
    assert order_book.openBidsStack(0) == price
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2
    assert order_book.user_ordersId(account, 1) == 3


def test_marketBuy_success_mutiple_ask_same_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    buy = 20 * 10**18
    order_book.addAsk(price, ask, {"from": asker})
    order_book.addAsk(price, ask, {"from": asker})

    # Act
    tx = order_book.marketBuy(buy, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        buy,
        0,
        2,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == EMPTY_ORDER
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + ask * 2
    assert book_token.balanceOf(asker) == supply - ask * 2
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - buy * price // 10**18
    assert price_token.balanceOf(asker) == supply + buy * price // 10**18
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_marketBuy_success_mutiple_ask_different_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    buy = 30 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    total = (price1 * ask + price2 * ask + price3 * ask) // 10**18
    tx = order_book.addAsk(price1, ask, {"from": asker})
    tx = order_book.addAsk(price3, ask, {"from": asker})
    tx = order_book.addAsk(price2, ask, {"from": asker})

    # Act
    tx = order_book.marketBuy(buy, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price1,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price3,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        asker.address,
        price2,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == (
        account.address,
        (total // buy) * 10**18,
        buy,
        0,
        2,
        1,
        order_book.orderID_order(4)[6],
        order_book.orderID_order(4)[7],
    )
    assert order_book.orderID_order(5) == EMPTY_ORDER
    assert order_book.marketPrice() == price3
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + buy
    assert book_token.balanceOf(asker) == supply - buy
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - total
    assert price_token.balanceOf(asker) == supply + total
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price3, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price3, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(asker, 2) == 3
    assert order_book.user_ordersId(account, 0) == 4


def test_marketBuy_success_mutiple_ask_different_and_same_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    asker = get_account(index=1)
    book_token.mint(asker, supply, {"from": asker})
    book_token.approve(order_book, supply, {"from": asker})
    price_token.mint(asker, supply, {"from": asker})
    price_token.approve(order_book, supply, {"from": asker})

    ask = 10 * 10**18
    buy = 30 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    total = (price1 * ask * 2 + price2 * ask) // 10**18
    tx = order_book.addAsk(price1, ask, {"from": asker})
    tx = order_book.addAsk(price1, ask, {"from": asker})
    tx = order_book.addAsk(price2, ask, {"from": asker})

    # Act
    tx = order_book.marketBuy(buy, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        asker.address,
        price1,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price1,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        asker.address,
        price2,
        ask,
        0,
        1,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == (
        account.address,
        (total * 10**18 // buy),
        buy,
        0,
        2,
        1,
        order_book.orderID_order(4)[6],
        order_book.orderID_order(4)[7],
    )
    assert order_book.orderID_order(5) == EMPTY_ORDER
    assert order_book.marketPrice() == price2
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + buy
    assert book_token.balanceOf(asker) == supply - buy
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - total
    assert price_token.balanceOf(asker) == supply + total
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price2, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price1, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price2, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(asker, 0) == 1
    assert order_book.user_ordersId(asker, 1) == 2
    assert order_book.user_ordersId(asker, 2) == 3
    assert order_book.user_ordersId(account, 0) == 4


def test_marketBuy_fail_amount_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be greater than zero"):
        order_book.marketBuy(0, {"from": account})


def test_marketBuy_fail_no_open_asks(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("No open asks"):
        order_book.marketBuy(10 * 10**18, {"from": account})


# endregion

# region marketSell


def test_marketSell_success_single_ask_complete(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.marketSell(bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        0,
        3,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - bid
    assert book_token.balanceOf(bidder) == supply + bid
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + bid * price // 10**18
    assert price_token.balanceOf(bidder) == supply - bid * price // 10**18
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.user_ordersId(account, 1) == 0


def test_marketSell_success_single_ask_partial(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    sell = 15 * 10**18
    order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.marketSell(sell, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        sell,
        5 * 10**18,
        3,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        5 * 10**18,
        5 * 10**18,
        1,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 5 * 10**18
    assert book_token.balanceOf(account) == supply - sell
    assert book_token.balanceOf(bidder) == supply + bid
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + bid * price // 10**18
    assert price_token.balanceOf(bidder) == supply - bid * price // 10**18
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert order_book.price_openAsks(price, 0) == 3
    assert order_book.openAsksStack(0) == price
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(account, 0) == 2
    assert order_book.user_ordersId(account, 1) == 3


def test_marketSell_success_mutiple_ask_same_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    price = 1 * 10**18

    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    sell = 20 * 10**18
    order_book.addBid(price, bid, {"from": bidder})
    order_book.addBid(price, bid, {"from": bidder})

    # Act
    tx = order_book.marketSell(sell, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        sell,
        0,
        3,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == EMPTY_ORDER
    assert order_book.marketPrice() == price
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - sell
    assert book_token.balanceOf(bidder) == supply + sell
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + sell * price // 10**18
    assert price_token.balanceOf(bidder) == supply - sell * price // 10**18
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(account, 0) == 3


def test_marketSell_success_mutiple_ask_different_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    sell = 30 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    total = (price1 * bid + price2 * bid + price3 * bid) // 10**18
    tx = order_book.addBid(price1, bid, {"from": bidder})
    tx = order_book.addBid(price3, bid, {"from": bidder})
    tx = order_book.addBid(price2, bid, {"from": bidder})

    # Act
    tx = order_book.marketSell(sell, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price1,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price3,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        bidder.address,
        price2,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == (
        account.address,
        (total // sell) * 10**18,
        sell,
        0,
        3,
        1,
        order_book.orderID_order(4)[6],
        order_book.orderID_order(4)[7],
    )
    assert order_book.orderID_order(5) == EMPTY_ORDER
    assert order_book.marketPrice() == price1
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - sell
    assert book_token.balanceOf(bidder) == supply + sell
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + total
    assert price_token.balanceOf(bidder) == supply - total
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price3, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price3, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(bidder, 2) == 3
    assert order_book.user_ordersId(account, 0) == 4


def test_marketSell_success_mutiple_ask_different_and_same_price(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price_token.mint(bidder, supply, {"from": bidder})
    price_token.approve(order_book, supply, {"from": bidder})

    bid = 10 * 10**18
    sell = 30 * 10**18
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    total = (price1 * bid * 2 + price2 * bid) // 10**18
    tx = order_book.addBid(price1, bid, {"from": bidder})
    tx = order_book.addBid(price1, bid, {"from": bidder})
    tx = order_book.addBid(price2, bid, {"from": bidder})

    # Act
    tx = order_book.marketSell(sell, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price1,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price1,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        bidder.address,
        price2,
        bid,
        0,
        0,
        1,
        order_book.orderID_order(3)[6],
        order_book.orderID_order(3)[7],
    )
    assert order_book.orderID_order(4) == (
        account.address,
        (total * 10**18 // sell),
        sell,
        0,
        3,
        1,
        order_book.orderID_order(4)[6],
        order_book.orderID_order(4)[7],
    )
    assert order_book.orderID_order(5) == EMPTY_ORDER
    assert order_book.marketPrice() == price1
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply - sell
    assert book_token.balanceOf(bidder) == supply + sell
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply + total
    assert price_token.balanceOf(bidder) == supply - total
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price2, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price1, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price2, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert order_book.user_ordersId(bidder, 0) == 1
    assert order_book.user_ordersId(bidder, 1) == 2
    assert order_book.user_ordersId(bidder, 2) == 3
    assert order_book.user_ordersId(account, 0) == 4


def test_marketSell_fail_amount_zero(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Amount must be greater than zero"):
        order_book.marketSell(0, {"from": account})


def test_marketSell_fail_no_open_asks(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("No open bids"):
        order_book.marketSell(10 * 10**18, {"from": account})


def test_marketSell_fail_insufficient_funds(order_book, book_token, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    order_book.addBid(1 * 10**18, 10 * 10**18, {"from": account})
    balance = book_token.balanceOf(account)
    book_token.transfer(
        "0x0000000000000000000000000000000000000001", balance, {"from": account}
    )

    # Act

    # Assert
    with brownie.reverts("Insufficient funds"):
        order_book.marketSell(10 * 10**18, {"from": account})


# endregion


# region cancelOrder
def test_cancelOrder_success_alone_bid(order_book, price_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price = 1 * 10**18
    amount = 10 * 10**18
    order_book.addBid(price, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(1, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        amount,
        amount,
        0,
        2,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(1)[7] > 0
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply
    assert order_book.user_ordersId(account, 0) == 1


def test_cancelOrder_success_alone_ask(order_book, book_token, supply, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price = 1 * 10**18
    amount = 10 * 10**18
    order_book.addAsk(price, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(1, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        amount,
        amount,
        1,
        2,
        order_book.orderID_order(1)[6],
        order_book.orderID_order(1)[7],
    )
    assert order_book.orderID_order(1)[7] > 0
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openAsksStack(0)
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply
    assert order_book.user_ordersId(account, 0) == 1


def test_cancelOrder_success_multiple_same_price_bid(
    order_book, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price = 1 * 10**18
    amount = 10 * 10**18
    order_book.addBid(price, amount, {"from": account})
    order_book.addBid(price, amount, {"from": account})
    order_book.addBid(price, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(2, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        amount,
        amount,
        0,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        amount,
        amount,
        0,
        2,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        amount,
        amount,
        0,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.orderID_order(2)[7] > 0
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.price_openBids(price, 1) == 3
    assert order_book.openBidsStack(0) == price
    assert price_token.balanceOf(order_book) == 2 * price * amount // 10**18
    assert price_token.balanceOf(account) == supply - 2 * price * amount // 10**18
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3


def test_cancelOrder_success_multiple_same_price_ask(
    order_book, book_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price = 1 * 10**18
    amount = 10 * 10**18
    order_book.addAsk(price, amount, {"from": account})
    order_book.addAsk(price, amount, {"from": account})
    order_book.addAsk(price, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(2, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price,
        amount,
        amount,
        1,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        amount,
        amount,
        1,
        2,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        amount,
        amount,
        1,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.orderID_order(2)[7] > 0
    assert order_book.price_openAsks(price, 0) == 1
    assert order_book.price_openAsks(price, 1) == 3
    assert order_book.openAsksStack(0) == price
    assert book_token.balanceOf(order_book) == 2 * amount
    assert book_token.balanceOf(account) == supply - 2 * amount
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3


def test_cancelOrder_success_multiple_different_price_bid(
    order_book, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    amount = 10 * 10**18
    order_book.addBid(price1, amount, {"from": account})
    order_book.addBid(price2, amount, {"from": account})
    order_book.addBid(price3, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(2, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price1,
        amount,
        amount,
        0,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price2,
        amount,
        amount,
        0,
        2,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price3,
        amount,
        amount,
        0,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.orderID_order(2)[7] > 0
    assert order_book.price_openBids(price1, 0) == 1
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price2, 0)
    assert order_book.price_openBids(price3, 0) == 3
    assert order_book.openBidsStack(0) == price1
    assert order_book.openBidsStack(1) == price3
    assert price_token.balanceOf(order_book) == amount * (price1 + price3) // 10**18
    assert (
        price_token.balanceOf(account)
        == supply - amount * (price1 + price3) // 10**18
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3


def test_cancelOrder_success_multiple_different_price_ask(
    order_book, book_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    price1 = 1 * 10**18
    price2 = 2 * 10**18
    price3 = 3 * 10**18
    amount = 10 * 10**18
    order_book.addAsk(price1, amount, {"from": account})
    order_book.addAsk(price2, amount, {"from": account})
    order_book.addAsk(price3, amount, {"from": account})

    # Act
    tx = order_book.cancelOrder(2, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        account.address,
        price1,
        amount,
        amount,
        1,
        0,
        order_book.orderID_order(1)[6],
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price2,
        amount,
        amount,
        1,
        2,
        order_book.orderID_order(2)[6],
        order_book.orderID_order(2)[7],
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price3,
        amount,
        amount,
        1,
        0,
        order_book.orderID_order(3)[6],
        0,
    )
    assert order_book.orderID_order(2)[7] > 0
    assert order_book.price_openAsks(price1, 0) == 1
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openAsks(price2, 0)
    assert order_book.price_openAsks(price3, 0) == 3
    assert order_book.openAsksStack(0) == price3
    assert order_book.openAsksStack(1) == price1
    assert book_token.balanceOf(order_book) == 2 * amount
    assert book_token.balanceOf(account) == supply - 2 * amount
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.user_ordersId(account, 1) == 2
    assert order_book.user_ordersId(account, 2) == 3


def test_cancelOrder_fail_order_not_found(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange

    # Act

    # Assert
    with brownie.reverts("Order not found"):
        order_book.cancelOrder(1, {"from": account})


def test_cancelOrder_fail_not_maker(order_book, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    not_maker = get_account(index=1)
    order_book.addBid(1 * 10**18, 10 * 10**18, {"from": account})

    # Act

    # Assert
    with brownie.reverts("Not order maker"):
        order_book.cancelOrder(1, {"from": not_maker})


def test_cancelOrder_fail_order_not_open(order_book, book_token, account):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    order_book.addBid(1 * 10**18, 10 * 10**18, {"from": account})
    order_book.addAsk(1 * 10**18, 10 * 10**18, {"from": account})

    # Act

    # Assert
    with brownie.reverts("Order not open"):
        order_book.cancelOrder(2, {"from": account})


# endregion

# region getLiquidityDepthByPrice
# todo
# endregion

# region getMarketOrderAveragePrice
# todo
# endregion
