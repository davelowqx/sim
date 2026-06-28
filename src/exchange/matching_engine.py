from dataclasses import dataclass
from decimal import Decimal
from sortedcontainers import SortedDict

from commons import Side, OrderType, MQClient
from messages import market_data, events
from .order import Order

@dataclass
class PriceLevel:
    def __init__(self, mq_client: MQClient, side: Side, px: Decimal):
        self._mq_client = mq_client
        self.side = side
        self.px = px
        self.agg_qty = 0
        self._first_order : Order | None = None
        self._last_order : Order | None = None
    
    def match(self, incoming_order: Order):
        curr_order = self._first_order
        while incoming_order.unfilled_qty > 0 and curr_order is not None:
            fill_qty = min(curr_order.unfilled_qty, incoming_order.unfilled_qty)
            self.agg_qty -= fill_qty
            incoming_order.fill(fill_qty)
            curr_order.fill(fill_qty)
            self._mq_client.send(
                incoming_order.client_id,
                events.OrderExecuted(
                    client_id=incoming_order.client_id,
                    order_id=incoming_order.order_id,
                    px=curr_order.limit_px,
                    qty=fill_qty
                )
            )
            self._mq_client.send(
                curr_order.client_id,
                events.OrderExecuted(
                    client_id=curr_order.client_id,
                    order_id=curr_order.order_id,
                    px=curr_order.limit_px,
                    qty=fill_qty
                )
            )
            self._mq_client.publish(
                market_data.Trade(
                    px=curr_order.limit_px,
                    qty=fill_qty
                )
            )

            if curr_order.is_filled:
                curr_order = curr_order.next_order
        
    def add_resting_order(self, order: Order) -> None:
        if not self._first_order and not self._last_order:
            self._first_order = order
            self._last_order = order
        else:
            prev_last_order = self._last_order
            prev_last_order.next_order = order
            self._last_order = order
            order.prev_order = prev_last_order

        self.agg_qty += order.unfilled_qty

    def cancel(self, order: Order) -> None:
        if self._first_order == order:
            self._first_order = order.next_order
        else:
            order.prev_order.next_order = order.next_order
        
        if self._last_order == order:
            self._last_order = order.prev_order
        else:
            order.next_order.prev_order = order.prev_order

        self.agg_qty -= order.unfilled_qty

        l2_update = (
            market_data.L2Update(bids=[(self.px, self.agg_qty)], asks=[])
            if self.side == Side.BUY
            else market_data.L2Update(bids=[], asks=[(self.px, self.agg_qty)])
        )
        self._mq_client.publish(l2_update)
    
    def __str__(self) -> str:
        qtys = []
        curr_order = self._first_order
        while curr_order is not None:
            qtys.append(f"{curr_order.unfilled_qty}")
            curr_order = curr_order.next_order
        return f"${self.px}x{self.agg_qty}: [{','.join(qtys)}]"

class MatchingEngine:
    def __init__(self, mq_client: MQClient):
        self._mq_client = mq_client
        self._bids = SortedDict(lambda x: -x)
        self._asks = SortedDict()
    
    def _same_side(self, side: Side) -> SortedDict:
        return self._bids if side == Side.BUY else self._asks

    def _opp_side(self, side: Side) -> SortedDict:
        return self._bids if side == Side.SELL else self._asks
    
    @property
    def l1_quote(self) -> market_data.L1Quote:
        bid, ask = None, None
        if len(self._bids) != 0:
            px, level = self._bids.peekitem(0)
            bid = (px, level.agg_qty)
        if len(self._asks) != 0:
            px, level = self._asks.peekitem(0)
            ask = (px, level.agg_qty)

        return market_data.L1Quote(bid=bid, ask=ask)
    
    @property
    def l2_snapshot(self) -> market_data.L2Snapshot:
        return market_data.L2Snapshot(
            bids=[(px, level.agg_qty) for px, level in self._bids.items()],
            asks=[(px, level.agg_qty) for px, level in self._asks.items()],
        )

    def new(self, order: Order) -> None:
        bids_updates, asks_updates = [], []
        inital_l1_quote = self.l1_quote

        levels = self._opp_side(order.side)
        while order.unfilled_qty > 0 and len(levels) > 0:
            px, level = levels.peekitem(0)
            if not order.can_match(px):
                break
            level.match(order)

            if level.agg_qty == 0:
                del levels[px]

            (asks_updates if order.is_buy else bids_updates).append(
                (px, level.agg_qty)
            )

        if not order.is_filled and order.order_type == OrderType.LIMIT:
            levels = self._same_side(order.side)
            if levels.get(order.limit_px) is None:
                levels[order.limit_px] = PriceLevel(
                    mq_client=self._mq_client,
                    side=order.side, 
                    px=order.limit_px
                )
            level = levels[order.limit_px]
            level.add_resting_order(order)

            (bids_updates if order.is_buy else asks_updates).append(
                (level.px, level.agg_qty)
            )
        
        curr_l1_quote = self.l1_quote
        if curr_l1_quote.bid != inital_l1_quote.bid or curr_l1_quote.ask != inital_l1_quote.ask:
            print(curr_l1_quote)
            self._mq_client.publish(curr_l1_quote)
        l2_update = market_data.L2Update(
            bids=bids_updates,
            asks=asks_updates,
        )
        self._mq_client.publish(l2_update)

    def cancel(self, order: Order) -> None:
        levels = self._same_side(order.side)
        levels[order.limit_px].cancel(order)
        order.cancel()
    
    def print(self) -> None:
        s = "=======================\n"
        s += "\n".join(str(level) for level in reversed(self._asks.values()))
        s += "\n- - - - - - - - - - - -\n"
        s += "\n".join(str(level) for level in self._bids.values())
        s += "\n======================="
        print(s)