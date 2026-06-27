from dataclasses import dataclass
from decimal import Decimal

from commons import OrderType, Side
from .message import Message

@dataclass(kw_only=True, frozen=True)
class Request(Message):
    request_id: str
    client_id: str

@dataclass(kw_only=True, frozen=True)
class NewOrder(Request):
    order_type: OrderType
    side: Side
    qty: int
    limit_px: Decimal | None

@dataclass(kw_only=True, frozen=True)
class CancelOrder(Request):
    order_id: str

@dataclass(kw_only=True, frozen=True)
class GetL2Snapshot(Request):
    pass