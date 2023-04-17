// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./interfaces/ITradable.sol";
import "./AllowTokens.sol";
import "./TokenValue.sol";

abstract contract Tradable is ERC20, ITradable, AllowTokens, TokenValue {
    uint256 public buyableTokens;
    address[] public tokenWithDeposits;
    mapping(address => uint256) public token_deposit;

    event Bought(
        address from,
        address exchangeToken,
        uint256 amountIn,
        uint256 amountOut
    );
    event CashedOut(address admin);
    event Sold(
        address from,
        uint256 amountIn,
        address exchangeToken,
        uint256 amountOut
    );
    event FilledUp(uint256 amount, address token);

    function buy(uint256 amount, address exchangeToken) public virtual {
        require(isTokenAllowed(exchangeToken), "Cannot buy with this token");
        require(amount > 0, "Amount must be more than 0 tokens");
        require(
            amount <= buyableTokens,
            "Amount must be lower than available tokens"
        );

        if (token_deposit[exchangeToken] == 0)
            tokenWithDeposits.push(exchangeToken);
        token_deposit[exchangeToken] += amount;

        uint256 valueSent = getValueFromToken(amount, exchangeToken);
        uint256 buyedTokens = getTokenFromValue(valueSent, address(this));
        buyableTokens -= buyedTokens;

        IERC20(exchangeToken).transferFrom(msg.sender, address(this), amount);
        _transfer(address(this), msg.sender, buyedTokens);

        emit Bought(msg.sender, exchangeToken, amount, buyedTokens);
    }

    function cashOut() external onlyOwner {
        for (uint256 i = 0; i < tokenWithDeposits.length; i++) {
            IERC20(tokenWithDeposits[i]).transfer(
                owner(),
                token_deposit[tokenWithDeposits[i]]
            );
            delete token_deposit[tokenWithDeposits[i]];
        }

        delete tokenWithDeposits;
        emit CashedOut(msg.sender);
    }

    function sell(uint256 amount, address exchangeToken) public virtual {
        require(isTokenAllowed(exchangeToken), "Cannot sell to this token");
        require(amount > 0, "Amount must be more than 0 tokens");

        uint256 valueSold = getValueFromToken(amount, address(this));
        uint256 tokensToSend = getTokenFromValue(valueSold, exchangeToken);
        uint256 sendableTokens = token_deposit[exchangeToken];
        require(
            tokensToSend <= sendableTokens,
            "There are not enought available tokens to sell"
        );

        token_deposit[exchangeToken] -= tokensToSend;
        if (token_deposit[exchangeToken] == 0)
            removeTokenDeposit(exchangeToken);

        buyableTokens += amount;

        _transfer(msg.sender, address(this), amount);
        IERC20(exchangeToken).transfer(msg.sender, tokensToSend);

        emit Sold(msg.sender, amount, exchangeToken, tokensToSend);
    }

    function fillUp(uint256 amount, address token) public {
        require(
            isTokenAllowed(token),
            "Cannot fill up reserves with this token"
        );
        require(amount > 0, "Amount must be more than 0 tokens");

        if (token == address(this)) {
            buyableTokens += amount;
            _transfer(msg.sender, address(this), amount);
        } else {
            if (token_deposit[token] == 0) tokenWithDeposits.push(token);
            token_deposit[token] += amount;
            IERC20(token).transferFrom(msg.sender, address(this), amount);
        }

        emit FilledUp(amount, token);
    }

    function removeTokenDeposit(address token) internal {
        for (uint256 i = 0; i < tokenWithDeposits.length; i++) {
            if (tokenWithDeposits[i] == token) {
                tokenWithDeposits[i] = tokenWithDeposits[
                    tokenWithDeposits.length - 1
                ];
                tokenWithDeposits.pop();
                break;
            }
        }
    }
}
