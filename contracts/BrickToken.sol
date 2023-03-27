// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./utils/Tradable.sol";

contract BrickToken is Tradable {
    uint256 public companyBrick;
    uint256 public aprBrick;
    uint256 public sellSpread;

    constructor(uint256 initialSupply) ERC20("Coincrete", "BRICK") {
        sellSpread = 2500; // 25%
        companyBrick = (initialSupply * 8) / 10;
        buyableTokens = (initialSupply - companyBrick) / 2;
        aprBrick = initialSupply - companyBrick - buyableTokens;
        _mint(address(this), buyableTokens);
        _mint(address(this), aprBrick); // todo send to NFT contract
        _mint(msg.sender, companyBrick);
    }

    function buy(uint256 amount, address exchangeToken) public override {
        require(isTokenAllowed(exchangeToken), "Cannot buy with this token");
        uint256 valueSent = getValueFromToken(amount, exchangeToken);
        require(valueSent >= 10 ether, "Amount bought must be more than 10$");
        super.buy(amount, exchangeToken);
    }

    function setSellSpread(uint256 spread) external onlyOwner {
        require(
            spread >= 0 && spread <= 10000,
            "Spread must be >= 0 and <= 10000"
        );
        sellSpread = spread;
    }

    function sell(uint256 amount, address exchangeToken) public override {
        uint256 amountToKeep = (amount * sellSpread) / 10000;
        uint256 amountToSell = amount - amountToKeep;
        _transfer(msg.sender, address(this), amountToKeep);

        super.sell(amountToSell, exchangeToken);
    }
}
