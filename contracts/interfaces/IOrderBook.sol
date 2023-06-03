// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOrderBook {
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

    function addBid(uint256 price, uint256 amount) external;

    function addAsk(uint256 price, uint256 amount) external;

    function marketBuy(uint256 amount) external;

    function marketSell(uint256 amount) external;

    function cancelOrder(uint256 orderID) external;

    function bestBidPrice() external view returns (uint256);

    function bestAskPrice() external view returns (uint256);

    function getLiquidityDepthByPrice(
        uint256 price
    ) external view returns (uint256);

    function getMarketOrderAveragePrice(
        uint256 amount,
        Type orderType
    ) external view returns (uint256);
}
