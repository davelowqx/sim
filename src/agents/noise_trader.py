from datetime import datetime, timedelta
from decimal import Decimal
import math
import random

from messages import events, market_data
from commons import Side, OrderType

from .agent import Agent
from .exchange_adapter import ExchangeAdapter

class NoiseTrader(Agent):
    def __init__(self, max_qty: int, trade_interval_ms: int, client_id: str, exchange_adapter: ExchangeAdapter):
        super().__init__(client_id, exchange_adapter)
        self._max_qty = max_qty
        self._trade_interval_ms = trade_interval_ms
        self._last_trade_px = Decimal("10")
        self._last_traded_ts = datetime.now()

    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    def _on_l2_update(self, msg: market_data.L2Update):
        self._maybe_market_order()

    def _on_trade(self, msg: market_data.Trade):
        self._last_trade_px = msg.px

    def _on_order_accepted(self, ev: events.OrderAccepted):
        ...

    def _on_order_rejected(self, ev: events.OrderRejected):
        self._maybe_market_order()

    def _on_order_executed(self, ev: events.OrderExecuted):
        self._maybe_market_order()

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        ...

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        ...
    
    def _on_startup(self):
        ...

    def _on_timeout(self):
        self._maybe_market_order()
    
    def _maybe_market_order(self):
        if (datetime.now() - self._last_traded_ts < timedelta(milliseconds=self._trade_interval_ms)):
            return
        
        if random.random() > 0.8:
            return

        self._last_traded_ts = datetime.now()

        side = Side.BUY if random.random() < self._buy_probability else Side.SELL
        self._exch.submit(
            order_type=OrderType.MARKET,
            side=side, 
            qty=random.randrange(1, self._max_qty),
            limit_px=None
        )
    
    @property
    def _buy_probability(self) -> float:
        deviation = float((self._last_trade_px - Decimal("10")) / Decimal("10"))
        return 1 / (1 + math.exp(deviation))
    