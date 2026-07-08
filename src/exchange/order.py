from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from commons import Side, OrderType
from messages import reqs, events

class OrderStatus(Enum):
    LIVE = "LIVE"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass(kw_only=True)
class Order:
    order_id: str
    client_id: str
    order_type: OrderType
    side: Side
    limit_px: Decimal | None
    qty: int
    filled_qty: int = 0
    status: OrderStatus = OrderStatus.LIVE

    next_order: "Order | None" = None
    prev_order: "Order | None" = None

    @classmethod
    def from_new_order_request(cls, req: reqs.NewOrder, order_id: str) -> "Order":
        return Order(
            order_id=order_id,
            client_id=req.client_id, 
            order_type=req.order_type,
            side=req.side,
            limit_px=req.limit_px,
            qty=req.qty
        )

    @property
    def is_live(self) -> bool:
        return self.status == OrderStatus.LIVE

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_terminal(self) -> bool:
        return self.status in { OrderStatus.FILLED, OrderStatus.CANCELLED }
    
    @property
    def unfilled_qty(self) -> int:
        return self.qty - self.filled_qty
    
    @property
    def is_buy(self) -> bool:
        return self.side == Side.BUY

    @property
    def is_sell(self) -> bool:
        return self.side == Side.SELL
    
    def can_match(self, px: Decimal) -> bool:
        if self.order_type == OrderType.MARKET:
            return True
        
        if self.is_buy and self.limit_px > px:
            return True

        if self.is_sell and self.limit_px < px:
            return True
        
        return False
    
    def fill(self, qty: Decimal) -> events.OrderExecuted:
        assert self.is_live
        self.filled_qty += qty
        if self.filled_qty == self.qty:
            self.status = OrderStatus.FILLED

    def cancel(self) -> events.OrderCancelled:
        assert self.is_live
        self.next_order = None
        self.prev_order = None
        self.status = OrderStatus.CANCELLED
    
    def __str__(self) -> str:
        return f"[{self.client_id}-{self.order_id}] {self.side.value}{f' ${self.limit_px}' if self.limit_px else ''} {self.filled_qty}/{self.qty} : {self.status.value}"
