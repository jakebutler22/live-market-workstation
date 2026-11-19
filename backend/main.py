import asyncio
import os
from contextlib import asynccontextmanager
import anyio
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from .config import Config
from .service import Service
from .replay import Replay
from .trading import batch_indicators


class BacktestRequest(BaseModel):
    dataset_id: Literal["yahoo-4-1", "worked-eight"] = "yahoo-4-1"
    fast: int | None = Field(None, ge=1, le=199, strict=True)
    slow: int | None = Field(None, ge=2, le=200, strict=True)
    start_ms: int | None = Field(None, ge=0, strict=True)
    end_ms: int | None = Field(None, ge=0, strict=True)


class IndicatorRequest(BaseModel):
    candles: list[dict] = Field(default_factory=list, max_length=600)
    fast: int = Field(5, ge=1, le=199, strict=True)
    slow: int = Field(20, ge=2, le=200, strict=True)


def create_app(config=None, start_provider=None):
    config = config or Config()
    if start_provider is None:
        start_provider = os.getenv("CAPTURE_ENABLED", "1") != "0"

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = Service(config)
        if start_provider:
            await app.state.service.start()
        yield
        await app.state.service.close()

    app = FastAPI(title="Live Market Workstation · Assignments 4.1 / 4.2", lifespan=lifespan)

    @app.get("/api/strategy")
    async def strategy():
        return app.state.service.trading.overview()

    @app.post("/api/backtests")
    async def backtest(request: BacktestRequest):
        try:
            return app.state.service.trading.backtest(request.dataset_id, request.fast, request.slow,
                                                     request.start_ms, request.end_ms)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/backtests/{run_id}")
    async def backtest_result(run_id: str):
        result = app.state.service.trading.get_run(run_id)
        if not result:
            raise HTTPException(404, "Saved backtest not found")
        return result

    @app.post("/api/indicators")
    async def indicators(request: IndicatorRequest):
        try:
            points = batch_indicators(request.candles, request.fast, request.slow)
            return {"points":points,"signals":[],"fills":[],"config":{"fast":request.fast,"slow":request.slow}}
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/status")
    async def status():
        return app.state.service.status()

    @app.get("/api/health")
    async def health():
        return {"ok":True,"sqlite":"ready","upstream":app.state.service.status()["state"]}

    @app.get("/api/history")
    async def history(limit:int=Query(360,ge=1,le=600)):
        return {"symbol":config.symbol,"interval":60,"candles":app.state.service.store.history(limit)}

    @app.get("/api/observations")
    async def observations(limit:int=Query(20,ge=1,le=100)):
        return {"events":app.state.service.store.events(limit)}

    @app.get("/api/replay")
    async def replay_info():
        events = app.state.service.store.events()
        return Replay(events,config.symbol,app.state.service.status()).meta()

    @app.post("/api/feed/pause")
    async def pause():
        await app.state.service.provider.stop()
        await app.state.service.set_feed("paused","Controlled upstream interruption; local browser/backend connection stays active")
        return app.state.service.status()

    @app.post("/api/feed/resume")
    async def resume():
        await app.state.service.provider.stop()
        await app.state.service.provider.start()
        return app.state.service.status()

    def allowed(ws):
        return ws.headers.get("origin") in (None,"http://127.0.0.1:5173","http://localhost:5173","http://127.0.0.1:5174","http://localhost:5174","http://127.0.0.1:4173","http://localhost:4173")

    @app.websocket("/ws/live")
    async def live(ws:WebSocket):
        if not allowed(ws):
            await ws.close(code=1008)
            return
        await ws.accept()
        service = app.state.service
        queue = asyncio.Queue(maxsize=256)
        # Registration + snapshot occur before yielding, eliminating the HTTP/snapshot race.
        service.clients.add(queue)
        paper = service.trading.paper()
        snapshot = {"type":"snapshot","mode":"live","candles":service.store.history(),"status":service.status(),
                    "strategy":paper,"indicators":{k:paper[k] for k in ("points","signals","fills","config")}}
        reader = asyncio.create_task(ws.receive_text())
        next_message = None
        try:
            await ws.send_json(snapshot)
            while True:
                next_message = asyncio.create_task(queue.get())
                done,_ = await asyncio.wait({reader,next_message},return_when=asyncio.FIRST_COMPLETED)
                if reader in done:
                    # Surface disconnect first; the finally block collects the
                    # queue waiter under its cancellation shield.
                    reader.result()
                    if next_message not in done:
                        next_message.cancel()
                        with anyio.CancelScope(shield=True):
                            await asyncio.gather(next_message,return_exceptions=True)
                    reader = asyncio.create_task(ws.receive_text())
                if next_message in done:
                    message = next_message.result()
                    if message["type"] == "resync":
                        await ws.close(code=1013,reason="Slow client; reconnect for saved snapshot")
                        break
                    await ws.send_json(message)
        except (WebSocketDisconnect,RuntimeError):
            pass
        finally:
            service.clients.discard(queue)
            # A disconnect can cancel this route through AnyIO while it waits
            # for asyncio children. Shield cleanup so the receiver/queue task
            # is always collected and the subscriber is removed immediately.
            pending = [task for task in (reader,next_message) if task is not None]
            for task in pending:
                task.cancel()
            with anyio.CancelScope(shield=True):
                await asyncio.gather(*pending,return_exceptions=True)

    @app.websocket("/ws/replay")
    async def replay(ws:WebSocket):
        if not allowed(ws):
            await ws.close(code=1008)
            return
        await ws.accept()
        # Freeze this recording at connection; later live writes cannot leak into it.
        recording = app.state.service.store.events()
        try:
            await Replay(recording,config.symbol,app.state.service.status()).serve(ws)
        except (WebSocketDisconnect,RuntimeError,ValueError):
            pass

    return app


app = create_app()
