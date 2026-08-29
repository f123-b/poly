from polyquant.smart_money import SmartMoneyClient

def test_smart_money_normalization():
    rows=SmartMoneyClient._normalize([{'rank':1,'proxyWallet':'0x1','pnl':100,'vol':1000,'verifiedBadge':True}])
    assert rows[0]['wallet']=='0x1'; assert 0<=rows[0]['trader_score']<=100; assert rows[0]['efficiency']==.1
