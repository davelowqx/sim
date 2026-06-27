from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from commons import Side, OrderType
from messages import events

class OrderStatus(Enum):
    PENDING_LIVE = "PENDING_LIVE"
    LIVE = "LIVE"
    PENDING_CANCEL = "PENDING_CANCEL"
    CANCELLED = "CANCELLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"

@dataclass(kw_only=True)
class Order:
    request_id: str
    order_id: str | None = None
    order_type: OrderType
    side: Side
    limit_px: Decimal | None
    qty: int
    filled_qty: int = 0
    status: OrderStatus = OrderStatus.PENDING_LIVE

    @property
    def is_pending(self) -> bool:
        return self.status in {OrderStatus.PENDING_LIVE, OrderStatus.PENDING_CANCEL}

    @property
    def is_terminal(self) -> bool:
        return self.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}

    @property
    def unfilled_qty(self) -> int:
        return self.qty - self.filled_qty

    @property
    def is_buy(self) -> bool:
        return self.side == Side.BUY
    
    def live(self, ev: events.OrderAccepted) -> None:
        assert ev.request_id == self.request_id
        assert self.status == OrderStatus.PENDING_LIVE
        self.status = OrderStatus.LIVE
        self.order_id = ev.order_id
    
    def reject(self, ev: events.OrderRejected) -> None:
        assert ev.request_id == self.request_id
        assert self.status == OrderStatus.PENDING_LIVE
        self.status = OrderStatus.REJECTED
    
    def fill(self, ev: events.OrderExecuted) -> None:
        assert self.status == OrderStatus.LIVE
        assert ev.order_id == self.order_id
        self.filled_qty += ev.qty
        if self.filled_qty == self.qty:
            self.status = OrderStatus.FILLED

    def cancel(self, ev: events.OrderCancelled) -> None:
        assert ev.order_id == self.order_id
        assert self.status == OrderStatus.LIVE
        self.status = OrderStatus.CANCELLED

    def __str__(self) -> str:
        return f"[{self.order_id}] {self.order_type.value} {self.side.value} {self.filled_qty}/{self.qty} : {self.status}"


