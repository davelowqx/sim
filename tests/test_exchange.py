from dataclasses import dataclass
from decimal import Decimal
from multiprocessing import Queue
import pytest
from queue import Empty
import threading
from uuid import uuid4

from exchange import Exchange
from commons import Message, OrderType, Side
from messages import reqs, events, market_data

CLIENT_ID = "pytest"

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

def test(queues):
    client_to_exchange, exchange_to_client = queues

    dct = {
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            qty=10,
            limit_px=Decimal("2.99"),
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, market_data.L1Quote),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            qty=15,
            limit_px=Decimal("2.99"),
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, market_data.L1Quote),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.LIMIT,
            side=Side.BUY,
            qty=10,
            limit_px=Decimal("2.98"),
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.LIMIT,
            side=Side.SELL,
            qty=10,
            limit_px=Decimal("3.01"),
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, market_data.L1Quote),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.LIMIT,
            side=Side.SELL,
            qty=10,
            limit_px=Decimal("3.05"),
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.MARKET,
            side=Side.SELL,
            qty=5,
            limit_px=None
        ): [
            lambda msg: isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg: isinstance(msg, market_data.L1Quote),
            lambda msg: isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.MARKET,
            side=Side.SELL,
            qty=25,
            limit_px=None
        ): [
            lambda msg : isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg : isinstance(msg, market_data.L1Quote),
            lambda msg : isinstance(msg, market_data.L2Update)
        ],
        reqs.NewOrder(
            request_id=str(uuid4()),
            client_id=CLIENT_ID,
            order_type=OrderType.MARKET,
            side=Side.BUY,
            qty=15,
            limit_px=None
        ): [
            lambda msg : isinstance(msg, events.OrderAccepted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, events.OrderExecuted),
            lambda msg: isinstance(msg, market_data.Trade),
            lambda msg : isinstance(msg, market_data.L1Quote),
            lambda msg : isinstance(msg, market_data.L2Update)
        ]
    }

    for req, callbacks in dct.items():
        client_to_exchange.put(req)
        for callback in callbacks:
            msg = exchange_to_client.get()
            print(msg)
            assert callback(msg)



