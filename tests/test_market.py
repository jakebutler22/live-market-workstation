"""Synthetic TEST fixtures: repeatable rules, never evidence of a live Yahoo session."""
import tempfile
import unittest
import copy
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.market import INTERVAL_MS, normalize_bar, normalize_quote
from backend.store import Store

BASE = int(datetime(2026, 11, 9, 14, 30, tzinfo=timezone.utc).timestamp() * 1000)


def raw_quote(seconds, price, **fields):
    return {"id": "TEST", "time": str(BASE + seconds * 1000), "price": price, **fields}


def raw_bar(seconds=0, **fields):
    return {"start_ms": BASE + seconds * 1000, "open": 100, "high": 105,
            "low": 98, "close": 103, "volume": 11, "finalized": True, **fields}


class ValidationTests(unittest.TestCase):
    def test_quotes_validate_identity_units_and_finite_price(self):
        good = normalize_quote(raw_quote(10, 101), "TEST", BASE + 12000)
        self.assertEqual(good["source_ms"], BASE + 10000)
        self.assertEqual(good["raw"]["time"], str(BASE + 10000))
        for fields in ({"id": "WRONG"}, {"time": str(BASE // 1000)},
                       {"time": str(BASE + 400000)}, {"price": float("nan")},
                       {"price": 0}, {"price": True}):
            with self.subTest(fields=fields), self.assertRaises((ValueError, TypeError)):
                normalize_quote({**raw_quote(10, 101), **fields}, "TEST", BASE + 12000)
        with self.assertRaises((ValueError, TypeError)):
            normalize_quote({"id": "TEST", "time": str(BASE)}, "TEST", BASE)

    def test_bar_preserves_unknown_zero_finalization_and_rejects_bad_ohlcv(self):
        unknown = normalize_bar(raw_bar(volume=None, finalized=False))
        self.assertIsNone(unknown["volume"])
        self.assertFalse(unknown["finalized"])
        self.assertEqual(normalize_bar(raw_bar(volume=0))["volume"], 0)
        for fields in ({"start_ms": BASE + 1}, {"high": 99}, {"low": 101},
                       {"volume": -1}, {"volume": float("inf")}, {"open": 0}):
            with self.subTest(fields=fields), self.assertRaises((ValueError, TypeError)):
                normalize_bar(raw_bar(**fields))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "fixture.sqlite3"
        self.store = Store(self.path, "TEST")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def append(self, kind, payload, received_seconds, **kwargs):
        return self.store.append(kind, payload, BASE + received_seconds * 1000,
                                 source="fixture", **kwargs)

    def quote(self, seconds, price, received_seconds=None, **kwargs):
        return self.append("quote", raw_quote(seconds, price),
                           received_seconds if received_seconds is not None else seconds, **kwargs)

    def version_count(self):
        return self.store.db.execute("SELECT COUNT(*) FROM candle_versions").fetchone()[0]

    def test_hand_calculated_ohlcv_late_order_and_exclusive_interval_boundary(self):
        # Chronological prices: 100, 105, 98, 103 => O100 H105 L98 C103.
        self.quote(10, 100, 12)
        self.quote(50, 103, 51)
        self.quote(30, 98, 52)
        self.quote(20, 105, 53)
        self.quote(60, 107, 60)  # Exactly 09:31 belongs to [09:31, 09:32).
        first, second = self.store.history()
        self.assertEqual([first[k] for k in ("open", "high", "low", "close")], [100, 105, 98, 103])
        self.assertEqual(first["quote_count"], 4)
        self.assertEqual(second["time"] * 1000, BASE + INTERVAL_MS)
        self.assertEqual(second["open"], 107)
        self.assertIsNone(first["volume"])
        self.append("bar", raw_bar(), 62)
        first = self.store.history()[0]
        self.assertEqual(first["volume"], 11)
        self.assertTrue(first["elapsed"])
        self.assertFalse(first["partial"])
        self.assertEqual(first["price_source"], "Yahoo 1m aggregate")
        self.assertIsNone(self.store.history()[1]["volume"])

    def test_exact_duplicate_keeps_log_versions_and_volume_unchanged(self):
        sample = raw_quote(10, 100, day_volume="99999999", last_size="250")
        event, _ = self.append("quote", sample, 11)
        before = self.store.history()
        versions = self.version_count()
        duplicate, changes = self.append("quote", sample, 20)
        self.assertIsNone(duplicate)
        self.assertEqual(changes, [])
        self.assertEqual(self.store.count(), 1)
        self.assertEqual(self.version_count(), versions)
        self.assertEqual(self.store.history(), before)
        self.assertEqual(self.store.events()[0]["received_ms"], BASE + 11000)
        self.assertEqual(self.store.events()[0]["id"], event["id"])
        self.assertIsNone(before[0]["volume"], "Cumulative/last-size fields are never summed into interval volume")

    def test_same_time_different_observations_have_stable_hash_tie_order(self):
        a, _ = self.quote(20, 105, 21)
        b, _ = self.quote(20, 99, 22)
        expected = sorted((a, b), key=lambda e: e["fingerprint"])
        first = self.store.history()[0]
        self.assertEqual(first["quote_count"], 2)
        self.assertEqual(first["open"], expected[0]["payload"]["price"])
        self.assertEqual(first["close"], expected[1]["payload"]["price"])
        other = Store(":memory:", "TEST")
        try:
            other.append("quote", raw_quote(20, 99), BASE + 21000, source="fixture")
            other.append("quote", raw_quote(20, 105), BASE + 22000, source="fixture")
            self.assertEqual([first[k] for k in ("open", "high", "low", "close")],
                             [other.history()[0][k] for k in ("open", "high", "low", "close")])
        finally:
            other.close()

    def test_elapsed_sample_stays_partial_and_late_quote_revises_closed_interval(self):
        self.quote(20, 100, 22)
        self.append("clock", {"at_ms": BASE + 60000}, 60)
        closed = self.store.history()[0]
        self.assertTrue(closed["elapsed"])
        self.assertTrue(closed["partial"])
        self.assertTrue(closed["capture_midinterval"])
        self.quote(10, 95, 70)
        revised = self.store.history()[0]
        self.assertEqual((revised["open"], revised["low"], revised["close"]), (95, 95, 100))
        self.assertGreater(revised["revision"], closed["revision"])
        self.assertTrue(revised["elapsed"])
        self.assertEqual(len(self.store.history()), 1, "No unobserved minute is manufactured")

    def test_provisional_bar_does_not_override_sampled_price_until_finalized(self):
        self.quote(10, 101, 11)
        self.append("bar", raw_bar(finalized=False), 20)
        self.append("clock", {"at_ms": BASE + 60000}, 60)
        provisional = self.store.history()[0]
        self.assertEqual(provisional["open"], 101)
        self.assertTrue(provisional["elapsed"])
        self.assertTrue(provisional["partial"])
        self.append("bar", raw_bar(finalized=True), 65)
        final = self.store.history()[0]
        self.assertEqual(final["open"], 100)
        self.assertFalse(final["partial"])
        self.assertEqual(final["volume"], 11)

    def test_interval_bar_revision_preserves_original_and_replaces_volume(self):
        original, _ = self.append("bar", raw_bar(), 61)
        before = self.version_count()
        duplicate, _ = self.append("bar", raw_bar(), 62)
        self.assertIsNone(duplicate)
        self.assertEqual(self.version_count(), before)
        correction, _ = self.append("bar", raw_bar(high=108, close=106, volume=13), 63)
        self.assertEqual(correction["revision"], 2)
        self.assertEqual(correction["identity"], original["identity"])
        self.assertEqual(correction["supersedes_id"], original["id"])
        self.assertEqual(self.store.events()[0]["payload"]["volume"], 11)
        self.assertEqual(self.store.history()[0]["volume"], 13, "Reconciled interval volumes replace; they do not add")
        self.assertEqual(self.store.history()[0]["high"], 108)
        self.assertEqual(self.version_count(), before + 1)

    def test_explicit_fixture_quote_correction_chain_can_revert_value(self):
        original, _ = self.quote(10, 100, 11)
        corrected, _ = self.quote(10, 110, 12, supersedes_id=original["id"])
        reverted, _ = self.quote(10, 100, 13, supersedes_id=corrected["id"])
        self.assertIsNotNone(reverted, "A real correction reverting a previous value is an accepted new revision")
        self.assertEqual([e["revision"] for e in self.store.events()], [1, 2, 3])
        self.assertEqual(reverted["supersedes_id"], corrected["id"])
        self.assertEqual(len({e["identity"] for e in self.store.events()}), 1)
        self.assertEqual(self.store.history()[0]["quote_count"], 1)
        self.assertEqual(self.store.history()[0]["close"], 100)
        with self.assertRaises(ValueError):
            self.quote(10, 120, 14, supersedes_id=original["id"])

    def test_exact_corrected_quote_duplicate_is_not_reinserted_as_new_observation(self):
        original, _ = self.quote(10, 100, 11)
        self.quote(10, 110, 12, supersedes_id=original["id"])
        count, versions = self.store.count(), self.version_count()
        duplicate, changes = self.quote(10, 110, 13)
        self.assertIsNone(duplicate)
        self.assertEqual(changes, [])
        self.assertEqual((self.store.count(), self.version_count()), (count, versions))
        self.assertEqual(self.store.history()[0]["quote_count"], 1)

    def test_repeated_unavailability_is_retained_and_coverage_stays_partial(self):
        self.quote(10, 100, 11)
        self.append("feed", {"state": "unavailable", "detail": "induced fixture"}, 20)
        self.append("feed", {"state": "receiving", "detail": None}, 25)
        self.quote(70, 102, 71)
        second, _ = self.append("feed", {"state": "unavailable", "detail": "induced fixture"}, 75)
        self.assertIsNotNone(second)
        self.assertTrue(self.store.history()[1]["gap"])
        self.assertTrue(self.store.history()[1]["partial"])
        self.assertEqual(sum(e["kind"] == "feed" for e in self.store.events()), 3)

    def test_database_reopen_reconstructs_identical_state_without_new_versions(self):
        self.quote(10, 100, 11)
        self.quote(30, 105, 31)
        self.append("clock", {"at_ms": BASE + 60000}, 60)
        self.append("bar", raw_bar(), 62)
        self.append("bar", raw_bar(high=108, close=106, volume=13), 65)
        expected = self.store.history()
        events = self.store.events()
        versions = [tuple(r) for r in self.store.db.execute("SELECT * FROM candle_versions ORDER BY event_id,start_ms")]
        self.store.close()
        self.store = Store(self.path, "TEST")
        self.assertEqual(self.store.history(), expected)
        self.assertEqual(self.store.engine.history(), expected)
        self.assertEqual(self.store.events(), events)
        self.assertEqual([tuple(r) for r in self.store.db.execute("SELECT * FROM candle_versions ORDER BY event_id,start_ms")], versions)

    def test_candle_write_failure_rolls_back_sql_and_restores_in_memory_reducer(self):
        self.quote(10, 100, 11)
        before_events = copy.deepcopy(self.store.engine.events)
        before_history = self.store.history()
        before_clock = self.store.engine.clock_ms
        before_versions = self.version_count()
        self.store.db.execute("""CREATE TEMP TRIGGER refuse_candle_version
            BEFORE INSERT ON candle_versions BEGIN
            SELECT RAISE(ABORT, 'induced candle write failure'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "induced candle write failure"):
            self.quote(20, 110, 22)
        self.assertEqual(self.store.count(), 1, "Unsaved observations cannot remain in the SQL log")
        self.assertEqual(self.version_count(), before_versions)
        self.assertEqual(self.store.engine.events, before_events, "Rollback also removes unsaved reducer events")
        self.assertEqual(self.store.engine.clock_ms, before_clock)
        self.assertEqual(self.store.history(), before_history)
        self.assertEqual(self.store.engine.history(), before_history)
        self.store.db.execute("DROP TRIGGER refuse_candle_version")
        saved, changes = self.quote(20, 110, 23)
        self.assertIsNotNone(saved)
        self.assertEqual(self.store.count(), 2)
        self.assertEqual(changes[0]["high"], 110)
        self.assertEqual(changes[0]["quote_count"], 2)
        self.assertEqual(self.store.engine.history(), self.store.history())

    def test_delayed_recovery_flags_source_interval_without_poisoning_future_receipt_interval(self):
        # Every quote arrives 20 minutes after source time, as on the submitted ASX feed.
        self.quote(10, 100, 1211)
        self.append("feed", {"state": "unavailable", "detail": "induced delayed fixture"}, 1220)
        self.quote(70, 101, 1271)
        self.append("feed", {"state": "receiving", "detail": None}, 1272)
        self.quote(130, 102, 1331)
        candles = self.store.history()
        self.assertTrue(candles[0]["gap"])
        self.assertTrue(candles[1]["gap"], "The recovery quote's source interval contains the capture gap")
        self.assertFalse(candles[2]["gap"], "A subsequent clean source interval has no outage")
        # The receipt minute at recovery is 21 minutes after BASE. It must not
        # receive a phantom gap when that source-time interval arrives later.
        self.quote(1265, 103, 2466)
        future_source_interval = self.store.history()[-1]
        self.assertEqual(future_source_interval["time"] * 1000, BASE + 1260000)
        self.assertFalse(future_source_interval["gap"])
        self.assertEqual(self.store.engine.gap_buckets, {BASE, BASE + INTERVAL_MS})

    def test_explicit_quote_correction_rejects_source_timestamp_changes_even_within_one_bucket(self):
        original, _ = self.quote(10, 100, 11)
        before = self.store.history()
        for changed_time in (11, 70):
            with self.subTest(changed_time=changed_time), self.assertRaisesRegex(ValueError, "retain source timestamp"):
                self.quote(changed_time, 110, 80, supersedes_id=original["id"])
        self.assertEqual(self.store.count(), 1)
        self.assertEqual(self.store.history(), before)
        self.assertEqual(self.store.engine.history(), before)
        correction, _ = self.quote(10, 110, 81, supersedes_id=original["id"])
        self.assertEqual(correction["source_ms"], original["source_ms"])
        self.assertEqual(self.store.history()[0]["quote_count"], 1)
        self.assertEqual(self.store.history()[0]["close"], 110)

    def test_two_separate_python_processes_retain_exact_events_revisions_and_candles(self):
        process_database = str(Path(self.directory.name) / "separate-process.sqlite3")
        script = """
import json, os, sys
from backend.store import Store
store = Store(sys.argv[1], 'TEST')
base = int(sys.argv[3])
if sys.argv[2] == 'write':
    def append(kind, payload, second):
        return store.append(kind, payload, base + second * 1000, source='fixture')
    append('quote', {'id':'TEST','time':str(base+10000),'price':100}, 11)
    append('quote', {'id':'TEST','time':str(base+30000),'price':105}, 31)
    append('clock', {'at_ms':base+60000}, 60)
    first = {'start_ms':base,'open':100,'high':105,'low':98,'close':103,'volume':11,'finalized':True}
    append('bar', first, 62)
    append('bar', {**first,'high':108,'close':106,'volume':13}, 65)
snapshot = {'pid':os.getpid(), 'events':store.events(), 'history':store.history(),
            'engine_history':store.engine.history(),
            'versions':[dict(row) for row in store.db.execute('SELECT * FROM candle_versions ORDER BY event_id,start_ms')]}
store.close()
print(json.dumps(snapshot))
"""
        root = Path(__file__).resolve().parents[1]
        snapshots = []
        for mode in ("write", "read"):
            result = subprocess.run([sys.executable, "-c", script, process_database, mode, str(BASE)],
                                    cwd=root, check=True, capture_output=True, text=True, timeout=10)
            snapshots.append(json.loads(result.stdout))
        writer, reader = snapshots
        self.assertNotEqual(writer["pid"], reader["pid"])
        self.assertNotIn(os.getpid(), (writer["pid"], reader["pid"]))
        self.assertEqual(len(writer["events"]), 5)
        self.assertEqual(writer["history"][0]["volume"], 13)
        for key in ("events", "history", "engine_history", "versions"):
            self.assertEqual(writer[key], reader[key], f"Separate-process restart must preserve {key}")
        self.assertEqual(reader["history"], reader["engine_history"])


if __name__ == "__main__":
    unittest.main()
