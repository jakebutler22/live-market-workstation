"""Reproducible independent Assignment 4.2 numerical verification.

No provider access and no canonical database writes. pandas is verification-only;
production strategy arithmetic uses Decimal. Exit nonzero on any mismatch.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from backend.strategy import StrategyConfig, StrategyEngine, batch_indicators, run_backtest

TOLERANCE = 1e-10
KEYS = ("time", "fast_exact", "slow_exact", "eligible", "side", "event")


def worked_bars():
    opens = [12, 12, 10, 8, 12, 14, 11, 10]
    closes = [12, 10, 8, 12, 13, 11, 9, 9]
    return [{"time": i * 60, "end_ms": (i + 1) * 60000, "open": opening,
             "high": max(opening, close), "low": min(opening, close), "close": close,
             "volume": 100, "eligible": True}
            for i, (opening, close) in enumerate(zip(opens, closes))]


def independent_reference(bars, fast, slow):
    """Separate pandas rolling calculation and crossover state machine.

    Reference segmentation repeats the stated eligibility policy, rather than
    calling production helpers. Each valid segment uses trailing, uncentered,
    full-window pandas means; null warm-up positions remain null.
    """
    accepted, groups, group, seen, previous = [], [], [], set(), None
    for bar in bars:
        if bar.get("elapsed", True) is False or bar.get("confirmed", True) is False or bar.get("forming", False):
            continue
        stamp = int(bar["time"])
        if stamp in seen or (previous is not None and stamp < previous):
            continue
        qualifies = bool(bar.get("eligible", True)) and not bool(bar.get("gap", False))
        if previous is not None and stamp - previous != 60:
            if group: groups.append(group)
            group = []
        accepted.append({"time": stamp, "eligible": qualifies, "close": float(bar["close"])})
        if not qualifies:
            if group: groups.append(group)
            group = []
        else:
            group.append(len(accepted)-1)
        seen.add(stamp)
        previous = stamp
    if group: groups.append(group)
    for point in accepted:
        point.update(fast=None, slow=None, event=None, side="warming")
    for indexes in groups:
        series = pd.Series([accepted[index]["close"] for index in indexes], dtype="float64")
        short = series.rolling(window=fast, min_periods=fast, center=False).mean().tolist()
        long = series.rolling(window=slow, min_periods=slow, center=False).mean().tolist()
        previous_side = 0
        for offset, index in enumerate(indexes):
            point = accepted[index]
            a, b = short[offset], long[offset]
            point["fast"] = None if math.isnan(a) else a
            point["slow"] = None if math.isnan(b) else b
            if point["fast"] is None or point["slow"] is None:
                continue
            difference = a - b
            side = 1 if difference > TOLERANCE else -1 if difference < -TOLERANCE else 0
            point["side"] = "above" if side > 0 else "below" if side < 0 else "equal"
            if side:
                if previous_side and side != previous_side:
                    point["event"] = "UP" if side > 0 else "DOWN"
                previous_side = side
    return accepted


def compare_reference(name, bars, fast, slow):
    production = batch_indicators(bars, fast, slow)
    reference = independent_reference(bars, fast, slow)
    mismatches, max_difference = [], 0.0
    if len(production) != len(reference):
        mismatches.append({"reason":"point_count", "production":len(production), "reference":len(reference)})
    for actual, expected in zip(production, reference):
        for key in ("fast", "slow"):
            if actual[key] is None or expected[key] is None:
                if actual[key] != expected[key]:
                    mismatches.append({"time":actual["time"], "field":key, "reason":"warmup_null_mismatch"})
            else:
                difference = abs(actual[key]-expected[key])
                max_difference = max(max_difference, difference)
                if difference > TOLERANCE:
                    mismatches.append({"time":actual["time"], "field":key, "difference":difference})
        for key in ("time", "eligible", "event", "side"):
            if actual[key] != expected[key]:
                mismatches.append({"time":actual["time"], "field":key, "actual":actual[key], "expected":expected[key]})
    return {"name":name, "classification":"SYNTHETIC numerical fixture" if name != "recorded_historical" else "Recorded historical input",
            "fast":fast, "slow":slow, "input":bars, "reference":reference,
            "production":production, "maximum_absolute_difference":max_difference,
            "tolerance":TOLERANCE, "mismatches":mismatches,
            "confirmed_crosses":[{"time":p["time"],"direction":p["event"]}for p in production if p["event"]],
            "passed":not mismatches}


def prefix_comparison(bars):
    config = StrategyConfig(fast=2, slow=3, starting_cash="1000", quantity=2, fee="1")
    engine = StrategyEngine(config)
    mismatches = []
    for index, bar in enumerate(bars):
        engine.open_bar(bar)
        engine.close_bar(bar)
        incremental = engine.result()
        batch = run_backtest(bars[:index+1], config, finalize=False)
        direct = batch_indicators(bars[:index+1], fast=2, slow=3)
        for key in ("points", "signals", "orders", "fills", "equity", "account"):
            if incremental[key] != batch[key]:
                mismatches.append({"prefix_bars":index+1, "field":key})
        for actual, expected in zip(incremental["points"], direct):
            for key in KEYS:
                if actual[key] != expected[key]:
                    mismatches.append({"prefix_bars":index+1,"field":key,"time":actual["time"]})
    return {"algorithms":{"incremental":"bounded Decimal deque with trailing sums",
                           "batch":"separate direct-window slicing/sums; shared authoritative account"},
            "prefixes_compared":len(bars), "includes":"warm-up, equality, opposite crosses, absent interval, excluded gap, decimal closes",
            "mismatches":mismatches, "passed":not mismatches}


def literal_accounting():
    expected = {"fast":[None,11,9,10,12.5,12,10,9],
                "slow":[None,None,10,10,11,12,11,"29/3"],
                "events":[None,None,None,None,"UP",None,"DOWN",None],
                "bar_5_close":{"cash":"1000","quantity":0,"order_status":"pending"},
                "bar_6_open":{"cash":"971","quantity":2,"cost_basis":"29"},
                "bar_6_close":{"equity":"993","realized_pnl":"0","unrealized_pnl":"-7"},
                "bar_7_close":{"quantity":2,"order_status":"pending"},
                "bar_8_open":{"cash":"990","quantity":0,"realized_pnl":"-10"},
                "final":{"cash":"990","equity":"990","quantity":0,"realized_pnl":"-10","unrealized_pnl":"0","fees":"2"},
                "summary":{"orders":2,"fills":2,"round_trips":1,"return_pct":"-1"}}
    config = StrategyConfig(fast=2,slow=3,starting_cash="1000",quantity=2,fee="1")
    engine = StrategyEngine(config)
    actual = {}
    mismatches = []
    for index, bar in enumerate(worked_bars()):
        engine.open_bar(bar)
        if index in (5,7):
            label = f"bar_{index+1}_open"
            actual[label] = {key:engine.result()["account"][key]for key in expected[label]}
        engine.close_bar(bar)
        result = engine.result()
        if index in (4,5,6):
            label = f"bar_{index+1}_close"
            actual[label] = {key:result["orders"][-1]["status"] if key=="order_status" else result["account"][key]
                             for key in expected[label]}
        account = result["account"]
        equity, cash, value = [Decimal(account[key])for key in ("equity","cash","position_value")]
        realized, unrealized = [Decimal(account[key])for key in ("realized_pnl","unrealized_pnl")]
        if equity != cash+value or equity-1000 != realized+unrealized or (not account["quantity"] and unrealized):
            mismatches.append({"reason":"account_reconciliation","bar":index+1})
    result = engine.finish()
    actual["fast"] = [p["fast"]for p in result["points"]]
    actual["slow"] = [p["slow"]for p in result["points"]]
    actual["events"] = [p["event"]for p in result["points"]]
    actual["final"] = {key:result["account"][key]for key in expected["final"]}
    actual["summary"] = {key:result["summary"][key]for key in expected["summary"]}
    for key in expected:
        if key == "slow":
            target = [None,None,10,10,11,12,11,29/3]
            if actual[key] != target:mismatches.append({"field":key})
        elif actual[key] != expected[key]:mismatches.append({"field":key})
    return {"classification":"SYNTHETIC mandatory assignment fixture",
            "expected_source":"Literal values supplied in the user's Assignment 4.2 prompt; not generated by production",
            "expected":expected,"actual":actual,"orders":result["orders"],"fills":result["fills"],
            "mismatches":mismatches,"passed":not mismatches}


def causal_check():
    config=StrategyConfig(fast=2,slow=3,starting_cash="1000",quantity=2)
    bars=worked_bars()
    engine=StrategyEngine(config)
    for bar in bars[:6]:engine.open_bar(bar);engine.close_bar(bar)
    prefix=engine.result()
    for bar in bars[6:]:engine.open_bar(bar);engine.close_bar(bar)
    engine.close_bar({**bars[2],"close":999,"revision":99})
    full=engine.result()
    changed=deepcopy(bars)
    for bar in changed[6:]:bar.update(open=500,high=1000,low=1,close=700)
    altered=run_backtest(changed,config,finalize=False)
    unchanged=all(full[key][:len(prefix[key])]==prefix[key] and altered[key][:len(prefix[key])]==prefix[key]
                  for key in ("points","signals","orders","fills","equity"))
    repeat=run_backtest(bars,config)==run_backtest(deepcopy(bars),config)
    return {"cutoff":"after synthetic bar 6 closes, before finish cleanup",
            "appended_and_altered_future_leaves_prefix_unchanged":unchanged,
            "late_revision_reason":full["audit"][-1]["reason"],
            "repeat_run_economic_and_identity_results_equal":repeat,
            "passed":unchanged and repeat and full["audit"][-1]["reason"]=="late_revision_ignored"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",type=Path,help="Optional frozen historical JSON list or {bars:[...]} to compare")
    parser.add_argument("--output",type=Path,default=ROOT/"submissions/4.2/evidence/numerical-verification.json")
    arguments=parser.parse_args()
    bars=worked_bars()
    extra=[{"time":600,"end_ms":660000,"open":"9.00000000002","close":"9.00000000002"},
           {"time":660,"end_ms":720000,"open":9,"close":9,"gap":True},
           *[{"time":720+i*60,"end_ms":780000+i*60000,"open":10,"close":10}for i in range(4)]]
    fixed=[]
    for i in range(64):
        close = str(Decimal("60.1234567890123") + Decimal((i*7)%19-9)/Decimal(100))
        fixed.append({"time":i*60,"open":close,"close":close,"volume":100})
    checks=[compare_reference("eight_bar",bars,2,3),
            compare_reference("ties_gaps_precision",bars+extra,2,3),
            compare_reference("default_windows_fixed_series",fixed,5,20)]
    dataset_info=None
    if arguments.dataset:
        data=arguments.dataset.read_bytes();payload=json.loads(data)
        historical=payload if isinstance(payload,list) else payload["bars"]
        checks.append(compare_reference("recorded_historical",historical,5,20))
        dataset_info={"file":str(arguments.dataset.relative_to(ROOT)) if arguments.dataset.is_relative_to(ROOT) else arguments.dataset.name,
                      "sha256":hashlib.sha256(data).hexdigest(),"bars":len(historical)}
    value={"assignment":"4.2","recorded_at_utc":datetime.now(timezone.utc).isoformat(),
           "python":platform.python_version(),"reference_library":"pandas","reference_version":pd.__version__,
           "production":"Python Decimal at 40-digit calculation precision; no pandas production dependency",
           "references":[{"title":"Fidelity simple moving average and moving-average crossover definition","url":"https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma"},
                         {"title":"pandas Series.rolling trailing full-window means","url":"https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html"}],
           "reference_definition":"Series.rolling(window=N,min_periods=N,center=False).mean(); separately coded persistent-side crossover; equality tolerance 1e-10",
           "reference_comparisons":checks,"batch_incremental":prefix_comparison(bars+extra),
           "mandatory_accounting":literal_accounting(),"causality":causal_check(),"historical_dataset":dataset_info}
    value["passed"]=all(check["passed"]for check in checks) and all(value[key]["passed"]for key in ("batch_incremental","mandatory_accounting","causality"))
    arguments.output.parent.mkdir(parents=True,exist_ok=True)
    arguments.output.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"passed":value["passed"],"reference_cases":len(checks),
                      "maximum_absolute_difference":max(check["maximum_absolute_difference"]for check in checks),
                      "prefixes":value["batch_incremental"]["prefixes_compared"],
                      "worked_final":value["mandatory_accounting"]["actual"]["final"],
                      "evidence":str(arguments.output.relative_to(ROOT)) if arguments.output.is_relative_to(ROOT) else str(arguments.output)},indent=2))
    return 0 if value["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
