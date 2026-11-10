"""Per-browser replay of immutable availability order; never writes live storage."""
import asyncio
from .market import CandleEngine


class Replay:
    def __init__(self, events, symbol, metadata=None):
        self.metadata = metadata or {}
        self.events = events
        self.symbol = symbol
        self.engine = CandleEngine()
        self.position = 0
        self.state = "ready" if events else "empty"
        self.speed = 20
        self.status_data = {"symbol":symbol,"source":"Yahoo Finance","interval":60,
                            "state":"replay","last_source_ms":None,"last_received_ms":None,
                            "event_count":0,"duplicate_count":0,"volume_status":"Recorded Yahoo reconciliation",
                            **{k:self.metadata[k] for k in ("expected_delay_seconds","data_label","price_unit","volume_unit") if k in self.metadata}}

    def meta(self):
        return {"state":self.state,"position":self.position,"total":len(self.events),
                "clock_ms":self.engine.clock_ms or None,
                "first_received_ms": self.events[0]["received_ms"] if self.events else None,
                "last_received_ms":self.events[-1]["received_ms"] if self.events else None}

    def reset(self):
        self.__init__(self.events,self.symbol,self.metadata)

    def step(self):
        if self.position >= len(self.events):
            self.state = "finished" if self.events else "empty"
            return None
        event = self.events[self.position]
        changes = self.engine.apply(event)
        self.position += 1
        if event["kind"] == "quote":
            self.status_data.update(last_source_ms=max(self.status_data["last_source_ms"] or 0,event["source_ms"]),
                                    last_received_ms=event["received_ms"],last_event_id=event["id"])
        self.status_data["event_count"] = self.position
        if self.position == len(self.events):
            self.state = "finished"
        return {"type":"update","event":event,"candles":changes,"status":self.status_data.copy(),"replay":self.meta()}

    async def serve(self, ws):
        await ws.send_json({"type":"snapshot","candles":[],"status":self.status_data,"mode":"replay","replay":self.meta()})
        command = asyncio.create_task(ws.receive_json())
        delay = 0
        try:
            while True:
                started = asyncio.get_running_loop().time()
                was_playing = self.state == "playing"
                if was_playing:
                    done,_ = await asyncio.wait({command},timeout=delay)
                else:
                    done,_ = await asyncio.wait({command})
                if command in done:
                    message = command.result()
                    if was_playing:
                        delay = max(0, delay-(asyncio.get_running_loop().time()-started))
                    action = message.get("action")
                    self.speed = max(1,min(float(message.get("speed",self.speed)),100))
                    if action == "restart":
                        self.reset()
                        self.speed = max(1,min(float(message.get("speed",20)),100))
                        await ws.send_json({"type":"snapshot","candles":[],"status":self.status_data,"mode":"replay","replay":self.meta()})
                        self.state = "playing" if self.events else "empty"
                    elif action in ("start","resume") and self.position < len(self.events):
                        self.state = "playing"
                    elif action == "pause" and self.state == "playing":
                        self.state = "paused"
                    await ws.send_json({"type":"status","status":self.status_data,"replay":self.meta()})
                    command = asyncio.create_task(ws.receive_json())
                    if action in ("start","restart"):
                        delay = 0
                elif self.state == "playing":
                    result = self.step()
                    if result:
                        await ws.send_json(result)
                    if self.position < len(self.events):
                        previous = self.events[self.position-1]["received_ms"]
                        upcoming = self.events[self.position]["received_ms"]
                        delay = max(0,(upcoming-previous)/1000/self.speed)
        finally:
            command.cancel()
            await asyncio.gather(command,return_exceptions=True)
