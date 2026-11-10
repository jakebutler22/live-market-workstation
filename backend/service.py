import asyncio
import time
from .store import Store
from .provider import YahooProvider, now_ms


class Service:
    def __init__(self, config):
        self.config = config
        self.store = Store(config.db_path, config.symbol)
        self.state = "connecting"
        self.error = None
        self.volume_error = None
        self.clients = set()
        self.provider = YahooProvider(self)
        self.ticker = None
        self.lock = asyncio.Lock()
        self.last_duration_ms = None

    def status(self):
        latest_row = self.store.db.execute("SELECT * FROM events WHERE symbol=? AND kind='quote' ORDER BY id DESC LIMIT 1", (self.config.symbol,)).fetchone()
        latest = self.store.decode(latest_row) if latest_row else None
        quote_count, latest_source = self.store.db.execute("SELECT COUNT(*),MAX(source_ms) FROM events WHERE symbol=? AND kind='quote'", (self.config.symbol,)).fetchone()
        delay = 1200 if self.config.symbol == "BHP.AX" else 0
        state = self.state
        if state == "receiving" and latest_source and now_ms()-latest_source > (self.config.stale_seconds+delay)*1000:
            state = "stale"
        return {"symbol": self.config.symbol, "interval":60, "source":"Yahoo Finance",
                "state":state, "upstream_state":self.state,
                "expected_delay_seconds":delay, "data_label":"ASX · 20 min delayed · AUD" if delay else "Yahoo source · verify exchange delay",
                "price_unit":"AUD" if delay else "quote units", "volume_unit":"shares" if self.config.symbol in ("BHP.AX","AAPL") else "vendor units",
                "last_source_ms": latest_source, "last_received_ms":latest["received_ms"] if latest else None,
                "last_event_id":latest["id"] if latest else None,
                "event_count":self.store.count(), "quote_count":quote_count,
                "duplicate_count":self.store.duplicates, "error":self.error,
                "volume_status": self.volume_error or "Yahoo 1m reconciliation · up to 30s polling lag; vendor delay additional",
                "processing_ms":self.last_duration_ms,
                "database":"data/market.sqlite3" if self.config.db_path.endswith("data/market.sqlite3") else "configured SQLite database"}

    async def start(self):
        self.ticker = asyncio.create_task(self.clock_loop())
        await self.provider.start()

    async def close(self):
        await self.provider.stop()
        if self.ticker:
            self.ticker.cancel()
            await asyncio.gather(self.ticker,return_exceptions=True)
        self.store.close()

    async def ingest(self, kind, payload, received=None):
        started = time.perf_counter()
        async with self.lock:
            event, candles = self.store.append(kind,payload,received or now_ms())
            if event:
                self.last_duration_ms = round((time.perf_counter()-started)*1000,3)
                await self.broadcast({"type":"update","event":event,"candles":candles,"status":self.status()})
            return event, candles

    async def set_feed(self,state,error):
        self.state,self.error = state,error
        await self.ingest("feed", {"state":state,"detail":error})
        await self.broadcast_status()

    async def broadcast_status(self):
        await self.broadcast({"type":"status","status":self.status()})

    async def broadcast(self, message):
        # Slow browsers cannot block capture. Bounded queues require a fresh snapshot
        # when overflow closes that browser; records remain durable in SQLite.
        for queue in tuple(self.clients):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self.clients.discard(queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({"type":"resync"})

    async def clock_loop(self):
        while True:
            await asyncio.sleep(1)
            clock = now_ms()
            if any(not c["elapsed"] and c["end_ms"]<=clock for c in self.store.engine.candles.values()):
                await self.ingest("clock", {"at_ms":clock},clock)
            await self.broadcast_status()
