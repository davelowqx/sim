from decimal import Decimal

from commons import Side, OrderType
from messages import events, market_data

from .agent import Agent
from .order import Order, OrderStatus
from .exchange_adapter import ExchangeAdapter

TICKSIZE = Decimal("0.01")

class MarketMaker(Agent):
    def __init__(self, ticks_offset: Decimal, default_quote_qty: int, client_id: str, exchange_adapter: ExchangeAdapter):
        super().__init__(client_id, exchange_adapter)

        self._orders : dict[str, Order] = {}

        self._ticks_offset = ticks_offset
        self._default_quote_qty = default_quote_qty

        self._last_px = Decimal("10")

        self._delta = 0
    
    def _on_l1_quote(self, msg: market_data.L1Quote):
        ...

    def _on_l2_update(self, msg: market_data.L2Update):
        ...
    
    def _on_trade(self, msg: market_data.Trade):
        self._last_px = msg.px

        curr_bid = self._curr_bid
        if (curr_bid is not None and not curr_bid.is_pending 
            and self._is_outside_range(curr_bid.limit_px, self._target_bid_px)):
            self._exch.cancel(curr_bid.order_id)
            curr_bid.status = OrderStatus.PENDING_CANCEL
    
        curr_ask = self._curr_ask
        if (curr_ask is not None and not curr_ask.is_pending
            and self._is_outside_range(curr_ask.limit_px, self._target_ask_px)):
            self._exch.cancel(curr_ask.order_id)
            curr_ask.status = OrderStatus.PENDING_CANCEL

    def _on_order_accepted(self, ev: events.OrderAccepted):
        order = self._orders[ev.request_id]
        order.live(ev)
        self._orders[ev.order_id] = order 
        del self._orders[ev.request_id]

    def _on_order_rejected(self, ev: events.OrderRejected):
        order = self._orders[ev.request_id]
        order.reject(ev)
        del self._orders[ev.request_id]
        self._new_quote(order.side)

    def _on_order_executed(self, ev: events.OrderExecuted):
        order = self._orders[ev.order_id]
        order.fill(ev)
        self._delta += ev.qty * (1 if order.is_buy else -1)
        if order.unfilled_qty == 0:
            del self._orders[ev.order_id]
            self._new_quote(order.side)

    def _on_order_cancelled(self, ev: events.OrderCancelled):
        order = self._orders[ev.order_id]
        order.cancel(ev)
        del self._orders[ev.order_id]
        self._new_quote(order.side)

    def _on_order_cancel_rejected(self, ev: events.OrderCancelRejected):
        if order := self._orders.get(ev.order_id):
            self._logger.error("Order %s cancel rejected, status: %s", ev.order_id, order.status.value)
    
    def _on_startup(self):
        self._new_quote(Side.BUY)
        self._new_quote(Side.SELL)

    def _on_timeout(self):
        self._logger.info("delta=%s, orders=%s", self._delta, [str(order) for order in self._orders.values()])

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
    
    @property
    def _abs_delta(self) -> int:
        return int(abs(self._delta) / 100)

    @property
    def _target_bid_px(self) -> Decimal:
        if self._delta > 0:
            return self._last_px - (self._ticks_offset + self._abs_delta) * TICKSIZE
        return self._last_px - (self._ticks_offset * TICKSIZE)

    @property
    def _target_bid_qty(self) -> Decimal:
        return max(self._abs_delta, self._default_quote_qty) if self._delta < 0 else self._default_quote_qty

    @property
    def _target_ask_px(self) -> Decimal:
        if self._delta < 0:
            return self._last_px + (self._ticks_offset + self._abs_delta) * TICKSIZE
        return self._last_px + (self._ticks_offset * TICKSIZE)

    @property
    def _target_ask_qty(self) -> Decimal:
        return max(self._abs_delta, self._default_quote_qty) if self._delta > 0 else self._default_quote_qty
    
    @staticmethod
    def _is_outside_range(curr_px: Decimal, target_px: Decimal) -> bool:
        return not (target_px - TICKSIZE <= curr_px <= target_px + TICKSIZE)

    def _new_quote(self, side: Side):
        order = self._exch.submit(
            order_type=OrderType.LIMIT,
            side=side, 
            qty=self._target_bid_qty if side == Side.BUY else self._target_ask_qty,
            limit_px=self._target_bid_px if side == Side.BUY else self._target_ask_px
        )
        self._orders[order.request_id] = order
    