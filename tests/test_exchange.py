from decimal import Decimal
from multiprocessing import Queue
import pytest
import threading
from uuid import uuid4

from exchange import Exchange, EventBus
from commons import OrderType, Side
from messages import reqs, events, market_data

CLIENT_ID = "pytest"

def run_exchange(event_bus: EventBus):
    exch = Exchange(event_bus)
    exch.run()

@pytest.fixture
def queues():
    client_to_exchange, exchange_to_client = Queue(), Queue()
    event_bus = EventBus(
        send_qs={CLIENT_ID: exchange_to_client}, 
        rcv_q=client_to_exchange
    )
    t = threading.Thread(
        target=run_exchange, 
        args=(event_bus,), 
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



