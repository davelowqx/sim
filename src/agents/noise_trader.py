from decimal import Decimal
import math
import random

from messages import events, market_data
from commons import Side, OrderType

from .agent import Agent
from .exchange_adapter import ExchangeAdapter

class NoiseTrader(Agent):
    def __init__(self, client_id: str, exchange_adapter: ExchangeAdapter):
        super().__init__(client_id, exchange_adapter)
        self._last_trade : market_data.Trade | None = None

    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    def _on_l2_update(self, msg: market_data.L2Update):
        ...

    def _on_trade(self, msg: market_data.Trade):
        self._last_trade = msg

    def _on_order_accepted(self, ev: events.OrderAccepted):
        super()._on_order_accepted(ev)

    def _on_order_rejected(self, ev: events.OrderRejected):
        super()._on_order_rejected(ev)

    def _on_order_executed(self, ev: events.OrderExecuted):
        super()._on_order_executed(ev)

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        super()._on_order_cancelled(ev)

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        super()._on_order_rejected(ev)
    
    @property
    def _buy_probability(self) -> float:
        if self._last_trade is None:
            return 0.5
        if self._last_trade.px < 1:
            return 1
        deviation = float((self._last_trade.px - Decimal("10")) / Decimal("10"))
        return 1 / (1 + math.exp(deviation))
    
    def _on_empty(self):
        if random.random() > 0.5:  
            return

        side = Side.BUY if random.random() < self._buy_probability else Side.SELL
        self._exch.submit(
            order_type=OrderType.MARKET,
            side=side, 
            qty=random.randrange(1, 10),
            limit_px=None
        )
    