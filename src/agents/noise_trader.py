from datetime import datetime
import random
from uuid import uuid4

from .agent import Agent
from messages import events, market_data, reqs
from commons import OrderType, Side

class NoiseTrader(Agent):
    def _on_quote(self, msg: market_data.L1Quote):
        if random.random() > 0.5: 
            self.submit(reqs.NewOrder(
                ts=datetime.now(),
                client_id=self._client_id,
                request_id=uuid4(),
                order_type=OrderType.MARKET,
                side=Side.BUY if random.random() > 0.5 else Side.SELL,
                limit_price=None,
                qty=random.randrange(1, 10),
            ))

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

    