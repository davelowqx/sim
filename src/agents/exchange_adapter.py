from decimal import Decimal
from uuid import uuid4
from queue import Empty
from multiprocessing import Queue

from commons import OrderType, Side
from messages import reqs

from .order import Order

class ExchangeAdapter:
    def __init__(self, client_id: str, send_q: Queue, rcv_q: Queue):
        self._client_id = client_id
        self._send_q = send_q
        self._rcv_q = rcv_q

    def subscribe(self, init_func, msg_callback, timeout_callback) -> None:
        init_func()
        while True: 
            try:
                msg = self._rcv_q.get(timeout=1) 
                msg_callback(msg)
            except Empty:
                timeout_callback()

    def submit(self, order_type: OrderType, side: Side, qty: int, limit_px: Decimal | None) -> Order:
        request_id = str(uuid4())
        req = reqs.NewOrder(
            client_id=self._client_id,
            request_id=request_id,
            order_type=order_type,
            side=side,
            qty=qty,
            limit_px=limit_px,
        )
        self._send_q.put(req)
        return Order(
            request_id=request_id,
            order_type=order_type,
            side=side,
            limit_px=limit_px,
            qty=qty
        )
    
    def cancel(self, order_id: str) -> None:
        req = reqs.CancelOrder(
            client_id=self._client_id, 
            request_id=str(uuid4()),
            order_id=order_id
        )
        self._send_q.put(req)
