from dataclasses import dataclass
from decimal import Decimal
import logging
from sortedcontainers import SortedDict

from commons import Side, OrderType
from messages import market_data, events

from .order import Order
from .event_bus import EventBus

@dataclass
class PriceLevel:
    def __init__(self, event_bus: EventBus, side: Side, px: Decimal):
        self._event_bus = event_bus
        self.side = side
        self.px = px
        self.agg_qty = 0
        self._first_order : Order | None = None
        self._last_order : Order | None = None
    
    def match(self, incoming_order: Order) -> list[str]:
        terminal_order_ids = []
        while incoming_order.unfilled_qty > 0 and self._first_order is not None:
            if incoming_order.client_id == self._first_order.client_id:
                incoming_order.cancel()
                self._event_bus.send(
                    incoming_order.client_id,
                    events.OrderCancelled(
                        client_id=incoming_order.client_id,
                        order_id=incoming_order.order_id,
                    )
                )
                return terminal_order_ids
            fill_qty = min(self._first_order.unfilled_qty, incoming_order.unfilled_qty)
            self.agg_qty -= fill_qty
            incoming_order.fill(fill_qty)
            self._first_order.fill(fill_qty)
            self._event_bus.send(
                incoming_order.client_id,
                events.OrderExecuted(
                    client_id=incoming_order.client_id,
                    order_id=incoming_order.order_id,
                    px=self.px,
                    qty=fill_qty
                )
            )
            self._event_bus.send(
                self._first_order.client_id,
                events.OrderExecuted(
                    client_id=self._first_order.client_id,
                    order_id=self._first_order.order_id,
                    px=self.px,
                    qty=fill_qty
                )
            )
            self._event_bus.publish(
                market_data.Trade(
                    px=self.px,
                    qty=fill_qty
                )
            )

            if self._first_order.is_filled:
                terminal_order_ids.append(self._first_order.order_id)
                self._first_order = self._first_order.next_order
        
        return terminal_order_ids
        
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
        self._event_bus.publish(l2_update)
    
    def __str__(self) -> str:
        lst = []
        order = self._first_order
        while order is not None:
            lst.append(f"[{order.client_id}-{order.order_id}]:{order.unfilled_qty}")
            order = order.next_order
        return f"${self.px}x{self.agg_qty}: [{', '.join(lst)}]"

class MatchingEngine:
    def __init__(self, event_bus: EventBus):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._event_bus = event_bus
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

    def new(self, order: Order) -> list[str]:
        self._logger.info("matching_engine.new() %s", order)
        terminal_order_ids = []
        bids_updates, asks_updates = [], []
        inital_l1_quote = self.l1_quote

        levels = self._opp_side(order.side)
        while order.is_live and order.unfilled_qty > 0 and len(levels) > 0:
            px, level = levels.peekitem(0)
            if not order.can_match(px):
                break
            terminal_order_ids.extend(level.match(order))

            if level.agg_qty == 0:
                del levels[px]

            (asks_updates if order.is_buy else bids_updates).append(
                (px, level.agg_qty)
            )

        if order.order_type == OrderType.LIMIT and not order.is_terminal:
            levels = self._same_side(order.side)
            if levels.get(order.limit_px) is None:
                levels[order.limit_px] = PriceLevel(
                    event_bus=self._event_bus,
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
            self._event_bus.publish(curr_l1_quote)
        l2_update = market_data.L2Update(
            bids=bids_updates,
            asks=asks_updates,
        )
        self._event_bus.publish(l2_update)

        return terminal_order_ids

    def cancel(self, order: Order) -> None:
        self._logger.info("matching_engine.cancel() %s", order)
        levels = self._same_side(order.side)
        level: PriceLevel = levels[order.limit_px]
        level.cancel(order)
        if level.agg_qty == 0:
            del levels[order.limit_px]
        order.cancel()

        msg = events.OrderCancelled(
            client_id=order.client_id, 
            order_id=order.order_id
        )
        self._event_bus.send(order.client_id, msg)

    
    def print(self) -> None:
        s = "=======================\n"
        s += "\n".join(str(level) for level in reversed(self._asks.values()))
        s += "\n- - - - - - - - - - - -\n"
        s += "\n".join(str(level) for level in self._bids.values())
        s += "\n=======================\n"
        print(s)