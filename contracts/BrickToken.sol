// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./utils/AllowTokens.sol";
import "./utils/TokenValue.sol";

contract BrickToken is ERC20, AllowTokens, TokenValue {
    uint256 public buyableBrick;
    uint256 public companyBrick;
    uint256 public aprBrick;

    address[] public tokenWithDeposits;
    mapping(address => uint256) public token_deposit;

    event Exchange(
        address from,
        address exchangeToken,
        uint256 amountIn,
        uint256 amountBetOut
    );
    event CashOut(address admin);

    constructor(uint256 initialSupply) ERC20("Bet Token", "BET") {
        companyBrick = (initialSupply / 10) * 8;
        buyableBrick = (initialSupply - companyBrick) / 2;
        aprBrick = initialSupply - companyBrick - buyableBrick;
        _mint(address(this), buyableBrick);
        _mint(address(this), aprBrick);
        _mint(msg.sender, companyBrick);
    }

    function buy(uint256 amount, address exchangeToken) public {
        require(
            isTokenAllowed(exchangeToken),
            "Cannot buy BET with this token"
        );
        require(amount > 0, "Amount must be more than 0 tokens");

        tokenWithDeposits.push(exchangeToken);
        token_deposit[exchangeToken] = amount;

        uint256 valueSent = getValueFromToken(amount, exchangeToken);
        uint256 buyedBetTokens = getTokenFromValue(valueSent, address(this));
        buyableBrick -= buyedBetTokens;

        IERC20(exchangeToken).transferFrom(msg.sender, address(this), amount);
        _transfer(address(this), msg.sender, buyedBetTokens);

        emit Exchange(msg.sender, exchangeToken, amount, buyedBetTokens);
    }

    function cashOut() public onlyOwner {
        for (uint256 i = 0; i < tokenWithDeposits.length; i++) {
            IERC20(tokenWithDeposits[i]).transfer(
                owner(),
                token_deposit[tokenWithDeposits[i]]
            );
            delete token_deposit[tokenWithDeposits[i]];
        }

        delete tokenWithDeposits;
        emit CashOut(msg.sender);
    }

    function setTokenPriceFeed(
        address token,
        address priceFeed
    ) public override onlyOwner {
        super.setTokenPriceFeed(token, priceFeed);
    }
}
