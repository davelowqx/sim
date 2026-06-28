import random

from .agent import Agent
from messages import events, market_data
from commons import Side

class NoiseTrader(Agent):
    def _on_l1_quote(self, msg: market_data.L1Quote):
        if random.random() > 0.5:  
            side = Side.BUY if random.random() > 0.5 else Side.SELL, 
            self.send_market_order(side=side, qty=1)

    def _on_l2_update(self, msg: market_data.L2Update):
        super()._on_l2_update(msg)

    def _on_trade(self, msg: market_data.Trade):
        super()._on_trade(msg)

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

    