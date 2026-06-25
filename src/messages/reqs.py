from dataclasses import dataclass
from decimal import Decimal

from commons import OrderType, Side
from .message import Message

@dataclass(frozen=True)
class Request(Message):
    client_id: str
    request_id: str

@dataclass(frozen=True)
class NewOrder(Request):
    order_type: OrderType
    side: Side
    limit_price: Decimal | None = None
    qty: int

@dataclass(frozen=True)
class CancelOrder(Request):
    order_id: str

@dataclass(frozen=True)
class GetL2Snapshot(Request):
    pass