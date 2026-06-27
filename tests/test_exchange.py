from dataclasses import dataclass
from decimal import Decimal
from multiprocessing import Queue
import pytest
from queue import Empty
import threading
from uuid import uuid4

from src.exchange import Exchange
from src.commons import Message, OrderType, Side
from src.messages import reqs, events

@dataclass
class LocalMQ:
    send_q: Queue
    rcv_q: Queue
    
    def subscribe(self, client_id: str, callback) -> None:
        while True: 
            try:
                msg = self.rcv_q.get(timeout=0.1) 
                callback(msg)
            except Empty:
                continue

    def send(self, client_id: str, message: Message) -> None:
        self.send_q.put(message)

    def publish(self, message: Message) -> None:
        self.send_q.put(message)

def run_exchange(send_q: Queue, rcv_q: Queue):
    exch = Exchange(LocalMQ(send_q, rcv_q))
    exch.run()

@pytest.fixture
def queues():
    client_to_exchange = Queue()
    exchange_to_client = Queue()
    t = threading.Thread(
        target=run_exchange, 
        args=(exchange_to_client, client_to_exchange), 
        daemon=True
    )
    t.start()

    return client_to_exchange, exchange_to_client

def test_new_order(queues):
    client_to_exchange, exchange_to_client = queues
    request_id = str(uuid4())
    client_id = "test1"
    client_to_exchange.put(
        reqs.NewOrder(
            request_id=request_id,
            client_id=client_id,
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            qty=10,
            limit_px=Decimal(5),
        )
    )

    res = exchange_to_client.get()
    assert isinstance(res, events.OrderAccepted)
    assert res.request_id == request_id
    assert res.client_id == client_id

