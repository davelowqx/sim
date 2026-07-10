from abc import ABC, abstractmethod
import logging

from messages import Message, events, market_data

from .exchange_adapter import ExchangeAdapter

class Agent(ABC):
    def __init__(self, client_id: str, exchange_adapter: ExchangeAdapter):
        self._logger = logging.getLogger(client_id)
        self._client_id = client_id
        self._exch = exchange_adapter

    def run(self):
        self._logger.info("running")
        self._exch.subscribe(self._on_startup, self._dispatch, self._on_timeout)

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
    
    @abstractmethod
    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    @abstractmethod
    def _on_l2_update(self, msg: market_data.L2Update):
        ...

    @abstractmethod
    def _on_trade(self, msg: market_data.Trade):
        ...

    @abstractmethod
    def _on_order_accepted(self, ev: events.OrderAccepted):
        ...

    @abstractmethod
    def _on_order_rejected(self, ev: events.OrderRejected):
        ...

    @abstractmethod
    def _on_order_executed(self, ev: events.OrderExecuted):
        ...

    @abstractmethod
    def _on_order_cancelled(self, ev: events.OrderCancelled):
        ...

    @abstractmethod
    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        ...
    
    @abstractmethod
    def _on_startup(self):
        ...

    @abstractmethod
    def _on_timeout(self):
        ...

    