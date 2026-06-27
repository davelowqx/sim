from dataclasses import dataclass
from decimal import Decimal

from commons import RejectReason
from .message import Message

@dataclass(kw_only=True, frozen=True)
class Event(Message):
    client_id: str

@dataclass(kw_only=True, frozen=True)
class OrderAccepted(Event):
    request_id: str
    order_id: str

@dataclass(kw_only=True, frozen=True)
class OrderCancelled(Event):
    order_id: str

@dataclass(kw_only=True, frozen=True)
class OrderExecuted(Event):
    order_id: str
    px: Decimal
    qty: int

    def __str__(self) -> str:
        return f"{self.order_id} ${self.px}x{self.qty}"

@dataclass(kw_only=True, frozen=True)
class OrderRejected(Event):
    request_id: str
    reason: RejectReason

@dataclass(kw_only=True, frozen=True)
class OrderCancelRejected(Event):
    request_id: str
    order_id: str
    reason: RejectReason