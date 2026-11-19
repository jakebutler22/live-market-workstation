import copy
import math
from fastapi.testclient import TestClient
from backend.config import Config
from backend.main import create_app
from backend.store import Store
from backend.trading import Trading
from backend.strategy import StrategyConfig, StrategyEngine

BASE = 1794265200000


def quote(store, trading, minute, second, price):
    stamp = BASE + minute*60000 + second*1000
    event, _ = store.append('quote', {'id':'BHP.AX','time':stamp,'price':price}, stamp+1200000)
    if event:
        trading.consume(event)
    return event


def test_recorded_paper_cannot_fill_at_quote_used_to_confirm_close():
    store = Store(':memory:', 'BHP.AX')
    trading = Trading(store)
    trading.engine = StrategyEngine(StrategyConfig(fast=2,slow=3,starting_cash='1000',quantity=2,fee='1'), 'BHP.AX', execution='next_quote')
    closes = [12,12,10,8,12,13]
    for minute, price in enumerate(closes):
        quote(store,trading,minute,1,price)
        quote(store,trading,minute,59,price)
    trigger = quote(store,trading,6,1,14)
    result = trading.paper()
    assert len(result['signals']) == 1
    assert result['signals'][0]['event_id'] == trigger['id']
    assert result['orders'][0]['status'] == 'pending'
    assert result['account']['cash'] == '1000' and result['account']['quantity'] == 0
    fill_event = quote(store,trading,6,2,15)
    fill = trading.paper()['fills'][0]
    assert fill['event_id'] == fill_event['id'] > trigger['id']
    assert fill['price'] == '15' and fill['cash_after'] == '969'
    frozen = copy.deepcopy(trading.paper()['fills'])
    quote(store,trading,2,50,99)  # Late receipt stays in market history, not the ledger.
    assert trading.paper()['fills'] == frozen
    assert store.count() == 15
    store.close()


def test_vendor_bar_changes_current_mark_without_rewriting_decisions_or_past_equity():
    store=Store(':memory:','BHP.AX');trading=Trading(store)
    for minute in range(30):
        quote(store,trading,minute,1,60+math.sin(minute/5))
        quote(store,trading,minute,59,60+math.sin(minute/5)+.01)
    before=trading.paper()
    source=BASE+60*60000
    event,_=store.append('bar',{'start_ms':source,'open':50,'high':51,'low':49,'close':50,'volume':100,'finalized':True},source+1200000)
    trading.consume(event);after=trading.paper()
    for key in ('signals','orders','fills','equity'):
        assert after[key]==before[key]
    assert after['account']['mark']=='50'
    assert after['account']['mark_event_id']==event['id']
    assert after['account']['mark_available_ms']==event['received_ms']
    store.close()


def test_paper_restart_and_backtests_do_not_mutate_capture_or_paper(tmp_path):
    path = tmp_path/'capture.sqlite3'
    store = Store(path,'BHP.AX'); trading = Trading(store)
    for minute in range(100):
        quote(store,trading,minute,1,60+math.sin(minute/5))
        quote(store,trading,minute,59,60+math.sin(minute/5)+.01)
    original = trading.paper(); count = store.count()
    a=trading.backtest('worked-eight'); b=trading.backtest('worked-eight')
    assert a == b and a['summary']['ending_equity']=='990'
    assert trading.paper() == original and store.count()==count
    store.close()
    store=Store(path,'BHP.AX'); restored=Trading(store)
    assert restored.paper() == original
    assert restored.get_run(a['id']) == a
    assert store.count()==count
    store.close()


def test_real_http_routes_bounds_and_recorded_run(tmp_path):
    with TestClient(create_app(Config(db_path=str(tmp_path/'api.sqlite3')),start_provider=False)) as client:
        initial=client.get('/api/strategy').json()
        assert initial['paper']['account']['cash']=='10000'
        result=client.post('/api/backtests',json={'dataset_id':'yahoo-4-1'}).json()
        assert result['dataset']['synthetic'] is False and len(result['bars'])==358
        assert client.get('/api/backtests/'+result['id']).json() == result
        assert client.get('/api/strategy').json()['paper']==initial['paper']
        for body in ({'fast':5,'slow':5},{'fast':1.5},{'dataset_id':'missing'},{'start_ms':10,'end_ms':5}):
            assert client.post('/api/backtests',json=body).status_code==422
        assert client.post('/api/indicators',json={'candles':[{}]*601}).status_code==422
        assert client.get('/api/backtests/missing').status_code==404
