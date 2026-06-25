import logging

from messages import reqs, events
from commons import RejectReason, MQClient, MQTopic
from .order import Order
from .matching_engine import MatchingEngine

class Exchange:
    def __init__(self, mq_client: MQClient):
        self._logger = logging.getLogger("matching_engine")
        self._mq_client = mq_client
        self._matching_engine = MatchingEngine()

        self._request_ids: set[str] = set()
        self._orders: dict[str, Order] = {}
        self._client_ids : list[str] = []

    def run(self) -> None:
        self._logger.info("running")
        self._mq_client.subscribe(MQTopic.ORDER_ENTRY, self._dispatch)
    
    def _dispatch(self, req: reqs.Request):
        if req.request_id in self._request_ids:
            self._logger.warning("duplicate request %s ignored", req.request_id)
            return 

        match req:
            case reqs.NewOrder():
                self._on_new_order_request(req)
            case reqs.CancelOrder():
                self._on_cancel_order_request(req)
            case reqs.GetL2Snapshot():
                self._on_l2_snapshot_request(req)

    def _on_l2_snapshot_request(self, req: reqs.GetL2Snapshot) -> None:
        l2_snapshot = self._matching_engine.get_l2_snapshot() 
        self._mq_client.publish([req.client_id], l2_snapshot)
    
    def _on_new_order_request(self, req: reqs.NewOrder) -> None:
        order = Order.from_new_order_request(req)
        self._matching_engine.new(order)

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
            self._mq_client.publish(req.client_id, msg)
            return 
        
        if not order.is_live or order.client_id != req.client_id:
            self._logger.warning("order cancel rejected: illegal operation")
            msg = events.OrderCancelRejected(
                ts=req.ts,
                client_id=req.client_id, 
                request_id=req.request_id, 
                order_id=req.order_id,
                reason=RejectReason.ILLEGAL_OP
            )
            self._mq_client.publish(req.client_id, msg)
            return 
                         
        self._matching_engine.cancel(order)