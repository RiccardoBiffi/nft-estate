// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface ITradable {
    function buy(uint256 amount, address exchangeToken) external;

    function cashOut() external;

    function sell(uint256 amount, address exchangeToken) external;

    function fillUp(uint256 amount, address token) external;
}
