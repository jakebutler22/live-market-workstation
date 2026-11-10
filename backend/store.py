"""SQLite immutable accepted-event log plus versioned materialized candles."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .market import CandleEngine, normalize_bar, normalize_quote

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source TEXT NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL,
 source_ms INTEGER, received_ms INTEGER NOT NULL, identity TEXT NOT NULL,
 fingerprint TEXT NOT NULL, revision INTEGER NOT NULL,
 supersedes_id INTEGER REFERENCES events(id), payload TEXT NOT NULL,
 UNIQUE(source,symbol,kind,identity,revision)
);
CREATE INDEX IF NOT EXISTS events_symbol_time ON events(symbol,source_ms,id);
CREATE INDEX IF NOT EXISTS events_kind_time ON events(symbol,kind,source_ms,id);
CREATE INDEX IF NOT EXISTS events_fingerprint ON events(source,symbol,kind,fingerprint);
CREATE INDEX IF NOT EXISTS events_available ON events(received_ms,id);
CREATE TABLE IF NOT EXISTS candle_versions (
 symbol TEXT NOT NULL, start_ms INTEGER NOT NULL, revision INTEGER NOT NULL,
 event_id INTEGER NOT NULL REFERENCES events(id), candle TEXT NOT NULL,
 PRIMARY KEY(symbol,start_ms,revision)
);
CREATE VIEW IF NOT EXISTS latest_candles AS
 SELECT c.* FROM candle_versions c WHERE c.revision=(
 SELECT MAX(v.revision) FROM candle_versions v WHERE v.symbol=c.symbol AND v.start_ms=c.start_ms);
"""


class Store:
    def __init__(self, path, symbol):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.symbol = symbol
        self.engine = CandleEngine()
        self.duplicates = 0
        for event in self.events():
            self.engine.apply(event)

    @staticmethod
    def decode(row):
        data = dict(row)
        data["payload"] = json.loads(data["payload"])
        return data

    def events(self, limit=None):
        if limit:
            rows = self.db.execute("SELECT * FROM events WHERE symbol=? ORDER BY id DESC LIMIT ?", (self.symbol,limit)).fetchall()
            return [self.decode(r) for r in reversed(rows)]
        rows = self.db.execute("SELECT * FROM events WHERE symbol=? ORDER BY id", (self.symbol,)).fetchall()
        return [self.decode(r) for r in rows]

    def append(self, kind, payload, received_ms, *, source="Yahoo Finance", supersedes_id=None):
        if kind == "quote":
            payload = normalize_quote(payload, self.symbol, received_ms)
            source_ms = payload["source_ms"]
        elif kind == "bar":
            payload = normalize_bar(payload)
            source_ms = payload["start_ms"]
        else:
            source_ms = None
        packed = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = hashlib.sha256(packed.encode()).hexdigest()
        # Without a genuine Yahoo trade ID, only byte-equivalent useful messages deduplicate.
        identity = str(payload["start_ms"]) if kind == "bar" else fingerprint
        prior = None
        revision = 1
        if supersedes_id:
            old = self.db.execute("SELECT * FROM events WHERE id=?", (supersedes_id,)).fetchone()
            if not old or old["symbol"] != self.symbol or old["kind"] != kind or old["source"] != source:
                raise ValueError("correction must reference an existing observation of same source/symbol/kind")
            if kind == "quote" and old["source_ms"] != source_ms:
                raise ValueError("quote correction must retain source timestamp")
            repeated = self.db.execute("SELECT * FROM events WHERE supersedes_id=?", (supersedes_id,)).fetchone()
            if old["fingerprint"] == fingerprint or (repeated and repeated["fingerprint"] == fingerprint):
                self.duplicates += 1
                return None, []
            if repeated:
                raise ValueError("correction must supersede the active revision")
            identity, revision = old["identity"], old["revision"] + 1
        elif kind == "quote":
            prior = self.db.execute("SELECT id FROM events WHERE source=? AND symbol=? AND kind=? AND fingerprint=? LIMIT 1",
                                   (source,self.symbol,kind,fingerprint)).fetchone()
            if prior:
                self.duplicates += 1
                return None, []
        elif kind == "bar":
            prior = self.db.execute("SELECT * FROM events WHERE source=? AND symbol=? AND kind=? AND identity=? ORDER BY revision DESC LIMIT 1",
                                   (source,self.symbol,kind,identity)).fetchone()
            if prior and prior["fingerprint"] == fingerprint:
                self.duplicates += 1
                return None, []
            if prior:
                revision, supersedes_id = prior["revision"]+1, prior["id"]
        else:
            # State transitions are occurrences, not price observations. Repeating
            # a disconnect/recovery on a later attempt must remain replayable.
            identity = f"{received_ms}:{self.count()+1}:{fingerprint}"
        # Source and receipt times remain distinct. ID is deterministic availability order,
        # even if the OS clock adjusts backwards; reducer clock never reverses.
        try:
            with self.db:
                cursor = self.db.execute("INSERT INTO events(source,symbol,kind,source_ms,received_ms,identity,fingerprint,revision,supersedes_id,payload) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (source,self.symbol,kind,source_ms,received_ms,identity,fingerprint,revision,supersedes_id,packed))
                event = self.decode(self.db.execute("SELECT * FROM events WHERE id=?", (cursor.lastrowid,)).fetchone())
                changes = self.engine.apply(event)
                for candle in changes:
                    self.db.execute("INSERT INTO candle_versions VALUES(?,?,?,?,?)",
                        (self.symbol,candle["time"]*1000,candle["revision"],event["id"],json.dumps(candle)))
        except Exception:
            # SQLite rolled back. Restore the reducer from durable events so a
            # subsequent successful publish can never include unsaved state.
            self.engine = CandleEngine()
            for saved_event in self.events():
                self.engine.apply(saved_event)
            raise
        return event, changes

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM events WHERE symbol=?", (self.symbol,)).fetchone()[0]

    def history(self, limit=600):
        rows = self.db.execute("SELECT candle FROM latest_candles WHERE symbol=? ORDER BY start_ms DESC LIMIT ?", (self.symbol,limit)).fetchall()
        return [json.loads(r[0]) for r in reversed(rows)]

    def close(self):
        self.db.close()
