"""4.2 adapters: immutable decision inputs, durable paper view, isolated final-bar runs."""
import hashlib
import json
from pathlib import Path
from .strategy import StrategyConfig, StrategyEngine, run_backtest, batch_indicators

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {"yahoo-4-1": ROOT / "fixtures/historical/bhp-4-1.json",
            "worked-eight": ROOT / "fixtures/worked-eight.json"}


def dataset(identifier):
    if identifier not in DATASETS:
        raise ValueError("Unknown dataset. Choose a published snapshot.")
    data = json.loads(DATASETS[identifier].read_text())
    actual = hashlib.sha256(json.dumps({k:v for k,v in data.items() if k != "snapshot_sha256"},
                                      sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data.get("snapshot_sha256"):
        raise ValueError("Historical snapshot checksum mismatch; do not reuse its run identity")
    return data


def metadata(data):
    return {k: v for k, v in data.items() if k != "bars"} | {
        "bar_count": len(data["bars"]),
        "start_ms": data["bars"][0]["time"] * 1000 if data["bars"] else None,
        "end_ms": data["bars"][-1]["end_ms"] if data["bars"] else None}


class Trading:
    """Rebuild paper state from original market-event ID order, never corrected latest candles.

    A next-interval quote confirms the previous sampled interval. That same quote
    cannot fill the new decision. Only a subsequent accepted, non-late quote can.
    Vendor backfill and corrections never rewrite an already issued paper decision.
    """
    def __init__(self, store):
        self.store = store
        store.db.executescript("""
        CREATE TABLE IF NOT EXISTS strategy_runs (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, snapshot_id TEXT NOT NULL,
          last_event_id INTEGER NOT NULL, result TEXT NOT NULL);
        """)
        self.engine = StrategyEngine(StrategyConfig(), store.symbol, execution="next_quote", run_id="paper-v1")
        self.cursor = 0
        self.forming = None
        self.last_source = None
        self.capture_gap = False
        self.mark_meta = {"mark_source": "No observed mark", "mark_event_id": None, "mark_available_ms": None}
        self.mark_time = None
        for event in store.events():
            self.consume(event, persist=False)
        self.save()

    def consume(self, event, persist=True):
        if event["id"] <= self.cursor:
            return
        self.cursor = event["id"]
        kind = event["kind"]
        if kind == "bar" and event["payload"].get("finalized"):
            self.mark(event["payload"]["close"], event["payload"]["start_ms"]+60000, event,
                      "Yahoo finalized minute aggregate · interval-end mark")
        if kind == "feed" and event["payload"].get("state") in ("paused", "unavailable"):
            self.capture_gap = True
            if self.forming:
                self.forming["gap"] = True
        if kind == "quote":
            source = event["source_ms"]
            if event.get("supersedes_id") or (self.last_source is not None and source < self.last_source):
                self.engine.ignore("Late quote/correction retained in market log; issued paper decisions unchanged", event_id=event["id"])
            else:
                price = event["payload"]["price"]
                # Pending decisions predate this quote. New decisions below carry
                # this event ID and cannot retroactively execute at its price.
                self.engine.execute_pending(price, source, event["received_ms"], event["id"])
                bucket = source // 60000 * 60
                if self.forming is None or bucket > self.forming["time"]:
                    first = self.forming is None
                    if self.forming:
                        self.engine.close_bar(self.forming, confirmation_ms=event["received_ms"], event_id=event["id"])
                    self.forming = {"time": bucket, "end_ms": (bucket+60)*1000,
                                    "open": price, "high": price, "low": price, "close": price,
                                    "volume": None, "eligible": not first and not self.capture_gap,
                                    "gap": self.capture_gap, "source_event_id": event["id"]}
                    self.capture_gap = False
                else:
                    self.forming["high"] = max(price, self.forming["high"])
                    self.forming["low"] = min(price, self.forming["low"])
                    self.forming["close"] = price
                self.last_source = source
                self.mark(price, source, event, "Yahoo sampled quote")
        if persist:
            self.save()

    def paper(self):
        result = self.engine.result()
        result["account"]["currency"] = "AUD" if self.store.symbol == "BHP.AX" else "quote currency"
        result["account"].update(self.mark_meta)
        return result | {"id": "paper-v1", "mode": "SIMULATED PAPER",
            "last_event_id": self.cursor, "forming_excluded": True,
            "basis": "Original captured quote availability order; sampled quote closes. First partial interval/gaps excluded. The first next-interval quote confirms; a later quote fills. Corrected chart history can differ from frozen decision inputs.",
            "forming": self.forming, "recording_start_ms": self.store.db.execute(
                "SELECT MIN(received_ms) FROM events WHERE symbol=? AND kind='quote'", (self.store.symbol,)).fetchone()[0]}

    def mark(self, price, source_ms, event, basis):
        # Known bar valuations may advance a stale quote mark, but never create
        # decisions/fills or alter earlier immutable account snapshots.
        if source_ms <= event["received_ms"] and (self.mark_time is None or source_ms >= self.mark_time):
            self.engine.mark(price, source_ms)
            self.mark_time = source_ms
            self.mark_meta = {"mark_source": basis, "mark_event_id": event["id"],
                              "mark_available_ms": event["received_ms"]}

    def save(self):
        result = self.paper()
        with self.store.db:
            self.store.db.execute("INSERT OR REPLACE INTO strategy_runs VALUES(?,?,?,?,?)",
                ("paper-v1", "paper", "original-capture-availability", self.cursor, json.dumps(result)))

    def overview(self):
        result = self.paper()
        return {"paper": result, "datasets": [metadata(dataset(key)) for key in DATASETS],
                "chart": {k: result[k] for k in ("points", "signals", "fills", "config")}}

    def backtest(self, identifier="yahoo-4-1", fast=None, slow=None, start_ms=None, end_ms=None):
        data = dataset(identifier)
        synthetic = data["synthetic"]
        config = StrategyConfig(fast=fast if fast is not None else (2 if synthetic else 5),
            slow=slow if slow is not None else (3 if synthetic else 20),
            starting_cash="1000" if synthetic else "10000", quantity=2 if synthetic else 10, fee="1")
        parameters = {"snapshot": data["snapshot_sha256"], "strategy_version": "4.2-v1",
                      "config":config.as_dict(), "fast": config.fast, "slow": config.slow,
                      "start_ms": start_ms, "end_ms": end_ms}
        run_id = "bt-" + hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()[:20]
        row = self.store.db.execute("SELECT result FROM strategy_runs WHERE id=?", (run_id,)).fetchone()
        if row:
            return json.loads(row[0])
        result = run_backtest(data["bars"], config, data["symbol"], run_id=run_id, start_ms=start_ms, end_ms=end_ms)
        result["account"]["currency"] = data["currency"]
        result.update({"id": run_id, "mode": "HISTORICAL · SIMULATED", "dataset": metadata(data),
                       "bars": data["bars"], "parameters": parameters})
        with self.store.db:
            self.store.db.execute("INSERT INTO strategy_runs VALUES(?,?,?,?,?)",
                (run_id, "backtest", identifier, 0, json.dumps(result)))
        return result

    def get_run(self, run_id):
        row = self.store.db.execute("SELECT result FROM strategy_runs WHERE id=? AND kind='backtest'", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
