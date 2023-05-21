// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

//security avoid reentrancy attacks

contract OrderBook {
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

    uint256 private constant MAX_UINT = type(uint256).max;

    uint256 private _id;
    address public bookToken;
    address public priceToken;
    uint256 public marketPrice;
    uint256 public bookTokenVault;
    uint256 public priceTokenVault;

    mapping(uint256 => Order) public orderID_order;
    mapping(address => uint256) public user_ordersId;
    mapping(uint256 => uint256[]) public price_openAsks; // asks ordered by time
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
        require(
            IERC20(priceToken).balanceOf(msg.sender) >= _amount,
            "Insufficient funds"
        );

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

        while (newOrder.status != Status.Filled || bestPrice < MAX_UINT) {
            uint256 bestBidId = price_openBids[bestPrice][0];
            Order storage bestBidOrder = orderID_order[bestBidId];

            matchOrders(bestBidOrder, newOrder);

            if (bestBidOrder.status == Status.Filled) {
                deleteItem(0, price_openBids[bestPrice]);
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

            matchOrders(newOrder, bestAskOrder);

            if (bestAskOrder.status == Status.Filled) {
                deleteItem(0, price_openAsks[bestPrice]);
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
        // todo require order not to be better than best counter offer, at most equal

        //todo check if bid price is greater than best ask price
        // in this case, convert to market order to avoid price manipulation
        // and to avoid triggers buy cascade

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

        bookTokenVault += newOrder.amount;
        IERC20(bookToken).transferFrom(
            msg.sender,
            address(this),
            newOrder.amount
        );

        for (uint256 i = 0; i < price_openAsks[_price].length; i++) {
            Order storage bestAsk = orderID_order[price_openAsks[_price][0]];
            matchOrders(newOrder, bestAsk);
            if (bestAsk.status == Status.Filled) {
                deleteItem(0, price_openAsks[_price]);
                openAsksStack.pop();
            }
            if (newOrder.status != Status.Open) break;
        }

        if (newOrder.status == Status.Open) {
            price_openBids[_price].push(_id);
            insertBidInStack(_price);
        }

        user_ordersId[msg.sender] = _id;
        _id++;
    }

    function insertBidInStack(uint256 _price) private {
        uint256 j = openBidsStack.length;
        while (j > 0 && openBidsStack[j - 1] > _price) {
            openBidsStack[j] = openBidsStack[j - 1];
            j--;
        }
        openBidsStack[j] = _price;
    }

    function addAsk(uint256 _price, uint256 _amount) public {
        require(_price > 0, "Price must be greater than zero");
        require(_amount > 0, "Amount must be greater than zero");
        // todo require order not to be better than best counter offer, at most equal

        //todo check if ask is less than best bid price
        // in this case, convert to market order to avoid price manipulation
        // and to avoid triggers sell cascade

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

        priceTokenVault += newOrder.amount * newOrder.pricePerUnit;
        IERC20(priceToken).transferFrom(
            msg.sender,
            address(this),
            newOrder.amount * newOrder.pricePerUnit
        );

        for (uint256 i = 0; i < price_openBids[_price].length; i++) {
            Order storage bestBid = orderID_order[price_openBids[_price][0]];
            matchOrders(bestBid, newOrder);
            if (bestBid.status == Status.Filled) {
                deleteItem(0, price_openBids[_price]);
                openBidsStack.pop();
            }
            if (newOrder.status != Status.Open) break;
        }

        if (newOrder.status == Status.Open) {
            price_openAsks[_price].push(_id);
            insertAskInStack(_price);
        }

        user_ordersId[msg.sender] = _id;
        _id++;
    }

    function insertAskInStack(uint256 _price) private {
        uint256 j = openAsksStack.length;
        while (j > 0 && openAsksStack[j - 1] < _price) {
            openAsksStack[j] = openAsksStack[j - 1];
            j--;
        }
        openAsksStack[j] = _price;
    }

    function matchOrders(Order storage bid, Order storage ask) internal {
        if (bid.amount == ask.amount) {
            // complete match
            fillOrder(bid);
            fillOrder(ask);
        } else if (bid.amount > ask.amount) {
            // partial match, bid is larger
            bid.amount -= ask.amount;
            fillOrder(ask);
        } else {
            // partial match, ask is larger
            fillOrder(bid);
            ask.amount -= bid.amount;
        }

        marketPrice = ask.pricePerUnit;
        bookTokenVault -= ask.amount;
        priceTokenVault -= ask.amount * ask.pricePerUnit;
        IERC20(bookToken).transferFrom(address(this), ask.maker, ask.amount);
        IERC20(priceToken).transferFrom(
            address(this),
            bid.maker,
            bid.amount * ask.pricePerUnit
        );
    }

    function fillOrder(Order storage order) internal {
        order.amount = 0;
        order.status = Status.Filled;
        order.timestampClose = block.timestamp;
    }

    function bestBidPrice() public view returns (uint256) {
        if (openBidsStack.length == 0) return MAX_UINT;
        return
            orderID_order[openBidsStack[openBidsStack.length - 1]].pricePerUnit;
    }

    function bestAskPrice() public view returns (uint256) {
        if (openAsksStack.length == 0) return 0;
        return
            orderID_order[openAsksStack[openAsksStack.length - 1]].pricePerUnit;
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
                    deleteItem(i, openBids);
                    break;
                }
            }
            for (uint256 i = 0; i < openBidsStack.length; i++) {
                if (openBidsStack[i] == orderID) {
                    deleteItem(i, openBidsStack);
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
                    deleteItem(i, openAsks);
                    break;
                }
            }
            for (uint256 i = 0; i < openAsksStack.length; i++) {
                if (openAsksStack[i] == orderID) {
                    deleteItem(i, openAsksStack);
                    break;
                }
            }

            priceTokenVault -=
                orderID_order[orderID].amount *
                orderID_order[orderID].pricePerUnit;
            IERC20(priceToken).transferFrom(
                address(this),
                orderID_order[orderID].maker,
                orderID_order[orderID].amount *
                    orderID_order[orderID].pricePerUnit
            );
        }
    }

    function deleteItem(uint256 index, uint256[] storage array) internal {
        require(index < array.length, "Index out of bounds");
        for (uint256 i = index; i < array.length - 1; i++) {
            array[i] = array[i + 1];
        }
        array.pop();
    }
}
