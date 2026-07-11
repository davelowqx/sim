import logging

from messages import events, reqs 
from commons import OrderType

from .event_bus import EventBus
from .matching_engine import MatchingEngine
from .rolling_set import RollingSet
from .order import Order

class Exchange:
    def __init__(self, event_bus: EventBus):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._event_bus = event_bus
        self._matching_engine = MatchingEngine(event_bus)

        self._request_ids = RollingSet()
        self._live_orders: dict[str, Order] = {}
        self._seq_num = 0

    def run(self) -> None:
        self._logger.info("running")
        self._event_bus.subscribe(self._dispatch)
    
    def _dispatch(self, req: reqs.Request):
        if req.request_id in self._request_ids:
            self._logger.warning("duplicate request %s ignored", req.request_id)
            return 
        self._request_ids.add(req.request_id)

        match req:
            case reqs.NewOrder():
                self._on_new_order_request(req)
            case reqs.CancelOrder():
                self._on_cancel_order_request(req)
            case reqs.GetL2Snapshot():
                self._on_l2_snapshot_request(req)
        
    def _on_l2_snapshot_request(self, req: reqs.GetL2Snapshot) -> None:
        self._event_bus.send(req.client_id, self._matching_engine.l2_snapshot)
    
    def _on_new_order_request(self, req: reqs.NewOrder) -> None:
        if req.order_type == OrderType.LIMIT and req.limit_px <= 0:
            self._event_bus.send(
                req.client_id,
                events.OrderRejected(
                    request_id=req.request_id,
                    client_id=req.client_id,
                )
            )
            return
        order = Order.from_new_order_request(req, f"{self._seq_num:06d}")
        self._seq_num = (self._seq_num + 1) % 1000000
        self._event_bus.send(
            order.client_id, 
            events.OrderAccepted(
                client_id=order.client_id,
                request_id=req.request_id,
                order_id=order.order_id
            )
        )
        for order_id in self._matching_engine.new(order):
            del self._live_orders[order_id]

        if order.order_type == OrderType.LIMIT and not order.is_terminal:
            self._live_orders[order.order_id] = order

        if len(self._live_orders) > 6:
            self._logger.warning("orders = %s", [f"{o.client_id}-{o.order_id}" for o in self._live_orders.values()])


    def _on_cancel_order_request(self, req: reqs.CancelOrder) -> None:
        order = self._live_orders.get(req.order_id, None)
        if not order or not order.is_live or order.client_id != req.client_id:
            self._logger.warning("order cancel rejected: order %s is %s", req.order_id, order.status.value if order else "not found")
            msg = events.OrderCancelRejected(
                ts=req.ts,
                client_id=req.client_id, 
                request_id=req.request_id, 
                order_id=req.order_id,
            )
            self._event_bus.send(req.client_id, msg)
            return 

        for order_id in self._matching_engine.cancel(order):
            del self._live_orders[order_id]