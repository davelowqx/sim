from dataclasses import dataclass
from decimal import Decimal

from .message import Message

@dataclass(kw_only=True, frozen=True)
class Event(Message):
    client_id: str

@dataclass(kw_only=True, frozen=True)
class OrderAccepted(Event):
    request_id: str
    order_id: str

    def __str__(self) -> str:
        return f"OrderAccepted: {self.order_id}"

@dataclass(kw_only=True, frozen=True)
class OrderCancelled(Event):
    order_id: str

    def __str__(self) -> str:
        return f"OrderCancelled: {self.order_id}"

@dataclass(kw_only=True, frozen=True)
class OrderExecuted(Event):
    order_id: str
    px: Decimal
    qty: int

    def __str__(self) -> str:
        return f"OrderExecuted: {self.order_id} ${self.px}x{self.qty}"

@dataclass(kw_only=True, frozen=True)
class OrderRejected(Event):
    request_id: str

    def __str__(self) -> str:
        return f"OrderRejected: {self.request_id}"

@dataclass(kw_only=True, frozen=True)
class OrderCancelRejected(Event):
    request_id: str
    order_id: str

    def __str__(self) -> str:
        return f"OrderCancelRejected: {self.order_id}"