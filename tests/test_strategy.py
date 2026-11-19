"""Labeled synthetic checks for Assignment 4.2; never live-market evidence."""
from copy import deepcopy
from decimal import Decimal
import unittest

from backend.strategy import StrategyConfig, StrategyEngine, batch_indicators, run_backtest


def fixture():
    opens = [12, 12, 10, 8, 12, 14, 11, 10]
    closes = [12, 10, 8, 12, 13, 11, 9, 9]
    return [{"time": index * 60, "end_ms": (index + 1) * 60_000,
             "open": opening, "high": max(opening, close), "low": min(opening, close),
             "close": close, "volume": 100, "eligible": True}
            for index, (opening, close) in enumerate(zip(opens, closes))]


def settings(**values):
    return StrategyConfig(fast=2, slow=3, starting_cash="1000", quantity=2, fee="1", **values)


class StrategyTests(unittest.TestCase):
    def assert_reconciles(self, account, starting_cash="1000"):
        cash, value, equity = map(Decimal, (account["cash"], account["position_value"], account["equity"]))
        realized, unrealized = map(Decimal, (account["realized_pnl"], account["unrealized_pnl"]))
        self.assertEqual(equity, cash + value)
        self.assertEqual(equity - Decimal(starting_cash), realized + unrealized)
        if account["quantity"] == 0:
            self.assertEqual(unrealized, 0)

    def test_literal_eight_bar_averages_events_fills_and_account_checkpoints(self):
        # These expected values are copied from the assignment, never calculated
        # by the code under test. Repeating 29/3 is checked to a declared tolerance.
        expected_fast = [None, "11", "9", "10", "12.5", "12", "10", "9"]
        expected_slow = [None, None, "10", "10", "11", "12", "11", "9.666666666666666666666666666666666666667"]
        expected_events = [None, None, None, None, "UP", None, "DOWN", None]
        engine = StrategyEngine(settings())
        for index, bar in enumerate(fixture()):
            engine.open_bar(bar)
            if index == 5:
                self.assertEqual({key:engine.result()["account"][key] for key in ("cash","quantity","cost_basis")},
                                 {"cash":"971","quantity":2,"cost_basis":"29"})
            if index == 7:
                self.assertEqual(engine.result()["account"]["cash"], "990")
                self.assertEqual(engine.result()["account"]["realized_pnl"], "-10")
            point = engine.close_bar(bar)
            self.assertEqual(point["fast_exact"], expected_fast[index])
            self.assertEqual(point["slow_exact"], expected_slow[index])
            self.assertEqual(point["event"], expected_events[index])
            result = engine.result()
            self.assert_reconciles(result["account"])
            if index == 4:
                self.assertEqual(result["account"]["cash"], "1000")
                self.assertEqual(result["account"]["quantity"], 0)
                self.assertEqual(result["orders"][0]["status"], "pending")
                self.assertEqual(result["fills"], [])
            if index == 5:
                self.assertEqual({key:result["account"][key] for key in ("equity","realized_pnl","unrealized_pnl")},
                                 {"equity":"993","realized_pnl":"0","unrealized_pnl":"-7"})
            if index == 6:
                self.assertEqual(result["orders"][-1]["status"], "pending")
                self.assertEqual(result["account"]["quantity"], 2)
        result = engine.finish()
        self.assertEqual({key:result["account"][key] for key in ("cash","equity","quantity","realized_pnl","unrealized_pnl","fees")},
                         {"cash":"990","equity":"990","quantity":0,"realized_pnl":"-10","unrealized_pnl":"0","fees":"2"})
        self.assertEqual((result["summary"]["return_pct"],len(result["orders"]),len(result["fills"]),result["summary"]["round_trips"]),
                         ("-1",2,2,1))
        self.assertEqual([fill["price"] for fill in result["fills"]], ["14","10"])
        self.assertEqual([fill["execution_ms"] for fill in result["fills"]], [300000,420000])
        self.assertEqual(result["fills"][1]["gross"], "20")

    def test_forming_cross_then_reverse_never_places_a_confirmed_order(self):
        bars = fixture()
        engine = StrategyEngine(settings())
        for bar in bars[:4]:
            engine.close_bar(bar)
        before = engine.result()
        for close in (13, 15, 3):
            self.assertIsNone(engine.close_bar({**bars[4], "close":close, "elapsed":False}))
        self.assertEqual(engine.result()["points"], before["points"])
        self.assertEqual(engine.result()["orders"], [])
        engine.close_bar({**bars[4], "close":3})
        self.assertEqual(engine.result()["orders"], [])
        self.assertEqual(engine.result()["signals"], [])
        # Read-only chart calculations must use the later confirmed close,
        # rather than attaching the earlier preview price to that point.
        batch = batch_indicators(bars[:4] + [{**bars[4], "close":15, "elapsed":False},
                                           {**bars[4], "close":3}], 2, 3)
        self.assertEqual(batch[-1]["close_exact"], "3")
        self.assertIsNone(batch[-1]["event"])

    def test_duplicate_confirmation_and_late_revision_preserve_decisions(self):
        bars = fixture()
        engine = StrategyEngine(settings())
        for bar in bars[:5]:
            engine.close_bar(bar)
        original = engine.result()
        engine.close_bar(bars[4])
        engine.close_bar({**bars[4], "close":1, "revision":10})
        engine.close_bar({**bars[1], "close":999})
        current = engine.result()
        for key in ("points","signals","orders","fills","equity","account"):
            self.assertEqual(current[key], original[key], key)
        self.assertEqual([item["reason"] for item in current["audit"]],
                         ["duplicate_confirmation","late_revision_ignored","late_revision_ignored"])
        engine.open_bar(bars[5])
        engine.open_bar(bars[5])
        self.assertEqual(len(engine.result()["fills"]),1)

    def test_recorded_quote_that_confirmed_close_cannot_retroactively_fill(self):
        engine = StrategyEngine(settings(), execution="next_quote")
        for index, bar in enumerate(fixture()[:5]):
            engine.close_bar(bar, confirmation_ms=bar["end_ms"]+1_200_000, event_id=index+100)
        before = engine.result()["account"]
        self.assertIsNone(engine.execute_pending(14,300000,available_ms=1_500_000,event_id=104))
        self.assertEqual(engine.result()["account"],before)
        self.assertEqual(engine.result()["orders"][0]["status"],"pending")
        fill=engine.execute_pending(14,301000,available_ms=1_501_000,event_id=105)
        self.assertEqual(fill["event_id"],105)
        self.assertEqual(fill["available_ms"],1_501_000)
        self.assertEqual(fill["cash_after"],"971")

    def test_insufficient_cash_rejects_at_execution_including_fee_without_ledger_mutation(self):
        config=StrategyConfig(fast=2,slow=3,starting_cash="28",quantity=2,fee="1")
        engine=StrategyEngine(config)
        for bar in fixture()[:5]:
            engine.close_bar(bar)
        before=engine.result()["account"]
        self.assertIsNone(engine.open_bar(fixture()[5]))
        result=engine.result()
        self.assertEqual(result["account"],before)
        self.assertEqual(result["fills"],[])
        self.assertEqual(result["orders"][0]["status"],"rejected")
        self.assertEqual(result["orders"][0]["reason"],"insufficient_cash_including_fee")
        self.assert_reconciles(result["account"],"28")

    def test_final_signal_expires_without_fill_or_forced_liquidation(self):
        result=run_backtest(fixture()[:5],settings())
        self.assertEqual(result["orders"][0]["status"],"expired")
        self.assertEqual(result["fills"],[])
        self.assertEqual(result["account"]["equity"],"1000")
        open_long=run_backtest(fixture()[:6],settings())
        self.assertEqual(open_long["account"]["quantity"],2)
        self.assertEqual(open_long["account"]["equity"],"993")
        self.assertEqual(len(open_long["fills"]),1)
        self.assertEqual(open_long["summary"]["round_trips"],0)

    def test_future_appends_alterations_and_late_revision_do_not_rewrite_prefix(self):
        bars=fixture()
        engine=StrategyEngine(settings())
        for bar in bars[:6]:
            engine.open_bar(bar);engine.close_bar(bar)
        prefix=engine.result()  # No finish: no end-of-run cleanup may leak backward.
        for bar in bars[6:]:
            engine.open_bar(bar);engine.close_bar(bar)
        engine.close_bar({**bars[2],"close":999,"revision":999})
        result=engine.result()
        for key in ("points","signals","fills","equity"):
            self.assertEqual(result[key][:len(prefix[key])],prefix[key],key)
        self.assertEqual(result["orders"][:len(prefix["orders"])],prefix["orders"])
        # Alter arbitrary future opens/highs/lows/closes. The prefix is identical.
        future=deepcopy(bars)
        for bar in future[6:]:
            bar.update(open=500,high=1000,low=1,close=700)
        altered=run_backtest(future,settings(),finalize=False)
        for key in ("points","signals","fills","equity"):
            self.assertEqual(altered[key][:len(prefix[key])],prefix[key],key)
        self.assertEqual(altered["orders"][:len(prefix["orders"])],prefix["orders"])

    def test_direct_window_batch_and_deque_incremental_agree_at_every_prefix(self):
        bars=fixture()+[{"time":600,"end_ms":660000,"open":"9.00000000002","close":"9.00000000002","volume":100},
                        {"time":660,"end_ms":720000,"open":9,"close":9,"volume":100,"eligible":False},
                        {"time":720,"end_ms":780000,"open":10,"close":10,"volume":100},
                        {"time":780,"end_ms":840000,"open":10,"close":10,"volume":100},
                        {"time":840,"end_ms":900000,"open":10,"close":10,"volume":100}]
        engine=StrategyEngine(settings())
        for index,bar in enumerate(bars):
            engine.open_bar(bar);engine.close_bar(bar)
            direct=batch_indicators(bars[:index+1],fast=2,slow=3)
            for expected,actual in zip(direct,engine.result()["points"]):
                for key in ("time","fast_exact","slow_exact","eligible","side","event"):
                    self.assertEqual(actual[key],expected[key],(index,key))
            batch=run_backtest(bars[:index+1],settings(),finalize=False)
            for key in ("points","signals","orders","fills","equity","account"):
                self.assertEqual(engine.result()[key],batch[key],(index,key))

    def test_gap_and_ineligible_bar_reset_warmup_side_without_fictional_candles(self):
        bars=fixture()[:4]
        bars += [{"time":360,"end_ms":420000,"open":20,"close":20},
                 {"time":420,"end_ms":480000,"open":21,"close":21,"gap":True},
                 {"time":480,"end_ms":540000,"open":22,"close":22},
                 {"time":540,"end_ms":600000,"open":23,"close":23},
                 {"time":600,"end_ms":660000,"open":24,"close":24}]
        result=run_backtest(bars,settings())
        self.assertEqual(len(result["points"]),9)
        self.assertIsNone(result["points"][4]["slow"])
        self.assertFalse(result["points"][5]["eligible"])
        self.assertIsNone(result["points"][7]["slow"])
        self.assertEqual(result["points"][8]["slow"],23)
        self.assertEqual(result["signals"],[])
        self.assertEqual(result["orders"],[])

    def test_decimal_precision_tolerance_and_config_validation(self):
        bars=[{"time":i*60,"open":close,"close":close}for i,close in enumerate(["10","10.0000000001","10","9.9999999999","10"])]
        result=run_backtest(bars,StrategyConfig(fast=1,slow=2))
        self.assertEqual(result["signals"],[])
        self.assertEqual(result["points"][1]["fast_exact"],"10.0000000001")
        self.assertEqual(result["points"][1]["side"],"equal")
        for params in ({"fast":2,"slow":2},{"fast":1.5},{"quantity":True},{"fee":"NaN"},{"slippage_bps":"10000"}):
            with self.subTest(params=params),self.assertRaises(ValueError):StrategyConfig(**params)

    def test_warmup_before_selected_range_never_fills_and_repeat_runs_are_isolated(self):
        bars=fixture()
        result=run_backtest(bars,settings(),start_ms=360000)
        self.assertEqual(result["fills"],[])
        self.assertEqual(result["orders"][0]["status"],"skipped")
        self.assertEqual(result["orders"][0]["reason"],"outside_selected_trading_range")
        original=StrategyEngine(settings(),run_id="other-account")
        before=original.result()
        a=run_backtest(bars,settings());b=run_backtest(deepcopy(bars),settings())
        self.assertEqual(a,b)
        self.assertEqual(original.result(),before)
        self.assertEqual(run_backtest([],settings())["summary"]["fills"],0)

    def test_slippage_and_both_fees_reconcile_without_early_execution(self):
        result=run_backtest(fixture(),settings(slippage_bps="100"))
        self.assertEqual([f["price"] for f in result["fills"]],["14.14","9.9"])
        self.assertEqual(result["account"]["cash"],"989.52")
        self.assertEqual(result["account"]["realized_pnl"],"-10.48")
        self.assert_reconciles(result["account"])
        for account in result["equity"]:self.assert_reconciles(account)


if __name__ == "__main__":
    unittest.main()
