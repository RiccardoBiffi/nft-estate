// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

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
        Ask
    }

    enum Status {
        Open,
        Filled,
        Cancelled
    }

    uint256 private _id;
    address public bookToken;
    address public priceToken;
    uint256 public marketPrice;

    mapping(uint256 => Order) public orderID_order;
    mapping(address => uint256) public user_ordersId;
    mapping(uint256 => uint256[]) public price_openAsks; // asks ordered by time
    mapping(uint256 => uint256[]) public price_openBids; // bids ordered by time
    // stack of all open asks ordered by pricePerUnit asc, [length-1] is the best
    uint256[] public openAsksStack;
    // stack of all open bids ordered by pricePerUnit desc, [length-1] is the best
    uint256[] public openBidsStack;

    constructor(address _bookToken, address _priceToken) {
        bookToken = _bookToken;
        priceToken = _priceToken;
        marketPrice = 0;
        _id = 1;
    }

    function marketBuy(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        require(
            IERC20(priceToken).balanceOf(msg.sender) >= _amount,
            "Insufficient funds"
        );

        uint256 amount = _amount;
        uint256 i = 0;
        while (amount > 0 && i < openAsksStack.length) {
            uint256 price = openAsksStack[i];
            uint256 j = 0;
            while (amount > 0 && j < price_openAsks[price].length) {
                Order memory ask = orderID_order[price_openAsks[price][j]];
                uint256 toBuy = (amount > ask.amount) ? ask.amount : amount;
                amount -= toBuy;
                ask.amount -= toBuy;
                IERC20(bookToken).transferFrom(ask.maker, msg.sender, toBuy);
                IERC20(priceToken).transferFrom(
                    msg.sender,
                    ask.maker,
                    toBuy * ask.pricePerUnit
                );
                if (ask.amount == 0) {
                    deleteItem(j, price_openAsks[price]);
                }
                j++;
            }
            if (price_openAsks[price].length == 0) {
                deleteItem(i, openAsksStack);
            }
            i++;
        }
    }

    function marketSell(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        require(
            IERC20(bookToken).balanceOf(msg.sender) >= _amount,
            "Insufficient funds"
        );

        uint256 amount = _amount;
        uint256 i = 0;
        while (amount > 0 && i < openBidsStack.length) {
            uint256 price = openBidsStack[i];
            uint256 j = 0;
            while (amount > 0 && j < price_openBids[price].length) {
                Order memory bid = orderID_order[price_openBids[price][j]];
                uint256 toSell = (amount > bid.amount) ? bid.amount : amount;
                amount -= toSell;
                bid.amount -= toSell;
                IERC20(bookToken).transferFrom(msg.sender, bid.maker, toSell);
                IERC20(priceToken).transferFrom(
                    bid.maker,
                    msg.sender,
                    toSell * bid.pricePerUnit
                );
                if (bid.amount == 0) {
                    deleteItem(j, price_openBids[price]);
                }
                j++;
            }
            if (price_openBids[price].length == 0) {
                deleteItem(i, openBidsStack);
            }
            i++;
        }
    }

    function addBid(uint256 _price, uint256 _amount) public {
        require(_price > 0, "Price must be greater than zero");
        require(_amount > 0, "Amount must be greater than zero");

        //todo check if bid price is greater than best ask price
        // in this case, convert to market order to avoid price manipulation
        // and triggers buy cascade

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

        for (uint256 i = 0; i < price_openAsks[_price].length; i++) {
            matchOrders(newOrder, orderID_order[price_openAsks[_price][i]]);
            if (
                orderID_order[price_openAsks[_price][i]].status == Status.Filled
            ) {
                price_openAsks[_price].pop();
                openAsksStack.pop();
            }
            if (newOrder.status == Status.Filled) break;
        }

        if (newOrder.status == Status.Open) {
            price_openBids[_price].push(_id);
            insertBid(_price);
        }

        user_ordersId[msg.sender] = _id;
        _id++;
    }

    function insertBid(uint256 _price) private {
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

        //todo check if ask is less than best bid price
        // in this case, convert to market order to avoid price manipulation
        // and triggers sell cascade

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

        for (uint256 i = 0; i < price_openBids[_price].length; i++) {
            matchOrders(orderID_order[price_openBids[_price][i]], newOrder);
            if (
                orderID_order[price_openBids[_price][i]].status == Status.Filled
            ) {
                price_openBids[_price].pop();
                openBidsStack.pop();
            }
            if (newOrder.status == Status.Filled) break;
        }

        if (newOrder.status == Status.Open) {
            price_openAsks[_price].push(_id);
            insertAsk(_price);
        }

        user_ordersId[msg.sender] = _id;
        _id++;
    }

    function insertAsk(uint256 _price) private {
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
            closeOrder(bid);
            closeOrder(ask);
        } else if (bid.amount > ask.amount) {
            // partial match, bid is larger
            bid.amount -= ask.amount;
            closeOrder(ask);
        } else {
            // partial match, ask is larger
            closeOrder(bid);
            ask.amount -= bid.amount;
        }

        marketPrice = ask.pricePerUnit;
        IERC20(bookToken).transferFrom(bid.maker, ask.maker, ask.amount);
        IERC20(priceToken).transferFrom(
            ask.maker,
            bid.maker,
            bid.amount * ask.pricePerUnit
        );
    }

    function closeOrder(Order storage order) internal {
        order.amount = 0;
        order.status = Status.Filled;
        order.timestampClose = block.timestamp;
    }

    function bestBidPrice() public view returns (uint256) {
        return orderID_order[openBidsStack[0]].pricePerUnit;
    }

    function bestAskPrice() public view returns (uint256) {
        return orderID_order[openAsksStack[0]].pricePerUnit;
    }

    function removeOrder(uint256 orderID) external {
        require(
            msg.sender == orderID_order[orderID].maker,
            "Only the maker can remove the order"
        );
        // todo
        // identify order type
        // modify order status and close timestamp
        // remove orderId from price_order array and orderStack
        // return remaining assets to user
    }

    function deleteItem(uint256 index, uint256[] storage orders) internal {
        require(index < orders.length, "Index out of bounds");
        for (uint256 i = index; i < orders.length - 1; i++) {
            orders[i] = orders[i + 1];
        }
        orders.pop();
    }
}
