"""Synthetic API integration. Never opens Yahoo or uses the canonical capture DB."""
import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from backend.config import Config
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


@unittest.skipUnless(WEB_AVAILABLE, "approved FastAPI/httpx/yfinance dependencies not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Config(symbol="TEST", db_path=str(Path(self.temp.name)/"api.sqlite3"))
        self.app = create_app(self.config,start_provider=False)
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()
        self.source_ms = int(time.time()*1000)//60000*60000+1000

    def tearDown(self):
        self.client_context.__exit__(None,None,None)
        self.temp.cleanup()

    def add_quote(self, price=100):
        return self.client.portal.call(self.app.state.service.ingest,"quote",
            {"id":"TEST","time":str(self.source_ms),"price":price},self.source_ms+20)

    def test_live_socket_snapshot_then_durable_incremental_update_and_duplicate(self):
        with self.client.websocket_connect("/ws/live") as ws:
            first = ws.receive_json()
            self.assertEqual(first["type"],"snapshot")
            self.assertEqual(first["candles"],[])
            event,changed = self.add_quote()
            message = ws.receive_json()
            self.assertEqual(message["event"]["id"],event["id"])
            self.assertEqual(message["candles"],changed)
            saved = self.client.get("/api/observations?limit=1").json()["events"][0]
            self.assertEqual(saved["id"],message["event"]["id"])
            self.assertEqual(saved["payload"]["price"],100)
            self.assertEqual(self.client.get("/api/history").json()["candles"],changed)
            before = self.client.get("/api/status").json()["event_count"]
            duplicate,_ = self.add_quote()
            self.assertIsNone(duplicate)
            self.assertEqual(self.client.get("/api/status").json()["event_count"],before)
        self.assertIsNone(self.app.state.service.provider.runner)

    def test_bounded_retrieval_separate_feed_state_and_controlled_failure(self):
        for path in ("/api/history?limit=601","/api/observations?limit=0"):
            self.assertEqual(self.client.get(path).status_code,422)
        self.add_quote()
        previous = self.client.get("/api/history").json()
        paused = self.client.post("/api/feed/pause")
        self.assertEqual(paused.status_code,200)
        self.assertEqual(paused.json()["state"],"paused")
        self.assertEqual(self.client.get("/api/health").json()["upstream"],"paused")
        self.assertEqual(self.client.get("/api/history").json()["candles"][0]["close"],previous["candles"][0]["close"])
        source_time = paused.json()["last_source_ms"]
        with patch.object(self.app.state.service.provider,"start",new_callable=AsyncMock) as start:
            self.assertEqual(self.client.post("/api/feed/resume").status_code,200)
            start.assert_awaited_once()
        self.assertEqual(self.client.get("/api/status").json()["last_source_ms"],source_time)

    def test_replay_socket_reads_frozen_recording_while_live_state_is_unchanged(self):
        self.add_quote(100)
        before = self.client.get("/api/status").json()["event_count"]
        with self.client.websocket_connect("/ws/replay") as ws:
            initial = ws.receive_json()
            self.assertEqual(initial["mode"],"replay")
            self.assertEqual(initial["candles"],[])
            self.source_ms += 1000
            self.add_quote(101)
            ws.send_json({"action":"start","speed":100})
            self.assertEqual(ws.receive_json()["replay"]["state"],"playing")
            result = ws.receive_json()
            self.assertEqual(result["replay"]["state"],"finished")
            self.assertEqual(result["replay"]["total"],before)
            self.assertEqual(result["candles"][0]["close"],100)
        self.assertEqual(self.client.get("/api/status").json()["event_count"],before+1)
        self.assertEqual(self.client.get("/api/history").json()["candles"][0]["close"],101)

    def test_websocket_rejects_untrusted_browser_origin(self):
        from starlette.websockets import WebSocketDisconnect
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect("/ws/live",headers={"origin":"https://unrelated.example"}):
                pass

    def test_repeated_socket_disconnect_cleans_subscribers_and_queue_waiters(self):
        async def queue_waiters():
            await asyncio.sleep(0)
            return sum(task.get_coro().__qualname__ == "Queue.get"
                       for task in asyncio.all_tasks() if not task.done())

        baseline = self.client.portal.call(queue_waiters)
        for _ in range(8):
            with self.client.websocket_connect("/ws/live") as ws:
                self.assertEqual(ws.receive_json()["type"],"snapshot")
                self.assertEqual(len(self.app.state.service.clients),1)
            self.assertEqual(len(self.app.state.service.clients),0)
            with self.client.websocket_connect("/ws/replay") as ws:
                self.assertEqual(ws.receive_json()["mode"],"replay")
            self.assertEqual(self.client.portal.call(queue_waiters),baseline)
