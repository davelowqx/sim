from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from commons import Side, OrderType

if TYPE_CHECKING:
    from messages import NewOrder

class OrderStatus(Enum):
    LIVE = "LIVE"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    order_id: str | None
    client_id: str
    order_type: OrderType
    side: Side
    limit_price: Decimal | None
    qty: int
    filled_qty: int = 0
    status: OrderStatus = OrderStatus.LIVE

    next_order: Order | None = None
    prev_order: Order | None = None

    @classmethod
    def from_new_order_request(cls, req: NewOrder) -> Order:
        return Order(
            order_id=None,
            client_id=req.client_id, 
            order_type=req.order_type,
            side=req.side,
            limit_price=req.limit_price,
            qty=req.qty
        )

    @property
    def is_live(self) -> bool:
        return self.status in {OrderStatus.LIVE, OrderStatus.PARTIALLY_FILLED}

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def unfilled_qty(self) -> int:
        return self.qty - self.filled_qty
    
    def can_match(self, px: Decimal) -> bool:
        if self.order_type == OrderType.MARKET:
            return True
        
        if self.side == Side.BUY and self.limit_price > px:
            return True

        if self.side == Side.SELL and self.limit_price < px:
            return True
        
        return False
    
    def cancel(self) -> None:
        assert self.is_live
        self.status = OrderStatus.CANCELLED

    def fill(self, qty: Decimal) -> None:
        assert self.is_live
        self.filled_qty += qty
        if self.filled_qty == self.qty:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def __str__(self) -> str:
        return f"[{self.order_id}] {self.order_type.value} {self.side.value} {self.filled_qty}/{self.qty} : {self.status}"
