"""Pure deterministic candle reducer. No networking, wall clock or database access."""
from __future__ import annotations
import math
from collections import defaultdict

INTERVAL_MS = 60_000


def finite(value, name, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"invalid {name}")
    return value


def normalize_quote(raw, symbol, received_ms):
    if raw.get("id") != symbol:
        raise ValueError("unexpected source symbol")
    # yfinance protobuf int64 values are strings. Yahoo time is Unix milliseconds.
    source_ms = int(raw.get("time", 0))
    if source_ms < 946684800000 or source_ms > received_ms + 300_000:
        raise ValueError("source time missing, invalid or implausibly future")
    return {"price": finite(raw.get("price"), "price", True), "source_ms": source_ms,
            "raw": raw}


def normalize_bar(raw):
    start = int(raw["start_ms"])
    if start % INTERVAL_MS:
        raise ValueError("bar start must be a UTC minute boundary")
    result = {"start_ms": start, "finalized": bool(raw.get("finalized", True))}
    for key in ("open", "high", "low", "close"):
        result[key] = finite(raw[key], key, True)
    if result["high"] < max(result["open"], result["close"], result["low"]) or result["low"] > min(result["open"], result["close"]):
        raise ValueError("inconsistent OHLC")
    volume = raw.get("volume")
    result["volume"] = None if volume is None else finite(volume, "volume")
    if result["volume"] is not None and result["volume"] < 0:
        raise ValueError("negative volume")
    return result


class CandleEngine:
    """Events applied in stored availability/ID order; prices sorted by source time/hash."""
    def __init__(self):
        self.clock_ms = 0
        self.quotes = defaultdict(dict)
        self.bars = {}
        self.events = {}
        self.candles = {}
        self.gap_buckets = set()
        self.gap = False
        self.first_quote_receipt = {}

    def apply(self, event):
        self.clock_ms = max(self.clock_ms, event["received_ms"])
        kind, payload, event_id = event["kind"], event["payload"], event["id"]
        affected = set()
        # The recording's clock, never today's clock, closes replay intervals.
        for bucket, candle in self.candles.items():
            if not candle["elapsed"] and bucket + INTERVAL_MS <= self.clock_ms:
                affected.add(bucket)
        if kind == "quote":
            bucket = event["source_ms"] // INTERVAL_MS * INTERVAL_MS
            prior = self.events.get(event.get("supersedes_id"))
            if prior:
                old = prior["source_ms"] // INTERVAL_MS * INTERVAL_MS
                self.quotes[old].pop(prior["id"], None)
                affected.add(old)
            self.quotes[bucket][event_id] = event
            self.first_quote_receipt.setdefault(bucket, event["source_ms"])
            affected.add(bucket)
            if self.gap:
                self.gap_buckets.add(bucket)
        elif kind == "bar":
            bucket = payload["start_ms"]
            self.bars[bucket] = event
            affected.add(bucket)
        elif kind == "feed":
            if payload["state"] in ("unavailable", "paused"):
                self.gap = True
                latest_quote = max((e for e in self.events.values() if e["kind"] == "quote"), key=lambda e:e["id"], default=None)
                if latest_quote:
                    last_bucket = latest_quote["source_ms"] // INTERVAL_MS * INTERVAL_MS
                    self.gap_buckets.add(last_bucket)
                    affected.add(last_bucket)
                for bucket, candle in self.candles.items():
                    if not candle["elapsed"]:
                        self.gap_buckets.add(bucket)
                        affected.add(bucket)
            elif payload["state"] == "receiving":
                # Recovery quote was already marked using its source-time bucket.
                self.gap = False
        self.events[event_id] = event
        changes = []
        for bucket in sorted(affected):
            candle = self._candle(bucket)
            old = self.candles.get(bucket)
            if candle is None:
                continue
            comparable = {k: v for k, v in candle.items() if k not in ("revision", "last_event_id")}
            previous = {k: v for k, v in (old or {}).items() if k not in ("revision", "last_event_id")}
            if comparable != previous:
                candle["revision"] = (old or {}).get("revision", 0) + 1
                candle["last_event_id"] = event_id
                self.candles[bucket] = candle
                changes.append(candle.copy())
        return changes

    def _candle(self, bucket):
        quotes = sorted(self.quotes[bucket].values(), key=lambda e: (e["source_ms"], e["fingerprint"]))
        bar = self.bars.get(bucket)
        elapsed = bucket + INTERVAL_MS <= self.clock_ms
        if not quotes and not bar:
            return None
        official = bar and ((elapsed and bar["payload"]["finalized"]) or not quotes)
        if official:
            prices = {k: bar["payload"][k] for k in ("open", "high", "low", "close")}
        else:
            values = [e["payload"]["price"] for e in quotes]
            prices = {"open": values[0], "high": max(values), "low": min(values), "close": values[-1]}
        return {"time": bucket // 1000, "end_ms": bucket + INTERVAL_MS, **prices,
                "volume": bar["payload"]["volume"] if bar else None,
                "volume_source": "Yahoo 1m reconciliation" if bar else "unavailable",
                "volume_event_id": bar["id"] if bar else None,
                "volume_asof_ms": bar["received_ms"] if bar else None,
                "price_source": "Yahoo 1m aggregate" if official else "sampled Yahoo quotes",
                "elapsed": elapsed, "partial": not bool(official and elapsed and bar["payload"]["finalized"]),
                "capture_midinterval": bool(quotes and self.first_quote_receipt[bucket] > bucket),
                "gap": bucket in self.gap_buckets, "quote_count": len(quotes),
                "last_quote_event_id": max((e["id"] for e in quotes), default=None)}

    def history(self, limit=600):
        return [self.candles[k].copy() for k in sorted(self.candles)[-limit:]]
