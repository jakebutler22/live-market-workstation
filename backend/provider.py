"""One application-owned Yahoo session. Browsers never create upstream tasks."""
import asyncio
import time
import json
import urllib.request
import urllib.parse
import os
import ssl
from pathlib import Path


def ensure_tls_roots():
    """Use the OS bundle if a framework Python has no configured trust roots.

    Certificate verification stays enabled. Never mutate the machine trust store.
    An explicitly configured SSL_CERT_FILE always takes precedence.
    """
    if not os.environ.get("SSL_CERT_FILE") and not ssl.get_default_verify_paths().cafile:
        bundle = Path("/etc/ssl/cert.pem")
        if bundle.is_file():
            os.environ["SSL_CERT_FILE"] = str(bundle)


class FiniteSocket:
    """Pinned yfinance 1.8 compatibility: normal iterator end must fail once.

    Its listen() otherwise loops over a closed iterator without yielding. All
    socket operations still use yfinance's original connection and decoder.
    """
    def __init__(self, socket):
        self.socket = socket
        self.iterator = socket.__aiter__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.iterator.__anext__()
        except StopAsyncIteration as exc:
            raise ConnectionError("Yahoo upstream closed its message iterator") from exc

    def __getattr__(self, name):
        return getattr(self.socket, name)


def now_ms():
    return time.time_ns() // 1_000_000


class YahooProvider:
    def __init__(self, service):
        self.service = service
        self.runner = None
        self.history_runner = None
        self.paused = False
        self.last_message = 0
        self.client = None

    async def start(self):
        self.paused = False
        if not self.runner or self.runner.done():
            self.runner = asyncio.create_task(self.run())
        if not self.history_runner or self.history_runner.done():
            self.history_runner = asyncio.create_task(self.reconcile())

    async def stop(self):
        self.paused = True
        for task in (self.runner, self.history_runner):
            if task:
                task.cancel()
        await asyncio.gather(*(t for t in (self.runner,self.history_runner) if t), return_exceptions=True)
        if self.client:
            try:
                await asyncio.wait_for(self.client.close(), 3)
            except Exception:
                pass
        self.client = None

    async def on_message(self, message):
        received = now_ms()
        if message.get("id") != self.service.config.symbol:
            return
        try:
            await self.service.ingest("quote", message, received)
        except (ValueError, TypeError, OverflowError) as exc:
            self.service.error = f"Rejected Yahoo message: {exc}"
            await self.service.broadcast_status()
            return
        self.last_message = received
        if self.service.state != "receiving":
            await self.service.set_feed("receiving", None)

    async def run(self):
        import yfinance as yf
        ensure_tls_roots()
        yf.config.debug.hide_exceptions = False
        for attempt in range(1, self.service.config.max_attempts + 1):
            if self.paused:
                return
            await self.service.set_feed("connecting", f"Connection attempt {attempt}/5")
            listener = None
            self.client = yf.AsyncWebSocket(verbose=False)
            try:
                await asyncio.wait_for(self.client.subscribe([self.service.config.symbol]), 15)
                self.client._ws = FiniteSocket(self.client._ws)
                self.last_message = now_ms()
                listener = asyncio.create_task(self.client.listen(self.on_message))
                # yfinance has its own unbounded reconnect loop. This outer watchdog
                # cancels that listener and replaces the entire client on every attempt.
                while not self.paused:
                    await asyncio.sleep(1)
                    if listener.done():
                        listener.result()
                        raise ConnectionError("Yahoo listener ended")
                    if now_ms() - self.last_message > 45_000:
                        raise TimeoutError("No valid Yahoo observations for 45 seconds")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self.service.set_feed("unavailable", f"{type(exc).__name__}: {str(exc)[:180]}")
            finally:
                if listener:
                    listener.cancel()
                    try:
                        await asyncio.wait_for(asyncio.gather(listener, return_exceptions=True),3)
                    except TimeoutError:
                        pass
                try:
                    await asyncio.wait_for(self.client.close(), 3)
                except Exception:
                    pass
                heartbeat = getattr(self.client,"_heartbeat_task",None)
                if heartbeat:
                    heartbeat.cancel()
                    await asyncio.gather(heartbeat,return_exceptions=True)
                self.client = None
            if attempt < self.service.config.max_attempts:
                await asyncio.sleep(min(2 ** attempt, 16))
        await self.service.set_feed("unavailable", "Five connection attempts exhausted. Use Resume source to retry.")

    def fetch_bars(self):
        ensure_tls_roots()
        # Raw Yahoo chart JSON retains null volume. yfinance history fills missing
        # volume with zero; preserving unknown is necessary for this assignment.
        symbol = urllib.parse.quote(self.service.config.symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d&includePrePost=false"
        request = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.load(response)
        result = body["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]
        rows = []
        last_bucket = max((int(t)//60*60 for t in timestamps), default=0)
        for index, stamp in enumerate(timestamps):
            # Yahoo sometimes appends a separate, non-aligned last-trade entry.
            if int(stamp) % 60:
                continue
            values = {key: quote.get(key, [None]*len(timestamps))[index]
                      for key in ("open","high","low","close","volume")}
            if any(values[key] is None for key in ("open","high","low","close")):
                continue
            # The latest returned minute is provisional even if wall time passed
            # (delayed exchanges). It becomes finalized only after a later bucket.
            rows.append({"start_ms": int(stamp)*1000, **values,
                         "finalized": int(stamp) < last_bucket,
                         "vendor_source_ms": result.get("meta",{}).get("regularMarketTime",0)*1000})
        return rows[-360:]

    async def reconcile(self):
        first = True
        while not self.paused:
            try:
                rows = await asyncio.wait_for(asyncio.to_thread(self.fetch_bars), 20)
                received = now_ms()
                # Initial seed is bounded; later requests reconcile the last five
                # vendor bars, preserving revisions in availability order.
                for bar in (rows if first else rows[-5:]):
                    await self.service.ingest("bar", bar, received)
                first = False
                self.service.volume_error = None if rows else "Yahoo returned no minute aggregates"
                await self.service.broadcast_status()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.service.volume_error = f"Yahoo minute reconciliation unavailable: {type(exc).__name__}: {str(exc)[:100]}"
                await self.service.broadcast_status()
            await asyncio.sleep(30)
