import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from queue import Empty
from multiprocessing import Queue, Event
import uvicorn

from messages import market_data

client: WebSocket | None = None
stop_event: Event | None = None
start_event: Event | None = None
in_q: Queue | None = None

async def market_data_publisher() -> None:
    loop = asyncio.get_event_loop()
    while True:
        try:
            msg = await loop.run_in_executor(None, lambda: in_q.get(timeout=0.1))
            if client:
                match msg:
                    case market_data.Trade():
                        await client.send_json({
                            "type": "trade",
                            "ts": int(msg.ts.timestamp()),
                            "px": str(msg.px),
                            "qty": msg.qty,
                        })
                    case market_data.L1Quote():
                        await client.send_json({
                            "type": "bbo",
                            "ts": int(msg.ts.timestamp()),
                            "bid_px": str(msg.bid_px) if msg.bid_px else None,
                            "ask_px": str(msg.ask_px) if msg.ask_px else None
                        })
        except Empty:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = asyncio.create_task(market_data_publisher())
    yield
    t.cancel() 

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def handler(ws: WebSocket) -> None:
    global client
    await ws.accept()
    client = ws
    stop_event.clear()
    start_event.set()
    try:
        while True:
            await ws.receive()
    except (WebSocketDisconnect, RuntimeError):
        start_event.clear()
        stop_event.set()
        client = None

async def f():
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000))
    await server.serve()

def run_server(_start_event: Event, _stop_event: Event, _in_q: Queue) -> None:
    global start_event
    global stop_event
    global in_q
    start_event, stop_event, in_q = _start_event, _stop_event, _in_q
    asyncio.run(f())
