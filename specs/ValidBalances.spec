using DummyERC20C as collateralToken
using MarginPool as pool
using Whitelist as whitelist
using OtokenHarnessA as shortOtoken
using OtokenHarnessB as longOtoken

methods {
    //The tracked asset balance of the system
    pool.getStoredBalance(address) returns uint256 envfree
    
    // ERC20 functions
    collateralToken.totalSupply() returns uint256 envfree
    shortOtoken.totalSupply() returns uint256 envfree
    collateralToken.balanceOf(address) returns uint256 envfree
    longOtoken.balanceOf(address) returns uint256 envfree

    // get the cash value for an otoken afte rexpiry
    getPayout(address, uint256) returns uint256 envfree
    
    getProceed(address, uint256) returns uint256 envfree

    //the amount of collateral in an index in a vault of an owner. i.e.,  vaults[owner][index].collateralAmounts[i]
    getVaultCollateralAmount(address, uint256, uint256)  returns uint256 envfree
    //the collateral asset of an index in a vault of an owner. i.e., vaults[owner][index].collateralAssets(i)
    getVaultCollateralAsset(address, uint256, uint256)  returns address envfree
    //the amount of long in an index in a vault of an owner. i.e.,  vaults[owner][index].longAmounts[i]
    getVaultLongAmount(address, uint256, uint256)  returns uint256 envfree
    //the long oToken in an index in a vault of an owner. i.e.,  vaults[owner][index].longOtoken[i]
    getVaultLongOtoken(address, uint256, uint256)  returns address envfree
    //the amount of long in an index in a vault of an owner. i.e.,  vaults[owner][index].shortAmounts[i]
    getVaultShortAmount(address, uint256, uint256)  returns uint256 envfree
    //the long oToken in an index in a vault of an owner. i.e.,  vaults[owner][index].shortOtoken[i]
    getVaultShortOtoken(address, uint256, uint256)  returns address envfree
	// checks if the vault is expired (true when there is an otoken which we can check expiry for)
    isVaultExpired(address, uint256) returns bool
    // checks if vault is "small" all lengths shorter than a constant
    smallVault(address, uint256, uint256) returns bool envfree
    // checks that a vault is valid
    isValidVault(address, uint256) returns bool envfree

    // The total supply of an asset. i.e., asset.totalSupply()
    assetTotalSupply(address) returns uint256 envfree
    whitelist.isWhitelistedOtoken(address) returns bool envfree
    whitelist.isWhitelistedCollateral(address) returns bool envfree
}

summaries {
    expiryTimestamp() => CONSTANT;
    burnOtoken(address, uint256) => CONSTANT;

}




rule validState(address owner, uint256 vaultId, uint256 index,  method f) 
{
    require ( shortOtoken == getVaultShortOtoken(owner, vaultId, index) &&
      longOtoken == getVaultLongOtoken(owner, vaultId, index) &&
      collateralToken == getVaultCollateralAsset(owner, vaultId, index) 
    );
    
    require ( assetTotalSupply(shortOtoken) >= (pool.getStoredBalance(shortOtoken) + getVaultShortAmount(owner, vaultId, index)) &&
      assetTotalSupply(longOtoken) >= pool.getStoredBalance(longOtoken) &&
      pool.getStoredBalance(longOtoken) >= getVaultLongAmount(owner, vaultId, index) &&
      pool.getStoredBalance(collateralToken) >= getVaultCollateralAmount(owner, vaultId, index) 
    ) ;
    callFunctionWithParameters(f, owner, vaultId, index);
    assert ( assetTotalSupply(shortOtoken) >= (pool.getStoredBalance(shortOtoken) + getVaultShortAmount(owner, vaultId, index)) &&
      assetTotalSupply(longOtoken) >= pool.getStoredBalance(longOtoken) &&
      pool.getStoredBalance(longOtoken) >= getVaultLongAmount(owner, vaultId, index) &&
      pool.getStoredBalance(collateralToken) >= getVaultCollateralAmount(owner, vaultId, index) 
    );
}



/**
@title Valid balance with respect to total collateral before expiry
@notice The sum of a collateral asset across vaults matches the assetBalance stored in the margin pool
        Vasset = { (v,i) v ∈ Vaults.  v.collateralAssets(i) = asset }
        getStoredBalance(asset) = ∑(v,i) ∈ Vasset. v.collateralAmounts[i]

This is proven by showing that change to a single vault is coherent with the change to the stored balance

*/
rule validBalanceTotalCollateral(address owner, uint256 vaultId, uint256 index, address asset, method f, address from, uint256 amount)
description "$f breaks the validity of stored balance of collateral asset"
{
    env e;
    require asset == collateralToken;
    require getVaultCollateralAsset(owner, vaultId, index) == asset;
    require !isVaultExpired(e, owner, vaultId);
    uint256 collateralVaultBefore = getVaultCollateralAmount(owner, vaultId, index);
    // todo: add pool.balance
    uint256 poolBalanceBefore = pool.getStoredBalance(asset);
    if (f.selector == settleVault(address,uint256,address).selector 
        || f.selector == redeemB(address,uint256).selector
        || f.selector == redeemA(address,uint256).selector) {
        assert true;
	} else if (f.selector == withdrawCollateral(address,uint256,address,uint256,uint256).selector) {
	    // have to require array lengths <= small const here
	    require smallVault(owner, vaultId, 1);
		address whoever;
		uint256 whatever;
		sinvoke withdrawCollateral(e, owner, vaultId, whoever, index, whatever);
    } else if (f.selector == depositCollateral(address,uint256,address,uint256,uint256).selector) {
        require (e.msg.sender != pool);
        require (owner != pool);
        sinvoke depositCollateral(e, owner, vaultId, from, index, amount);
    } else {
		calldataarg arg;
        sinvoke f(e, arg);
    }
    uint256 collateralVaultAfter = getVaultCollateralAmount(owner, vaultId, index);
    uint256 poolBalanceAfter = pool.getStoredBalance(asset);
    assert collateralVaultBefore != collateralVaultAfter => (poolBalanceAfter - poolBalanceBefore ==  collateralVaultAfter - collateralVaultBefore);
    assert poolBalanceBefore != poolBalanceAfter => (poolBalanceAfter - poolBalanceBefore ==  collateralVaultAfter - collateralVaultBefore);
}


/**
@title Valid balance of long oTokens
@notice The sum of a long asset across vaults matches the assetBalance stored in the margin pool
        Vasset = { (v,i) v ∈ Vaults.  v.longOtokens(i) = oToken}
        getStoredBalance(oToken) = ∑(v,i) ∈ Vasset. v.longAmounts[i]
*/
rule validBalanceTotalLong(address owner, uint256 vaultId, uint256 index, method f, address secondAddress, uint256 amount, address asset)
description "$f breaks the validity of stored balance of long asset"
{
    env e;
    require asset == longOtoken;
    require getVaultLongOtoken(owner, vaultId, index) == asset;
    uint256 longVaultBefore = getVaultLongAmount(owner, vaultId, index);
    uint256 poolBalanceBefore = longOtoken.balanceOf(pool);
    // the margin pool can neither be the owner nor the msg sender since it is a contract. 
    require (owner != pool);
    require (e.msg.sender != pool);

    if (f.selector == depositLongB(address,uint256,address,uint256,uint256).selector) {
        sinvoke depositLongB(e, owner, vaultId, secondAddress, index, amount);
	} else if (f.selector == mintOtokenB(address,uint256,address,uint256,uint256).selector) {
        // ignore the case where you can mint otokens directly to the margin pool
        require (secondAddress != pool);
        sinvoke mintOtokenB(e, owner, vaultId, secondAddress, index, amount);
	} else {
        callFunctionWithParameters(f, owner, vaultId, index);
    }
    
    uint256 longVaultAfter = getVaultLongAmount(owner, vaultId, index);
    uint256 poolBalanceAfter = longOtoken.balanceOf(pool);

    assert longVaultBefore != longVaultAfter => ( poolBalanceAfter - poolBalanceBefore ==  longVaultAfter - longVaultBefore);
    assert poolBalanceAfter != poolBalanceBefore => ( poolBalanceAfter - poolBalanceBefore ==  longVaultAfter - longVaultBefore);
}


/**
@title Valid supply of short oToken
@notice The sum of a short asset across vaults matches the supply of that short oToken
        Vasset = { (v,i) v ∈ Vaults.  v.shortOtokens(i) = oToken}
        oToken.totalSupply() = ∑(v,i) ∈ Vasset. v.shortAmounts[i]
*/
rule validBalanceTotalShort(address owner, uint256 vaultId, uint256 index, address oToken, method f)
description "$f breaks the validity of stored balance of short asset"
{
    env e;
    calldataarg arg;
    require oToken == shortOtoken;
    require !isVaultExpired(e, owner, vaultId);
    require getVaultShortOtoken(owner, vaultId, index) == oToken;
    uint256 shortVaultBefore = getVaultShortAmount(owner, vaultId, index);
    uint256 supplyBefore = shortOtoken.totalSupply();
    if (f.selector == settleVault(address,uint256,address).selector) {
        assert true;
    } else {
        callFunctionWithParameters(f, owner, vaultId, index);
    }
    uint256 shortVaultAfter = getVaultShortAmount(owner, vaultId, index);
    uint256 supplyAfter = shortOtoken.totalSupply();
    assert shortVaultBefore != shortVaultAfter => (supplyAfter - supplyBefore ==  shortVaultAfter - shortVaultBefore);
    assert supplyAfter != supplyBefore => ( supplyAfter - supplyBefore  ==  shortVaultAfter - shortVaultBefore);
}

// rule validBalanceTotalCollateralPostExpiry(address owner, uint256 vaultId, uint256 index, address oToken, address to, address collateral) {
    // env e;
    // require oToken == shortOtoken;
    // require collateral == collateralToken;
    // require isValidVault(owner, vaultId); 
    // require getVaultShortOtoken(owner, vaultId, index) == oToken;
    // require getVaultCollateralAsset(owner, vaultId, index) == collateral;
    // uint256 collateralVaultBefore = getProceed(owner, vaultId);
    // uint256 supplyBefore = shortOtoken.totalSupply();
    // // uint256 collateralBalanceBefore = collateralToken.balanceOf(pool);

    // sinvoke settleVault(e, owner, vaultId, to);

    // uint256 shortVaultAfter = getVaultShortAmount(owner, vaultId, index);
    // uint256 supplyAfter = shortOtoken.totalSupply();
    // // uint256 collateralBalanceAfter = collateralToken.balanceOf(pool);
    // assert shortVaultAfter == 0;
    // assert supplyAfter == supplyBefore;
    // // assert collateralBalanceBefore - collateralBalanceAfter == collateralVaultBefore;
    
    // 1. in a single tx only 1 vault can be modified 
    // 

// }

rule cantSettleUnexpiredVault(address owner, uint256 vaultId)
{
    env e;
    require !isVaultExpired(e, owner, vaultId);
    require smallVault(owner, vaultId, 1);
    address whoever;
    sinvoke settleVault(e, owner, vaultId, whoever);
    assert false; // will pass because cannot sinvoke settleVault when dealing with a non-expired vault
}


/**
@title Valid balance of the system
@notice The balance of the system at an external asset is correlated with the tracked  asset balance
        getStoredBalance(asset) ≤ asset.balanceOf(MarginPool)
*/
// XX Instantiated for collateral token
/*isValidAsset(asset) => */
invariant validBalanceOfTheSystem()
         sinvoke pool.getStoredBalance(collateralToken) == sinvoke collateralToken.balanceOf(pool)


rule onlyValidOtoken(address owner, uint256 vaultId, uint256 index, address otoken, method f) {
        require (otoken == shortOtoken || otoken == longOtoken );
        require ( getVaultShortOtoken(owner, vaultId, index) == otoken || getVaultLongOtoken(owner, vaultId, index) == otoken) 
                => whitelist.isWhitelistedOtoken(otoken);
        uint256 before = pool.getStoredBalance(otoken);
        uint256 totalSupplyBefore = assetTotalSupply(otoken);
        require !whitelist.isWhitelistedCollateral(otoken);
        callFunctionWithParameters(f, owner, vaultId, index);
        uint256 after = pool.getStoredBalance(otoken);
        uint256 totalSupplyAfter = assetTotalSupply(otoken);
        assert ( before != after || totalSupplyBefore != totalSupplyAfter) => whitelist.isWhitelistedOtoken(otoken);
}


function callFunctionWithParameters(method f, address owner, uint256 vaultId, uint256 index) {
    env e;
    uint256 amount;
    address to;
    address from;
    address receiver;
    if (f.selector == withdrawCollateral(address,uint256,address,uint256,uint256).selector) {
        withdrawCollateral(e, owner, vaultId, to, index, amount);
    }
    else if (f.selector == withdrawLongB(address,uint256,address,uint256,uint256).selector) {
        withdrawLongB(e, owner, vaultId, to, index, amount);
    }
    else if (f.selector == withdrawLongA(address,uint256,address,uint256,uint256).selector) {
        withdrawLongA(e, owner, vaultId, to, index, amount);
    }
    
    else if (f.selector == burnOtokenA(address,uint256,address,uint256,uint256).selector) {
        burnOtokenA(e, owner, vaultId, from, index, amount);
    }
    else if (f.selector == burnOtokenB(address,uint256,address,uint256,uint256).selector) {
        burnOtokenB(e, owner, vaultId, from, index, amount);
    }
    else if (f.selector == settleVault(address,uint256,address).selector) {
        settleVault(e, owner, vaultId, to);
    }
    else {
        calldataarg arg;
        sinvoke f(e,arg);
    }
}

rule OtokenInVaultIsWhitelisted(address owner, uint256 vaultId, uint256 index, address otoken, method f) {
    require (otoken == shortOtoken || otoken == longOtoken );
    require ( getVaultShortOtoken(owner, vaultId, index) == otoken || getVaultLongOtoken(owner, vaultId, index) == otoken) 
                => whitelist.isWhitelistedOtoken(otoken);
    callFunctionWithParameters(f, owner, vaultId, index);
    assert ( getVaultShortOtoken(owner, vaultId, index) == otoken || getVaultLongOtoken(owner, vaultId, index) == otoken) 
                => whitelist.isWhitelistedOtoken(otoken);
}

invariant assetIsNotOtoken(address a)
    !(whitelist.isWhitelistedOtoken(a) && whitelist.isWhitelistedCollateral(a))
   


