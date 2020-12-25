pragma solidity =0.6.10;

pragma experimental ABIEncoderV2;

import "../../contracts/MarginPool.sol";

contract MarginPoolHarness is MarginPool {
    constructor(address _addressBook) public MarginPool(_addressBook) {
    }

    mapping(address => uint256) internal assetBalanceHavoc;
    function havocSystemBalance(address _asset) public {
        assetBalance[_asset] = assetBalanceHavoc[_asset];
    }

    function transferToUser(
        address _asset,
        address _user,
        uint256 _amount
    ) public virtual override onlyController {
        require(_user != address(this), "MarginPool: cannot transfer assets to oneself");
        assetBalance[_asset] = assetBalance[_asset].sub(_amount);

        // transfer _asset _amount from pool to _user
        ERC20Interface(_asset).transfer(_user, _amount);
        emit TransferToUser(_asset, _user, _amount);
    }


     function transferToPool(
        address _asset,
        address _user,
        uint256 _amount
    ) public virtual override onlyController {
        require(_amount > 0, "MarginPool: transferToPool amount is equal to 0");
        assetBalance[_asset] = assetBalance[_asset].add(_amount);

        // transfer _asset _amount from _user to pool
        ERC20Interface(_asset).transferFrom(_user, address(this), _amount);
        emit TransferToPool(_asset, _user, _amount);
    }

}
