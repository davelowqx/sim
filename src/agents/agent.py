from abc import ABC, abstractmethod
from decimal import Decimal
import logging
from uuid import uuid4

from order import Order
from messages import Message, events, market_data, reqs
from commons import OrderType, Side, MQClient, MQTopic

class Agent(ABC):
    def __init__(self, client_id: str, mq_client: MQClient):
        self._logger = logging.getLogger(client_id)
        self._client_id = client_id
        self._mq_client = mq_client

    def run(self):
        self._logger.info("running")
        self._mq_client.subscribe(self._client_id, self._dispatch)

    def _dispatch(self, msg: Message):
        match msg:
            case market_data.L1Quote():
                self._on_l1_quote(msg)
            case market_data.L2Update():
                self._on_l2_update(msg)
            case market_data.Trade():
                self._on_trade(msg)
            case events.OrderAccepted():
                self._on_order_accepted(msg)
            case events.OrderRejected():
                self._on_order_rejected(msg)
            case events.OrderExecuted():
                self._on_order_executed(msg)
            case events.OrderCancelled():
                self._on_order_cancelled(msg)
            case events.OrderCancelRejected():
                self._on_order_cancel_rejected(msg)
    
    def send_market_order(self, side: Side, qty: int) -> Order:
        request_id = str(uuid4())
        req = reqs.NewOrder(
            self._client_id,
            request_id=request_id,
            order_type=OrderType.MARKET,
            side=side,
            qty=qty
        )
        self._mq_client.publish(MQTopic.ORDER_ENTRY, req)
        return Order(
            request_id=request_id,
            order_type=OrderType.MARKET,
            side=side,
            limit_px=None,
            qty=qty
        )
    
    def send_limit_order(self, side: Side, qty: int, limit_px: Decimal) -> Order:
        request_id = str(uuid4())
        req = reqs.NewOrder(
            self._client_id,
            request_id=request_id,
            order_type=OrderType.LIMIT,
            side=side,
            limit_px=limit_px,
            qty=qty
        )
        self._mq_client.publish(MQTopic.ORDER_ENTRY, req)
        return Order(
            request_id=request_id,
            order_type=OrderType.LIMIT,
            side=side,
            limit_px=limit_px,
            qty=qty
        )
    
    def send_cancel_order_request(self, order_id: str) -> None:
        req = reqs.CancelOrder(
            client_id=self._client_id, 
            request_id=uuid4(),
            order_id=order_id
        )
        self._mq_client.publish(MQTopic.ORDER_ENTRY, req)

    @abstractmethod
    def _on_l1_quote(self, msg: market_data.L1Quote):
        print(msg)

    @abstractmethod
    def _on_l2_update(self, msg: market_data.L2Update):
        print(msg)

    @abstractmethod
    def _on_trade(self, msg: market_data.Trade):
        print(msg)

    @abstractmethod
    def _on_order_accepted(self, ev: events.OrderAccepted):
        print(ev)

    @abstractmethod
    def _on_order_rejected(self, ev: events.OrderRejected):
        print(ev)

    @abstractmethod
    def _on_order_executed(self, ev: events.OrderExecuted):
        print(ev)

    @abstractmethod
    def _on_order_cancelled(self, ev: events.OrderCancelled):
        print(ev)

    @abstractmethod
    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        print(ev)

    