"""Assignment 4.2: causal SMA decisions and a shared Decimal simulated account.

Production incremental indicators use a bounded deque; historical indicators use
an independent direct-window implementation. Both feed the same decision/ledger
implementation. This module has no network, database, clock or UI dependencies.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json

PRECISION = 40
ZERO = Decimal(0)


def decimal(value, name="value", *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite decimal") from exc
    if not result.is_finite() or (positive and result <= 0) or (nonnegative and result < 0):
        raise ValueError(f"invalid {name}")
    return result


def exact(value):
    if value is None:
        return None
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@dataclass(frozen=True)
class StrategyConfig:
    fast: int = 5
    slow: int = 20
    starting_cash: str = "10000"
    quantity: int = 10
    fee: str = "1"
    slippage_bps: str = "0"
    tolerance: str = "0.0000000001"
    interval_seconds: int = 60

    def __post_init__(self):
        for key in ("fast", "slow", "quantity", "interval_seconds"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if not 1 <= self.fast < self.slow <= 1000:
            raise ValueError("SMA windows require 1 <= fast < slow <= 1000")
        if self.quantity > 1_000_000:
            raise ValueError("quantity must not exceed 1000000")
        for key in ("starting_cash", "fee", "slippage_bps", "tolerance"):
            object.__setattr__(self, key, exact(decimal(getattr(self, key), key, nonnegative=True)))
        if decimal(self.slippage_bps) >= 10_000:
            raise ValueError("slippage_bps must be below 10000")
        if decimal(self.tolerance) > Decimal("0.01"):
            raise ValueError("tolerance must not exceed 0.01")

    def as_dict(self):
        return asdict(self)


def config_value(config):
    return config if isinstance(config, StrategyConfig) else StrategyConfig(**(config or {}))


def bar_time(bar):
    value = bar["time"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise ValueError("bar time must be integer UTC seconds")
    return int(value)


def eligible(bar):
    # A flagged capture gap is excluded; partial sampled coverage alone is not
    # silently called exchange-complete and may be explicitly eligible by adapter.
    return bool(bar.get("eligible", True)) and not bool(bar.get("gap", False))


def confirmed(bar):
    return bar.get("elapsed", True) is not False and bar.get("confirmed", True) is not False and not bar.get("forming", False)


def fingerprint(bar):
    useful = {key: bar.get(key) for key in ("time", "end_ms", "open", "high", "low", "close", "volume", "eligible", "gap")}
    return hashlib.sha256(json.dumps(useful, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def batch_sma(bars, config=None):
    """Independent historical algorithm: direct trailing-window sums, no deque.

    Never sorts/forward-fills inputs. Duplicate and late confirmations cannot
    rewrite a previously emitted point. Missing minutes restart both windows.
    """
    config = config_value(config)
    output, segment, seen = [], [], set()
    previous = None
    for bar in bars:
        if not confirmed(bar):
            continue
        stamp = bar_time(bar)
        if stamp in seen or (previous is not None and stamp < previous):
            continue
        if previous is not None and stamp - previous != config.interval_seconds:
            segment = []
        is_eligible = eligible(bar)
        price = decimal(bar["close"], "close", positive=True)
        if not is_eligible:
            segment = []
        else:
            segment.append(price)
        with localcontext() as context:
            context.prec = PRECISION
            fast = sum(segment[-config.fast:], ZERO) / config.fast if len(segment) >= config.fast else None
            slow = sum(segment[-config.slow:], ZERO) / config.slow if len(segment) >= config.slow else None
        output.append({"time": stamp, "fast_exact": exact(fast), "slow_exact": exact(slow), "eligible": is_eligible})
        seen.add(stamp)
        previous = stamp
    return output


class StrategyEngine:
    def __init__(self, config=None, symbol="TEST", execution="next_open", run_id=None):
        self.config = config_value(config)
        if execution not in ("next_open", "next_quote"):
            raise ValueError("execution must be next_open or next_quote")
        self.symbol, self.execution = symbol, execution
        identity = json.dumps([symbol, execution, self.config.as_dict()], sort_keys=True, separators=(",", ":"))
        self.run_id = run_id or hashlib.sha256(identity.encode()).hexdigest()[:16]
        self.points, self.signals, self.orders, self.fills, self.equity, self.audit = [], [], [], [], [], []
        self._window = deque(maxlen=self.config.slow)
        self._last_time = None
        self._seen = {}
        self._side = 0
        self._pending = None
        self._cash = decimal(self.config.starting_cash)
        self._quantity = 0
        self._basis = ZERO
        self._realized = ZERO
        self._fees = ZERO
        self._mark = None
        self._mark_ms = None
        self._round_trips = 0
        self._finished = False

    def ignore(self, reason, event_id=None, **context):
        self.audit.append({"reason": reason, "event_id": event_id, **context})

    def mark(self, price, source_ms):
        price = decimal(price, "mark", positive=True)
        source_ms = int(source_ms)
        if self._mark_ms is not None and source_ms < self._mark_ms:
            self.ignore("late_mark_ignored", source_ms=source_ms)
            return self._account()
        self._mark, self._mark_ms = price, source_ms
        return self._account()

    def _account(self):
        with localcontext() as context:
            context.prec = PRECISION
            value = (self._mark or ZERO) * self._quantity
            unrealized = value - self._basis if self._quantity else ZERO
            equity = self._cash + value
            return {"cash": exact(self._cash), "quantity": self._quantity,
                    "cost_basis": exact(self._basis), "mark": exact(self._mark),
                    "mark_ms": self._mark_ms, "mark_source_ms": self._mark_ms,
                    "position_value": exact(value), "realized_pnl": exact(self._realized),
                    "unrealized_pnl": exact(unrealized), "equity": exact(equity),
                    "fees": exact(self._fees), "currency": "quote currency", "simulated": True}

    def execute_pending(self, price, execution_ms, available_ms=None, event_id=None):
        if self._finished or self._pending is None:
            return None
        order = self._pending
        if event_id is not None and str(event_id) == str(order["confirmation_event_id"]):
            self.ignore("confirmation_event_cannot_fill_its_new_order", event_id, order_id=order["id"])
            return None
        available_ms = int(execution_ms if available_ms is None else available_ms)
        if available_ms < order["submitted_ms"]:
            self.ignore("execution_available_before_decision", event_id, order_id=order["id"])
            return None
        raw_price = decimal(price, "execution price", positive=True)
        execution_ms = int(execution_ms)
        if execution_ms < order["source_ms"]:
            self.ignore("execution_source_before_confirmation_interval", event_id, order_id=order["id"])
            return None
        with localcontext() as context:
            context.prec = PRECISION
            fraction = decimal(self.config.slippage_bps) / 10_000
            fill_price = raw_price * (1 + fraction if order["side"] == "BUY" else 1 - fraction)
            fee = decimal(self.config.fee)
            quantity = order["quantity"]
            gross = fill_price * quantity
            if order["side"] == "BUY":
                if self._quantity:
                    order.update(status="rejected", reason="position_already_open")
                elif self._cash < gross + fee:
                    order.update(status="rejected", reason="insufficient_cash_including_fee")
                else:
                    self._cash -= gross + fee
                    self._quantity = quantity
                    self._basis = gross + fee
            elif self._quantity != quantity or not quantity:
                order.update(status="rejected", reason="position_unavailable")
            else:
                net = gross - fee
                self._cash += net
                self._realized += net - self._basis
                self._quantity, self._basis = 0, ZERO
                self._round_trips += 1
            self._pending = None
            if order["status"] == "rejected":
                return None
            self._fees += fee
            self.mark(raw_price, execution_ms)
            fill_id = f"{order['id']}:fill"
            fill = {"id": fill_id, "order_id": order["id"], "signal_id": order["signal_id"],
                    "symbol": self.symbol, "side": order["side"], "quantity": quantity,
                    "price": exact(fill_price), "fee": exact(fee), "gross": exact(gross),
                    "execution_ms": execution_ms, "available_ms": available_ms,
                    "event_id": event_id, "time": execution_ms // 1000,
                    "cash_after": exact(self._cash), "quantity_after": self._quantity,
                    "cost_basis_after": exact(self._basis), "realized_pnl_after": exact(self._realized)}
            self.fills.append(fill)
            order.update(status="filled", reason=None, fill_id=fill_id)
            return deepcopy(fill)

    def open_bar(self, bar):
        if self.execution != "next_open" or not eligible(bar):
            return None
        stamp = bar_time(bar)
        return self.execute_pending(bar["open"], stamp * 1000,
                                    available_ms=stamp * 1000, event_id=f"bar:{stamp}:open")

    def close_bar(self, bar, allow_trade=True, confirmation_ms=None, event_id=None):
        return self._close(bar, allow_trade, confirmation_ms, event_id)

    def _close(self, bar, allow_trade=True, confirmation_ms=None, event_id=None, averages=None):
        if self._finished:
            raise ValueError("finished strategy cannot accept new bars; start a new run")
        stamp = bar_time(bar)
        if not confirmed(bar):
            self.ignore("forming_candle_excluded", event_id, time=stamp)
            return None
        prior = self._seen.get(stamp)
        signature = fingerprint(bar)
        if prior is not None:
            self.ignore("duplicate_confirmation" if prior == signature else "late_revision_ignored", event_id, time=stamp)
            return None
        if self._last_time is not None and stamp < self._last_time:
            self.ignore("late_bar_ignored", event_id, time=stamp)
            return None
        price = decimal(bar["close"], "close", positive=True)
        end_ms = int(bar.get("end_ms", (stamp + self.config.interval_seconds) * 1000))
        if end_ms != (stamp + self.config.interval_seconds) * 1000:
            raise ValueError("bar end must match configured interval")
        confirmation_ms = end_ms if confirmation_ms is None else int(confirmation_ms)
        if confirmation_ms < end_ms:
            raise ValueError("candle cannot be confirmed before its source interval ends")
        event_id = event_id if event_id is not None else f"bar:{stamp}:close"
        is_eligible = eligible(bar)
        gap = self._last_time is not None and stamp - self._last_time != self.config.interval_seconds
        if gap or not is_eligible:
            self._window.clear()
            self._side = 0
        if is_eligible:
            self._window.append(price)
        with localcontext() as context:
            context.prec = PRECISION
            if averages is None:
                window = list(self._window)
                fast = sum(window[-self.config.fast:], ZERO) / self.config.fast if len(window) >= self.config.fast else None
                slow = sum(window, ZERO) / self.config.slow if len(window) >= self.config.slow else None
            else:
                fast, slow = averages
            event, side_name = None, "warming"
            if fast is not None and slow is not None:
                difference = fast - slow
                side = 1 if difference > decimal(self.config.tolerance) else -1 if difference < -decimal(self.config.tolerance) else 0
                side_name = "above" if side == 1 else "below" if side == -1 else "equal"
                if side:
                    if self._side and side != self._side:
                        event = "UP" if side == 1 else "DOWN"
                    self._side = side
            point = {"time": stamp, "fast": float(fast) if fast is not None else None,
                     "slow": float(slow) if slow is not None else None,
                     "fast_exact": exact(fast), "slow_exact": exact(slow),
                     "close": float(price), "close_exact": exact(price), "event": event,
                     "side": side_name, "eligible": is_eligible, "confirmed": True,
                     "confirmation_ms": confirmation_ms, "event_id": event_id}
            self.points.append(point)
            self._seen[stamp], self._last_time = signature, stamp
            if event:
                signal_id = f"{self.run_id}:signal:{stamp}:{event}"
                order_id = f"{signal_id}:order"
                signal = {"id": signal_id, "symbol": self.symbol, "direction": event,
                          "time": stamp, "candle_time": stamp, "source_ms": end_ms,
                          "confirmation_ms": confirmation_ms, "event_id": event_id,
                          "fast": point["fast"], "slow": point["slow"],
                          "fast_exact": exact(fast), "slow_exact": exact(slow), "order_id": order_id}
                self.signals.append(signal)
                side = "BUY" if event == "UP" else "SELL"
                quantity = self.config.quantity if side == "BUY" else self._quantity
                order = {"id": order_id, "signal_id": signal_id, "symbol": self.symbol,
                         "side": side, "quantity": quantity, "submitted_ms": confirmation_ms,
                         "source_ms": end_ms, "confirmation_event_id": event_id,
                         "candle_time": stamp, "status": "pending", "reason": None, "fill_id": None}
                if not allow_trade:
                    order.update(status="skipped", reason="outside_selected_trading_range")
                elif self._pending is not None:
                    order.update(status="skipped", reason="another_order_pending")
                elif side == "BUY" and self._quantity:
                    order.update(status="skipped", reason="already_long_no_pyramiding")
                elif side == "SELL" and not self._quantity:
                    order.update(status="skipped", reason="flat_no_shorting")
                else:
                    self._pending = order
                self.orders.append(order)
            self.mark(price, end_ms)
            account = self._account()
            self.equity.append({"time": stamp, "source_ms": end_ms, "available_ms": confirmation_ms,
                                "event_id": event_id, **account})
            return deepcopy(point)

    def finish(self):
        if not self._finished:
            if self._pending:
                self._pending.update(status="expired", reason="end_of_recording_no_subsequent_eligible_price")
                self._pending = None
            self._finished = True
        return self.result()

    def result(self):
        account = self._account()
        with localcontext() as context:
            context.prec = PRECISION
            start = decimal(self.config.starting_cash)
            total = decimal(account["equity"]) - start
            summary = {"starting_equity": exact(start), "ending_equity": account["equity"],
                       "total_pnl": exact(total), "return_pct": exact(total / start * 100) if start else None,
                       "orders": len(self.orders), "fills": len(self.fills),
                       "round_trips": self._round_trips, "open_position": self._quantity,
                       "signals": len(self.signals), "fees": exact(self._fees),
                       "eligible_bars": sum(p["eligible"] for p in self.points),
                       "warmup_remaining": max(0, self.config.slow - len(self._window)),
                       "finished": self._finished}
        return deepcopy({"run_id": self.run_id, "symbol": self.symbol, "execution": self.execution,
                         "mode": "SIMULATED", "config": self.config.as_dict(), "points": self.points,
                         "signals": self.signals, "orders": self.orders, "fills": self.fills,
                         "equity": self.equity, "account": account, "summary": summary, "audit": self.audit})


def run_backtest(bars, config=None, symbol="TEST", run_id=None, start_ms=None, end_ms=None, *, finalize=True):
    """Final OHLC assumption: bar available at close; pending fills at next open.

    Input order is authoritative. Earlier bars may warm up the selected range,
    but cannot fill or place actionable orders before start_ms. end_ms is exclusive
    by candle-start time. No forced liquidation; the last known close marks longs.
    """
    config = config_value(config)
    bars = list(bars)
    if len(bars) > 100_000:
        raise ValueError("backtest is bounded to 100000 input bars")
    if start_ms is not None and end_ms is not None and start_ms >= end_ms:
        raise ValueError("start_ms must precede end_ms")
    selected = [bar for bar in bars if end_ms is None or bar_time(bar) * 1000 < end_ms]
    averages = {point["time"]: point for point in batch_sma(selected, config)}
    engine = StrategyEngine(config, symbol, execution="next_open", run_id=run_id)
    for bar in selected:
        stamp = bar_time(bar)
        if not confirmed(bar) or stamp in engine._seen or (engine._last_time is not None and stamp < engine._last_time):
            engine.close_bar(bar, allow_trade=False)
            continue
        trade = start_ms is None or stamp * 1000 >= start_ms
        if trade:
            engine.open_bar(bar)
        point = averages[stamp]
        fast = decimal(point["fast_exact"]) if point["fast_exact"] is not None else None
        slow = decimal(point["slow_exact"]) if point["slow_exact"] is not None else None
        engine._close(bar, allow_trade=trade, averages=(fast, slow))
    result = engine.finish() if finalize else engine.result()
    result["mode"] = "HISTORICAL BACKTEST · SIMULATED"
    result["range"] = {"start_ms": start_ms, "end_ms": end_ms, "timezone": "UTC",
                       "first_bar_ms": engine.points[0]["time"] * 1000 if engine.points else None,
                       "last_bar_ms": engine.points[-1]["time"] * 1000 if engine.points else None}
    return result


def batch_indicators(bars, fast=5, slow=20):
    """Read-only chart calculation using independent direct-window SMA values.

    Equality preserves the last nonzero side; gaps/ineligible bars reset it. This
    exposes no orders/account and is suitable for replay or corrected chart data.
    """
    config = StrategyConfig(fast=fast, slow=slow)
    bars = list(bars)
    first = {}
    for bar in bars:
        if confirmed(bar):
            first.setdefault(bar_time(bar), bar)
    points, side, previous = [], 0, None
    for value in batch_sma(bars, config):
        stamp = value["time"]
        bar = first[stamp]
        if not value["eligible"] or (previous is not None and stamp - previous != config.interval_seconds):
            side = 0
        fast_value = decimal(value["fast_exact"]) if value["fast_exact"] is not None else None
        slow_value = decimal(value["slow_exact"]) if value["slow_exact"] is not None else None
        event, relation = None, "warming"
        if fast_value is not None and slow_value is not None:
            with localcontext() as context:
                context.prec = PRECISION
                difference = fast_value - slow_value
                current = 1 if difference > decimal(config.tolerance) else -1 if difference < -decimal(config.tolerance) else 0
            relation = "above" if current == 1 else "below" if current == -1 else "equal"
            if current:
                if side and current != side:
                    event = "UP" if current == 1 else "DOWN"
                side = current
        points.append({**value, "fast": float(fast_value) if fast_value is not None else None,
                       "slow": float(slow_value) if slow_value is not None else None,
                       "close": float(decimal(bar["close"])), "close_exact": exact(decimal(bar["close"])),
                       "event": event, "side": relation, "confirmed": True})
        previous = stamp
    return points
