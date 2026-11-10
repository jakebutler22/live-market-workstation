"""Transport edge fixtures; these are not real yfinance integration evidence."""
import asyncio
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend.provider import FiniteSocket, YahooProvider


class SocketFixture:
    def __init__(self):
        self.messages = iter(['actual socket payload placeholder'])
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration

    async def close(self):
        self.closed = True


class FiniteTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_clean_iterator_close_raises_once_instead_of_spinning_yfinance_loop(self):
        underlying = SocketFixture()
        socket = FiniteSocket(underlying)
        self.assertEqual(await socket.__anext__(),'actual socket payload placeholder')
        with self.assertRaisesRegex(ConnectionError,'upstream closed'):
            await asyncio.wait_for(socket.__anext__(),.1)
        await socket.close()
        self.assertTrue(underlying.closed)

    async def test_cancellation_propagates_through_guard(self):
        class Quiet(SocketFixture):
            async def __anext__(self):
                await asyncio.Event().wait()
        task = asyncio.create_task(FiniteSocket(Quiet()).__anext__())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task


class HistoricalTransportTests(unittest.TestCase):
    def test_raw_chart_preserves_null_zero_and_provisional_source_boundary(self):
        # Fixture: second-aligned Yahoo history timestamps; final non-aligned
        # separate live point must not become a fabricated one-minute candle.
        payload = {"chart":{"result":[{"meta":{"regularMarketTime":1794269681},
            "timestamp":[1794269580,1794269640,1794269681],
            "indicators":{"quote":[{"open":[10,11,12],"high":[11,12,12],
                "low":[9,10,12],"close":[10.5,11.5,12],"volume":[None,0,999]}]}}]}}
        provider = YahooProvider(SimpleNamespace(config=SimpleNamespace(symbol='TEST')))
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())):
            bars = provider.fetch_bars()
        self.assertEqual(len(bars),2)
        self.assertIsNone(bars[0]['volume'])
        self.assertEqual(bars[1]['volume'],0)
        self.assertTrue(bars[0]['finalized'])
        self.assertFalse(bars[1]['finalized'])
        self.assertEqual(bars[0]['start_ms'],1794269580000)
