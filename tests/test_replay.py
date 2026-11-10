"""Recorded synthetic fixtures verify availability-time replay, never live-feed proof."""
import asyncio
import copy
import json
import unittest
from contextlib import suppress
from datetime import datetime, timezone

from backend.replay import Replay
from backend.store import Store

BASE = int(datetime(2026, 11, 9, 14, 30, tzinfo=timezone.utc).timestamp() * 1000)


def quote(second, price):
    return {"id": "TEST", "time": str(BASE + second * 1000), "price": price}


def bar(**fields):
    return {"start_ms": BASE, "open": 100, "high": 105, "low": 98,
            "close": 103, "volume": 17, "finalized": True, **fields}


def capture():
    store = Store(":memory:", "TEST")
    def add(kind, value, receipt):
        return store.append(kind, value, BASE + receipt * 1000, source="fixture")
    add("quote", quote(10, 100), 11)
    add("quote", quote(40, 103), 41)
    add("bar", bar(finalized=False, volume=11), 42)
    add("feed", {"state": "unavailable", "detail": "induced fixture"}, 45)
    add("clock", {"at_ms": BASE + 60000}, 60)
    add("quote", quote(20, 98), 61)  # A late source event appears only now.
    add("bar", bar(), 62)
    add("bar", bar(high=110, close=109, volume=19), 63)
    add("feed", {"state": "receiving", "detail": None}, 64)
    return store


class ReplayTests(unittest.TestCase):
    def test_each_replayed_change_matches_immutable_persisted_candle_version(self):
        store = capture()
        try:
            events = store.events()
            expected = {}
            for row in store.db.execute("SELECT event_id,candle FROM candle_versions ORDER BY event_id,start_ms"):
                expected.setdefault(row["event_id"], []).append(json.loads(row["candle"]))
            replay = Replay(events, "TEST")
            first = replay.step()
            self.assertFalse(first["candles"][0]["elapsed"], "Replay must not close early using today's clock")
            self.assertIsNone(first["candles"][0]["volume"], "Later reconciliation cannot leak into the first replay tick")
            self.assertEqual(first["event"], events[0])
            self.assertEqual(first["candles"], expected[events[0]["id"]])
            for original in events[1:]:
                result = replay.step()
                self.assertEqual(result["event"], original, "Original source and receipt timestamps survive replay")
                self.assertEqual(result["candles"], expected.get(original["id"], []))
                self.assertEqual(result["replay"]["clock_ms"], max(e["received_ms"] for e in events[:replay.position]))
            self.assertEqual(replay.engine.history(), store.history())
            self.assertEqual(replay.state, "finished")
            self.assertIsNone(replay.step())
        finally:
            store.close()

    def test_replay_uses_receipt_id_order_with_ties_and_nonreversing_clock(self):
        store = Store(":memory:", "TEST")
        try:
            first, _ = store.append("quote", quote(10, 105), BASE + 11000, source="fixture")
            second, _ = store.append("quote", quote(5, 99), BASE + 11000, source="fixture")
            third, _ = store.append("quote", quote(8, 101), BASE + 10000, source="fixture")
            replay = Replay(store.events(), "TEST")
            results = [replay.step(), replay.step(), replay.step()]
            self.assertEqual([r["event"]["id"] for r in results], [first["id"], second["id"], third["id"]])
            self.assertEqual([r["replay"]["clock_ms"] for r in results], [BASE + 11000] * 3)
            self.assertEqual((replay.engine.history()[0]["open"], replay.engine.history()[0]["close"]), (99, 105))
        finally:
            store.close()

    def test_restart_repeats_same_revision_sequence_and_cannot_write_live_capture(self):
        store = capture()
        try:
            before_events = store.events()
            before_history = store.history()
            before_versions = store.db.execute("SELECT COUNT(*) FROM candle_versions").fetchone()[0]
            replay = Replay(before_events, "TEST")
            first_run = [replay.step() for _ in before_events]
            replay.reset()
            self.assertEqual(replay.position, 0)
            self.assertEqual(replay.engine.history(), [])
            self.assertIsNone(replay.meta()["clock_ms"])
            self.assertIsNone(replay.status_data["last_source_ms"])
            second_run = [replay.step() for _ in before_events]
            self.assertEqual(first_run, second_run)
            self.assertEqual(store.events(), before_events)
            self.assertEqual(store.history(), before_history)
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM candle_versions").fetchone()[0], before_versions)
            self.assertIsNot(replay.engine, store.engine)
        finally:
            store.close()

    def test_empty_recording_and_end_are_explicit(self):
        replay = Replay([], "TEST")
        self.assertEqual(replay.state, "empty")
        self.assertIsNone(replay.step())
        self.assertIsNone(replay.meta()["first_received_ms"])
        self.assertEqual(replay.meta()["total"], 0)
        replay.reset()
        self.assertEqual(replay.state, "empty")


class FakeSocket:
    def __init__(self):
        self.commands = asyncio.Queue()
        self.sent = []
        self.changed = asyncio.Event()

    async def send_json(self, value):
        self.sent.append(copy.deepcopy(value))
        self.changed.set()

    async def receive_json(self):
        return await self.commands.get()

    async def wait_for(self, predicate):
        async def wait():
            while not predicate():
                self.changed.clear()
                if predicate():
                    return
                await self.changed.wait()
        await asyncio.wait_for(wait(), timeout=1)


class ReplayControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_pause_resume_restart_and_finish_controls(self):
        store = Store(":memory:", "TEST")
        store.append("quote", quote(10, 100), BASE + 11000, source="fixture")
        store.append("quote", quote(40, 103), BASE + 41000, source="fixture")
        before = store.events()
        replay = Replay(before, "TEST")
        ws = FakeSocket()
        serving = asyncio.create_task(replay.serve(ws))
        try:
            await ws.wait_for(lambda: len(ws.sent) == 1)
            self.assertEqual(ws.sent[0]["mode"], "replay")
            await ws.commands.put({"action": "start", "speed": 100})
            await ws.wait_for(lambda: replay.position == 1)
            await ws.commands.put({"action": "pause"})
            await ws.wait_for(lambda: replay.state == "paused")
            position = replay.position
            await asyncio.sleep(0.04)
            self.assertEqual(replay.position, position)
            await ws.commands.put({"action": "resume", "speed": 100})
            await ws.wait_for(lambda: replay.state == "finished")
            self.assertEqual(replay.position, 2)
            await ws.commands.put({"action": "restart", "speed": 100})
            await ws.wait_for(lambda: sum(m["type"] == "snapshot" for m in ws.sent) == 2)
            await ws.wait_for(lambda: replay.state == "finished")
            self.assertEqual(sum(m["type"] == "update" for m in ws.sent), 4)
            self.assertEqual(store.events(), before)
        finally:
            serving.cancel()
            with suppress(asyncio.CancelledError):
                await serving
            store.close()
        self.assertTrue(serving.done(), "WebSocket receive task cleans up on disconnect")


if __name__ == "__main__":
    unittest.main()
