import asyncio
from polyquant.smart_money import SmartMoneyClient


def test_demo_smart_money_profile_and_flow():
    client=SmartMoneyClient(demo=True)
    profile=asyncio.run(client.profile('demo'))
    flow=asyncio.run(client.market_flow('demo-market'))
    assert 0<=profile['win_rate']<=1
    assert profile['closed_positions']>0
    assert -1<=flow['score']<=1
    assert flow['demo'] is True
