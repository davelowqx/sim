from abc import ABC, abstractmethod
import logging

from messages import Message, events, market_data, reqs
from commons import MQClient, MQTopic

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
                self._on_quote(msg)
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
    
    def submit(self, req: reqs.Request) -> None:
        self._mq_client.publish(MQTopic.ORDER_ENTRY, req)

    @abstractmethod
    def _on_quote(self, msg: market_data.L1Quote):
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

    