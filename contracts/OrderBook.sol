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
        Ask,
        MarketBuy,
        MarketSell
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
        _id = 1;
        bookToken = _bookToken;
        priceToken = _priceToken;
        marketPrice = 0;
    }

    function marketBuy(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        uint256 bestPrice = bestBidPrice();
        require(
            // todo this check is not very precise, should consider all involved bids
            IERC20(priceToken).balanceOf(msg.sender) >= _amount * bestPrice,
            "Insufficient funds"
        );

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

        while (
            newOrder.status != Status.Filled ||
            price_openBids[bestPrice].length > 0
        ) {
            bestPrice = bestBidPrice();
            uint256 bestBidId = price_openBids[bestPrice][0];
            Order storage bestBidOrder = orderID_order[bestBidId];

            matchOrders(bestBidOrder, newOrder);

            //todo try to move this check on function matchOrders()
            if (orderID_order[bestBidId].status == Status.Filled) {
                deleteItem(0, price_openBids[bestPrice]);
                openBidsStack.pop();
            }
        }

        //todo other checks?
    }

    function marketSell(uint256 _amount) public {
        require(_amount > 0, "Amount must be greater than zero");
        uint256 bestPrice = bestAskPrice();
        require(
            IERC20(bookToken).balanceOf(msg.sender) >= _amount,
            "Insufficient funds"
        );

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

        while (
            newOrder.status != Status.Filled ||
            price_openAsks[bestPrice].length > 0
        ) {
            bestPrice = bestAskPrice();
            uint256 bestAskId = price_openAsks[bestPrice][0];
            Order storage bestAskOrder = orderID_order[bestAskId];

            matchOrders(newOrder, bestAskOrder);

            if (orderID_order[bestAskId].status == Status.Filled) {
                deleteItem(0, price_openAsks[bestPrice]);
                openAsksStack.pop();
            }
        }

        //todo other checks?
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
