from decimal import Decimal
from commons import MQClient

from .agent import Agent
from messages import events, market_data, reqs

class MarketMaker(Agent):
    def __init__(self, client_id: str, mq_client: MQClient):
        super().__init__(client_id, mq_client)
        self.last_bid = Decimal(0)
        self.last_ask = Decimal(0)

    def _on_quote(self, msg: market_data.L1Quote):
        curr_bid = msg.bid[0] if msg.bid else None
        curr_ask = msg.ask[0] if msg.ask else None

        if curr_bid != self.last_bid:
            pass

        if curr_ask != self.last_ask:
            pass

    def _on_order_accepted(self, ev: events.OrderAccepted):
        ...

    def _on_order_rejected(self, ev: events.OrderRejected):
        ...

    def _on_order_executed(self, ev: events.OrderExecuted):
        ...

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        ...

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        ...

    