from decimal import Decimal

from commons import Side, OrderType
from messages import events, market_data

from .agent import Agent
from .order import Order, OrderStatus
from .exchange_adapter import ExchangeAdapter

class MarketMaker(Agent):
    def __init__(self, offset: Decimal, client_id: str, exchange_adapter: ExchangeAdapter):
        super().__init__(client_id, exchange_adapter)

        self._orders : dict[str, Order] = {}

        self._last_trade = market_data.Trade(px=Decimal("10"), qty=1)
        self._offset = offset
        self._delta = 0
    
    @property
    def _curr_bid(self) -> Order | None:
        for order in self._orders.values():
            if order.side == Side.BUY:
                return order
        return None

    @property
    def _curr_ask(self) -> Order | None:
        for order in self._orders.values():
            if order.side == Side.SELL:
                return order
        return None

    def _new_quote(self, side: Side, limit_px: Decimal):
        order = self._exch.submit(
            order_type=OrderType.LIMIT,
            side=side, 
            qty=10,
            limit_px=limit_px,
        )
        self._orders[order.request_id] = order
    
    def _cancel_quote(self, side: Side):
        order = self._curr_bid if side == Side.BUY else self._curr_ask
        self._exch.cancel(order.order_id)
        order.status = OrderStatus.PENDING_CANCEL
    
    def _target_bid_px(self):
        return self._last_trade.px - self._offset - (self._delta * Decimal("0.01"))
    
    def _target_ask_px(self):
        return self._last_trade.px + self._offset - (self._delta * Decimal("0.01"))
    
    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    def _on_l2_update(self, msg: market_data.L2Update):
        ...
    
    def _on_trade(self, msg: market_data.Trade):
        self._last_trade = msg
        if (self._curr_bid is not None
            and not self._curr_bid.is_pending 
            and self._target_bid_px() != self._curr_bid.limit_px): 
            self._cancel_quote(Side.BUY)
        if (self._curr_ask is not None
            and not self._curr_ask.is_pending
            and self._target_ask_px() != self._curr_ask.limit_px):
            self._cancel_quote(Side.SELL)

    def _on_order_accepted(self, ev: events.OrderAccepted):
        order = self._orders[ev.request_id]
        order.live(ev)
        self._orders[ev.order_id] = order 
        del self._orders[ev.request_id]

    def _on_order_rejected(self, ev: events.OrderRejected):
        order = self._orders[ev.request_id]
        order.reject(ev)
        del self._orders[ev.request_id]

    def _on_order_executed(self, ev: events.OrderExecuted):
        super()._on_order_executed(ev)
        order = self._orders[ev.order_id]
        order.fill(ev)
        self._delta += ev.qty * (1 if order.is_buy else -1)
        if order.unfilled_qty == 0:
            del self._orders[ev.order_id]

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        super()._on_order_cancelled(ev)
        order = self._orders[ev.order_id]
        order.cancel(ev)
        del self._orders[ev.order_id]

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        if order := self._orders.get(ev.order_id):
            self._logger.warning("%s is %s", ev.order_id, order.status.value)
    
    def _on_empty(self):
        self._logger.info("delta=%s, orders=%s", self._delta, [str(order) for order in self._orders.values()])
        if self._curr_bid is None or self._curr_bid.is_terminal:
            self._new_quote(Side.BUY, self._target_bid_px())
        if self._curr_ask is None or self._curr_ask.is_terminal:
            self._new_quote(Side.SELL, self._target_ask_px())

    