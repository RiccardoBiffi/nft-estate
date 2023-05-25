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
    assert ob.bestBidPrice() == 2**256 - 1
    assert ob.bestAskPrice() == 0


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
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.user_ordersId(account, 0) == 1
    assert order_book.price_openBids(price, 0) == 1
    assert order_book.openBidsStack(0) == price
    assert order_book.bestBidPrice() == price


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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        3 * 10**18,
        0,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
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
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        5 * 10**18,
        0,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        asker.address,
        price,
        ask,
        5 * 10**18,
        1,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
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
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        account.address,
        price,
        ask,
        3 * 10**18,
        1,
        0,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        5 * 10**18,
        0,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        0,
        1,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
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
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(2) == (
        bidder.address,
        price,
        bid,
        0,
        0,
        1,
        web3.eth.get_block("latest").timestamp,
        web3.eth.get_block("latest").timestamp,
    )
    assert order_book.orderID_order(3) == (
        account.address,
        price,
        ask,
        5 * 10**18,
        1,
        0,
        web3.eth.get_block("latest").timestamp,
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
    bidder = get_account(index=1)
    bid = 10 * 10**18
    book_token.mint(bidder, supply, {"from": bidder})
    book_token.approve(order_book, supply, {"from": bidder})
    price = 1 * 10**18
    order_book.addAsk(price, bid, {"from": bidder})
    buy_amount = price * bid // 10**18

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
    assert book_token.balanceOf(order_book) == 0
    assert book_token.balanceOf(account) == supply + bid
    assert book_token.balanceOf(bidder) == 0
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - buy_amount
    assert price_token.balanceOf(bidder) == buy_amount
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)


def test_marketBuy_success_single_bid_partial(
    order_book, book_token, price_token, supply, account
):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")

    # Arrange
    bidder = get_account(index=1)
    bid = 10 * 10**18
    book_token.mint(bidder, bid, {"from": bidder})
    book_token.approve(order_book, bid, {"from": bidder})
    price = 1 * 10**18
    order_book.addBid(price, bid, {"from": bidder})
    buy_amount = price * bid // 10**18

    # Act
    token_buy = 7 * 10**18
    tx = order_book.marketBuy(bid, {"from": account})

    # Assert
    assert order_book.orderID_order(1) == (
        bidder.address,
        price,
        bid,
        3 * 10**18,
        0,
        0,
        web3.eth.get_block("latest").timestamp,
        0,
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
    assert book_token.balanceOf(order_book) == 3 * 10**18
    assert book_token.balanceOf(account) == supply + token_buy
    assert book_token.balanceOf(bidder) == supply - bid
    # todo check rest
    assert price_token.balanceOf(order_book) == 0
    assert price_token.balanceOf(account) == supply - buy_amount
    assert price_token.balanceOf(bidder) == buy_amount
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.price_openBids(price, 0)
    with pytest.raises(exceptions.VirtualMachineError):
        assert order_book.openBidsStack(0)


# todo test_marketBuy_success_mutiple_bid_same_price
# todo test_marketBuy_success_mutiple_bid_different_price
# todo test_marketBuy_fail_amount_zero
# todo test_marketBuy_fail_no_open_bids

# endregion

# region marketSell

# endregion

# region cancelOrder

# endregion
