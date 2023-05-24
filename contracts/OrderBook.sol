// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/IOrderBook.sol";

//security avoid reentrancy attacks
//todo add and test events
//todo review ask and bid logic after meaning fix
//ask: io, per questa cosa che ho e voglio vendere, ti chiedo 0,5 l'uno (+ è meglio)
//bid: io, per questa cosa che tu hai e voglio acquistare, ti offro 0,5 l'uno (- è meglio)

contract OrderBook is IOrderBook {
    struct Order {
        address maker;
        uint256 pricePerUnit;
        uint256 startingAmount;
        uint256 amount;
        Type orderType;
        Status status;
        uint256 timestampOpen;
        uint256 timestampClose;
    }

    enum Type {
        Bid,
        Ask,
        MarketBuy,
        MarketSell
    }

    enum Status {
        Open,
        Filled,
        Cancelled
    }

    uint256 private constant _MAX_UINT = type(uint256).max;

    uint256 private _id;
    address public bookToken;
    address public priceToken;
    uint256 public marketPrice;
    uint256 public bookTokenVault; // todo create a Vault generic contract
    uint256 public priceTokenVault; // todo create a Vault generic contract

    mapping(uint256 => Order) public orderID_order;
    mapping(address => uint256[]) public user_ordersId;
    //todo make private
    mapping(uint256 => uint256[]) public price_openAsks; // asks ordered by time
    //todo make private
    mapping(uint256 => uint256[]) public price_openBids; // bids ordered by time
    // stack of all open asks ordered by pricePerUnit asc, [length-1] is the best
    uint256[] public openAsksStack;
    // stack of all open bids ordered by pricePerUnit desc, [length-1] is the best
    uint256[] public openBidsStack;

    constructor(address _bookToken, address _priceToken) {
        _id = 1;
        bookToken = _bookToken;
        priceToken = _priceToken;
        marketPrice = 0;
    }

    function marketBuy(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        require(openBidsStack.length > 0, "There are no open bids");

        uint256 bestPrice = bestBidPrice();

        orderID_order[_id] = Order(
            msg.sender,
            bestPrice,
            _amount,
            _amount,
            Type.MarketBuy,
            Status.Open,
            block.timestamp,
            0
        );

        Order storage newOrder = orderID_order[_id];
        _id++;

        while (newOrder.status != Status.Filled || bestPrice < _MAX_UINT) {
            uint256 bestBidId = price_openBids[bestPrice][0];
            Order storage bestBidOrder = orderID_order[bestBidId];

            _matchOrders(bestBidOrder, newOrder);

            if (bestBidOrder.status == Status.Filled) {
                _deleteItem(0, price_openBids[bestPrice]);
                if (price_openBids[bestPrice].length == 0) {
                    openBidsStack.pop();
                    bestPrice = bestBidPrice();
                }
            }
        }

        if (newOrder.status == Status.Open) {
            addAsk(marketPrice, newOrder.amount);
        }
    }

    function marketSell(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        require(openAsksStack.length > 0, "There are no open asks");
        require(
            IERC20(bookToken).balanceOf(msg.sender) >= _amount,
            "Insufficient funds"
        );

        uint256 bestPrice = bestAskPrice();
        orderID_order[_id] = Order(
            msg.sender,
            bestPrice,
            _amount,
            _amount,
            Type.MarketSell,
            Status.Open,
            block.timestamp,
            0
        );

        Order storage newOrder = orderID_order[_id];
        _id++;

        while (newOrder.status != Status.Filled || bestPrice > 0) {
            uint256 bestAskId = price_openAsks[bestPrice][0];
            Order storage bestAskOrder = orderID_order[bestAskId];

            _matchOrders(newOrder, bestAskOrder);

            if (bestAskOrder.status == Status.Filled) {
                _deleteItem(0, price_openAsks[bestPrice]);
                if (price_openAsks[bestPrice].length == 0) {
                    openAsksStack.pop();
                    bestPrice = bestAskPrice();
                }
            }
        }

        if (newOrder.status == Status.Open) {
            addBid(marketPrice, newOrder.amount);
        }
    }

    function addBid(uint256 _price, uint256 _amount) public {
        require(_price > 0, "Price must be greater than zero");
        require(_amount > 0, "Amount must be greater than zero");
        require(
            _price <= bestAskPrice(),
            "Price must be less or equal than best ask price"
        );

        orderID_order[_id] = Order(
            msg.sender,
            _price,
            _amount,
            _amount,
            Type.Bid,
            Status.Open,
            block.timestamp,
            0
        );

        Order storage newOrder = orderID_order[_id];
        user_ordersId[msg.sender].push(_id);

        priceTokenVault += (newOrder.amount * newOrder.pricePerUnit) / 1e18;
        IERC20(priceToken).transferFrom(
            msg.sender,
            address(this),
            (newOrder.amount * newOrder.pricePerUnit) / 1e18
        );

        uint256 i = 0;
        while (
            newOrder.status == Status.Open && i < price_openAsks[_price].length
        ) {
            Order storage bestAsk = orderID_order[price_openAsks[_price][i]];
            _matchOrders(newOrder, bestAsk);
            i++;
        }

        if (newOrder.status == Status.Open) {
            price_openBids[_price].push(_id);
            _insertBidInStack(_price);
        }

        if (i == 0) return;

        if (
            orderID_order[price_openAsks[_price][i - 1]].status == Status.Filled
        ) {
            price_openAsks[_price] = _skip(price_openAsks[_price], i);
        } else {
            price_openAsks[_price] = _skip(price_openAsks[_price], i - 1);
        }

        if (price_openAsks[_price].length == 0) openAsksStack.pop();

        _id++;
    }

    function _insertBidInStack(uint256 _price) private {
        if (price_openBids[_price].length == 1) {
            uint256 j = openBidsStack.length;
            openBidsStack.push(_price);
            while (j > 0 && openBidsStack[j - 1] > _price) {
                openBidsStack[j] = openBidsStack[j - 1];
                j--;
            }
            openBidsStack[j] = _price;
        }
    }

    function addAsk(uint256 _price, uint256 _amount) public {
        require(_price > 0, "Price must be greater than zero");
        require(_amount > 0, "Amount must be greater than zero");
        require(
            _price >= bestBidPrice(),
            "Price must be greater or equal than best bid price"
        );

        orderID_order[_id] = Order(
            msg.sender,
            _price,
            _amount,
            _amount,
            Type.Ask,
            Status.Open,
            block.timestamp,
            0
        );

        Order storage newOrder = orderID_order[_id];
        user_ordersId[msg.sender].push(_id);

        bookTokenVault += newOrder.amount;
        IERC20(bookToken).transferFrom(
            msg.sender,
            address(this),
            newOrder.amount
        );

        uint256 i = 0;
        while (
            newOrder.status == Status.Open && i < price_openBids[_price].length
        ) {
            Order storage bestBid = orderID_order[price_openBids[_price][i]];
            _matchOrders(bestBid, newOrder);
            i++;
        }

        if (newOrder.status == Status.Open) {
            price_openAsks[_price].push(_id);
            _insertAskInStack(_price);
        }

        if (i == 0) return;

        if (
            orderID_order[price_openBids[_price][i - 1]].status == Status.Filled
        ) {
            price_openBids[_price] = _skip(price_openBids[_price], i);
        } else {
            price_openBids[_price] = _skip(price_openBids[_price], i - 1);
        }

        if (price_openBids[_price].length == 0) openBidsStack.pop();

        _id++;
    }

    function _insertAskInStack(uint256 _price) private {
        if (price_openAsks[_price].length == 1) {
            uint256 j = openAsksStack.length;
            openAsksStack.push(_price);
            while (j > 0 && openAsksStack[j - 1] < _price) {
                openAsksStack[j] = openAsksStack[j - 1];
                j--;
            }
            openAsksStack[j] = _price;
        }
    }

    function _matchOrders(Order storage bid, Order storage ask) internal {
        uint256 matchedBookTokens = 0;

        if (bid.amount == ask.amount) {
            // complete match
            matchedBookTokens = bid.amount;
            _fillOrder(bid);
            _fillOrder(ask);
        } else if (bid.amount > ask.amount) {
            // partial match, bid is larger
            matchedBookTokens = ask.amount;
            bid.amount -= ask.amount;
            _fillOrder(ask);
        } else {
            // partial match, ask is larger
            matchedBookTokens = bid.amount;
            ask.amount -= bid.amount;
            _fillOrder(bid);
        }

        if (ask.orderType == Type.MarketBuy) {
            bookTokenVault -= matchedBookTokens;

            IERC20(bookToken).transfer(ask.maker, matchedBookTokens);
            IERC20(priceToken).transferFrom(
                ask.maker,
                bid.maker,
                (matchedBookTokens * ask.pricePerUnit) / 1e18
            );
        } else if (bid.orderType == Type.MarketSell) {
            priceTokenVault -= (matchedBookTokens * ask.pricePerUnit) / 1e18;

            IERC20(bookToken).transferFrom(
                bid.maker,
                ask.maker,
                matchedBookTokens
            );
            IERC20(priceToken).transfer(
                bid.maker,
                (matchedBookTokens * ask.pricePerUnit) / 1e18
            );
        } else {
            bookTokenVault -= matchedBookTokens;
            priceTokenVault -= (matchedBookTokens * ask.pricePerUnit) / 1e18;

            IERC20(bookToken).transfer(ask.maker, matchedBookTokens);
            IERC20(priceToken).transfer(
                bid.maker,
                (matchedBookTokens * ask.pricePerUnit) / 1e18
            );
        }
        marketPrice = ask.pricePerUnit;
    }

    function _fillOrder(Order storage order) internal {
        order.amount = 0;
        order.status = Status.Filled;
        order.timestampClose = block.timestamp;
    }

    function bestBidPrice() public view returns (uint256) {
        if (openBidsStack.length == 0) return _MAX_UINT;
        return openBidsStack[openBidsStack.length - 1];
    }

    function bestAskPrice() public view returns (uint256) {
        if (openAsksStack.length == 0) return 0;
        return openAsksStack[openAsksStack.length - 1];
    }

    function cancelOrder(uint256 orderID) external {
        require(
            msg.sender == orderID_order[orderID].maker,
            "Only the maker can cancel the order"
        );
        require(
            orderID_order[orderID].status == Status.Open,
            "Order is not open"
        );

        orderID_order[orderID].status = Status.Cancelled;
        orderID_order[orderID].timestampClose = block.timestamp;

        if (orderID_order[orderID].orderType == Type.Bid) {
            uint256[] storage openBids = price_openBids[
                orderID_order[orderID].pricePerUnit
            ];
            for (uint256 i = 0; i < openBids.length; i++) {
                if (openBids[i] == orderID) {
                    _deleteItem(i, openBids);
                    break;
                }
            }
            for (uint256 i = 0; i < openBidsStack.length; i++) {
                if (openBidsStack[i] == orderID) {
                    _deleteItem(i, openBidsStack);
                    break;
                }
            }

            bookTokenVault -= orderID_order[orderID].amount;
            IERC20(bookToken).transferFrom(
                address(this),
                orderID_order[orderID].maker,
                orderID_order[orderID].amount
            );
        } else {
            uint256[] storage openAsks = price_openAsks[
                orderID_order[orderID].pricePerUnit
            ];
            for (uint256 i = 0; i < openAsks.length; i++) {
                if (openAsks[i] == orderID) {
                    _deleteItem(i, openAsks);
                    break;
                }
            }
            for (uint256 i = 0; i < openAsksStack.length; i++) {
                if (openAsksStack[i] == orderID) {
                    _deleteItem(i, openAsksStack);
                    break;
                }
            }

            priceTokenVault -=
                (orderID_order[orderID].amount *
                    orderID_order[orderID].pricePerUnit) /
                1e18;
            IERC20(priceToken).transferFrom(
                address(this),
                orderID_order[orderID].maker,
                (orderID_order[orderID].amount *
                    orderID_order[orderID].pricePerUnit) / 1e18
            );
        }
    }

    function _skip(
        uint256[] memory array,
        uint256 n
    ) private pure returns (uint256[] memory) {
        require(
            n <= array.length,
            "Cannot skip more elements than the array length"
        );
        if (n == 0) return array;

        uint[] memory result = new uint[](array.length - n);
        for (uint i = n; i < array.length; i++) {
            result[i - n] = array[i];
        }
        return result;
    }

    function _deleteItem(uint256 index, uint256[] storage array) internal {
        require(index < array.length, "Index out of bounds");
        for (uint256 i = index; i < array.length - 1; i++) {
            array[i] = array[i + 1];
        }
        array.pop();
    }
}
