import asyncio
from contextlib import asynccontextmanager
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from queue import Empty
from multiprocessing import Queue
import uvicorn

from messages import market_data

clients: set[WebSocket] = set()
out_q: "Queue | None" = None
in_q: "Queue | None" = None
trades = deque(maxlen=10000)

async def broadcast(msg: dict) -> None:
    disconnected = []
    for client in clients:
        try:
            await client.send_json(msg)
        except:
            disconnected.append(client)
    for client in disconnected:
        clients.remove(client)

async def market_data_publisher() -> None:
    loop = asyncio.get_event_loop()
    while True:
        try:
            msg = await loop.run_in_executor(None, lambda: in_q.get(timeout=0.1))
            match msg:
                case market_data.Trade():
                    trade = {
                        "type": "trade",
                        "ts": int(msg.ts.timestamp()),
                        "px": str(msg.px),
                        "qty": msg.qty,
                        "aggressor_side": msg.aggressor_side.value
                    }
                    await broadcast(trade)
                    trades.append(trade)
                case market_data.L1Quote():
                    await broadcast({
                        "type": "l1_quote",
                        "ts": int(msg.ts.timestamp()),
                        "bid_px": str(msg.bid_px) if msg.bid_px else None,
                        "ask_px": str(msg.ask_px) if msg.ask_px else None
                    })
                case market_data.L2Update():
                    await broadcast({
                        "type": "l2_update",
                        "bids": [[str(px), qty] for px, qty in msg.bids],
                        "asks": [[str(px), qty] for px, qty in msg.asks] 
                    })
        except Empty:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = asyncio.create_task(market_data_publisher())
    yield
    t.cancel() 

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.post("/restart")
async def restart_simulation():
    trades.clear()
    out_q.put("")
    return None

@app.get("/trades")
async def get_trades():
    return list(trades)

@app.websocket("/ws")
async def ws_handler(ws: WebSocket) -> None:
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive()
    except (WebSocketDisconnect, RuntimeError):
        clients.remove(ws)

async def main():
    out_q.put("");
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=80))
    await server.serve()

def run_server(_in_q: Queue, _out_q: Queue) -> None:
    global in_q
    global out_q
    in_q, out_q = _in_q, _out_q
    asyncio.run(main())
