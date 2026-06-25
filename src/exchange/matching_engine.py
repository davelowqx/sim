from datetime import datetime
from sortedcontainers import SortedDict

from commons import Side, OrderType
from messages import market_data
from .order import Order

class PriceLevel:
    def __init__(self, order: Order):
        self.agg_qty: int = order.unfilled_qty
        self.first_order = order
        self.last_order = order
    
    def fill(self, incoming_order: Order):
        curr_order = self.first_order
        while incoming_order.unfilled_qty > 0 and curr_order is not None:
            fill_qty = min(curr_order.unfilled_qty, incoming_order.unfilled_qty)
            self.agg_qty -= fill_qty
            incoming_order.fill(fill_qty)
            curr_order.fill(fill_qty)

            if curr_order.unfilled_qty == 0:
                curr_order = curr_order.next_order

class MatchingEngine:
    def __init__(self):
        self._bids = SortedDict(key=lambda x: -x)
        self._asks = SortedDict()
    
    def _same_side(self, side: Side) -> SortedDict:
        return self._bids if side == Side.BUY else self._asks

    def _opp_side(self, side: Side) -> SortedDict:
        return self._bids if side == Side.SELL else self._asks
    
    def get_l1_snapshot(self) -> market_data.L1Quote:
        bid, ask = None, None
        if len(self._bids) != 0:
            px, level = self._bids.peekitem(0)
            bid = (px, level.agg_qty)
        if len(self._asks) != 0:
            px, level = self._asks.peekitem(0)
            ask = (px, level.agg_qty)

        return market_data.L1Quote(
            ts=datetime.now(),
            bid=bid,
            ask=ask
        )
    
    def get_l2_snapshot(self) -> market_data.L2Snapshot:
        market_data.L2Snapshot(
            ts=datetime.now(),
            bids=[(px, level.agg_qty) for px, level in self._bids.items()],
            asks=[(px, level.agg_qty) for px, level in self._asks.items()],
        )

    def new(self, order: Order) -> None:
        levels = self._opp_side(order.side)
        while order.unfilled_qty > 0 and len(levels) > 0:
            px, level = levels.peekitem(0)
            if not order.can_match(px):
                break
            level.fill(order)
            if level.agg_qty == 0:
                del levels[px]

        if order.is_filled:
            return
        
        if order.order_type == OrderType.MARKET:
            order.cancel() # cancel remaining qty
            return

        levels = self._same_side(order.side)
        if levels.get(order.price) is None:
            levels[order.price] = PriceLevel(order)
        else:
            prev_last_order: Order = levels[order.price].last_order
            prev_last_order.next_order = order
            levels[order.price].last_order = order
            order.prev_order = prev_last_order

    def cancel(self, order: Order) -> None:
        level: PriceLevel = self._same_side(order.side)[order.price]
        level.agg_qty -= order.unfilled_qty
        if level.first_order == order:
            level.first_order = order.next_order
        
        if level.last_order == order:
            level.last_order = order.prev_order

        if order.prev_order is not None:
            order.prev_order.next_order = order.next_order
        
        if order.next_order is not None:
            order.next_order.prev_order = order.prev_order
        
        order.next_order = None
        order.prev_order = None
        order.cancel()