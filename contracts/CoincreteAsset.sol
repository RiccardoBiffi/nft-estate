// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract CoincreteAsset is ERC1155, Ownable {
    using Strings for string;

    address public _brickToken;

    struct TokenData {
        string name; // used to identify the token metadata
        uint256 pricePerUnit;
        uint256 APR;
        uint256 currentAmount;
        uint256 maxAmount;
    }

    mapping(address => bool) public userList;
    mapping(uint256 => TokenData) public tokenID_data;
    mapping(address => uint256) public user_tokenID;

    constructor(
        address brickToken
    ) ERC1155("https://coincrete.com/api/asset/{id}.json") {
        _brickToken = brickToken;
    }

    function mint(uint256 tokenID, uint256 amount) public {
        require(amount > 0, "Cannot mint 0 tokens");
        require(
            tokenID_data[tokenID].currentAmount + amount <=
                tokenID_data[tokenID].maxAmount,
            "Cannot mint more than max amount"
        );
        _mint(msg.sender, tokenID, amount, "");
        tokenID_data[tokenID].currentAmount += amount;
    }

    function totalSupply(uint256 tokenID) external view returns (uint256) {
        return tokenID_data[tokenID].currentAmount;
    }

    function setTotalSupply(
        uint256 tokenID,
        uint256 amount
    ) external onlyOwner {
        tokenID_data[tokenID].maxAmount = amount;
    }

    function uri(uint256 tokenId) public view override returns (string memory) {
        require(_exists(tokenId), "ERC1155: nonexistent token");
        string memory tokenUri = replaceString(
            uri(tokenId),
            tokenID_data[tokenId].name
        );
        return tokenUri;
    }

    function setTokenURI(
        uint256 tokenId,
        string memory fileName
    ) external onlyOwner {
        require(_exists(tokenId), "ERC1155: nonexistent token");
        tokenID_data[tokenId].name = fileName;
    }

    function _exists(uint256 tokenId) internal view returns (bool) {
        return bytes(tokenID_data[tokenId].name).length > 0;
    }

    function replaceString(
        string memory str,
        string memory tokenID
    ) internal pure returns (string memory) {
        str = substring(str, 0, bytes(str).length - 3);
        str = string(abi.encodePacked(str, tokenID, ".json"));
        return str;
    }

    function substring(
        string memory str,
        uint startIndex,
        uint endIndex
    ) internal pure returns (string memory) {
        bytes memory strBytes = bytes(str);
        bytes memory result = new bytes(endIndex - startIndex);
        for (uint i = startIndex; i < endIndex; i++) {
            result[i - startIndex] = strBytes[i];
        }
        return string(result);
    }
}
