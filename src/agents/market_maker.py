from decimal import Decimal

from .agent import Agent
from .order import Order, OrderStatus
from commons import Side, MQClient
from messages import events, market_data

class MarketMaker(Agent):
    def __init__(self, client_id: str, mq_client: MQClient):
        super().__init__(client_id, mq_client)

        self._pending_orders : dict[str, Order]
        self._live_orders : dict[str, Order]

        self._curr_bid : Order | None = None
        self._curr_ask : Order | None = None

        self._offset = Decimal(0.03)
        self._qty = 10
    
    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    def _on_l2_update(self, msg: market_data.L2Update):
        ...
    
    def _on_trade(self, msg: market_data.Trade):
        if self._curr_bid is None or self._curr_bid.is_terminal:
            self._curr_bid = self.send_limit_order(
                side=Side.BUY,
                qty=self._qty,
                limit_px=msg.px - self._offset
            )
            self._pending_orders[self._curr_bid.request_id] = self._curr_bid
        elif (not self._curr_bid.is_pending and 
                msg.px - self._offset != self._curr_bid.limit_px):
            self.send_cancel_order_request(self._curr_bid.order_id)
            self._curr_bid.status = OrderStatus.PENDING_CANCEL

        if self._curr_ask is None or self._curr_ask.is_terminal:
            self._curr_ask = self.send_limit_order(
                side=Side.SELL,
                qty=self._qty,
                limit_px=msg.px + self._offset
            )
            self._pending_orders[self._curr_ask.request_id] = self._curr_ask
        elif (not self._curr_ask.is_pending and 
                msg.px + self._offset != self._curr_ask.limit_px):
            self.send_cancel_order_request(self._curr_ask.order_id)
            self._curr_ask.status = OrderStatus.PENDING_CANCEL

    def _on_order_accepted(self, ev: events.OrderAccepted):
        order = self._pending_orders[ev.request_id]
        order.live(ev)
        self._live_orders[ev.order_id] = order 
        del self._pending_orders[ev.request_id]

    def _on_order_rejected(self, ev: events.OrderRejected):
        order = self._pending_orders[ev.request_id]
        order.reject(ev)

    def _on_order_executed(self, ev: events.OrderExecuted):
        order = self._live_orders[ev.order_id]
        order.fill(ev)
        if order.unfilled_qty == 0:
            del self._live_orders[ev.order_id]

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        order = self._live_orders[ev.order_id]
        order.cancel(ev)

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        ...

    