import logging

from messages import events, reqs 
from commons import RejectReason

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
        self._orders: dict[str, Order] = {}
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
            case _:
                self._logger.warning("no match for %s", type(req))

    def _on_l2_snapshot_request(self, req: reqs.GetL2Snapshot) -> None:
        self._event_bus.send(req.client_id, self._matching_engine.l2_snapshot)
    
    def _on_new_order_request(self, req: reqs.NewOrder) -> None:
        order = Order.from_new_order_request(req, f"{self._seq_num:05d}")
        self._seq_num = (self._seq_num + 1) % 1000
        self._event_bus.send(
            order.client_id, 
            events.OrderAccepted(
                client_id=order.client_id,
                request_id=req.request_id,
                order_id=order.order_id
            )
        )
        self._orders[order.order_id] = order
        self._logger.info("matching_engine.new() %s", order)
        self._matching_engine.new(order)
        self._matching_engine.print()

    def _on_cancel_order_request(self, req: reqs.CancelOrder) -> None:
        order = self._orders.get(req.order_id, None)
        if not order:
            self._logger.warning("order cancel rejected: order %s not found", req.order_id)
            msg = events.OrderCancelRejected(
                ts=req.ts,
                client_id=req.client_id, 
                request_id=req.request_id, 
                order_id=req.order_id,
                reason=RejectReason.NOT_FOUND
            )
            self._event_bus.send(req.client_id, msg)
            return 
        
        if not order.is_live or order.client_id != req.client_id:
            self._logger.warning("order cancel rejected: order %s is %s", req.order_id, order.status.value)
            msg = events.OrderCancelRejected(
                ts=req.ts,
                client_id=req.client_id, 
                request_id=req.request_id, 
                order_id=req.order_id,
                reason=RejectReason.ILLEGAL_OP
            )
            self._event_bus.send(req.client_id, msg)
            return 

        self._logger.info("matching_engine.cancel() %s", order)
        self._matching_engine.cancel(order)
        self._matching_engine.print()
        del self._orders[req.order_id]