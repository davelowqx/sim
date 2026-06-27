from enum import Enum
from typing import Protocol
from messages import Message

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class RejectReason(Enum):
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    ILLEGAL_OP= "ILLEGAL_OP"
    NOT_FOUND = "NOT_FOUND"

class MQTopic(Enum):
    ORDER_ENTRY = "order.entry"
    MD_L1 = "md.l1"
    MD_L2 = "md.l2"
    MD_TRADE = "md.trade"

class MQClient(Protocol):
    def subscribe(self, client_id: str, callback) -> None:
        ...

    def send(self, client_id: str, message: Message) -> None:
        ...

    def publish(self, message: Message) -> None:
        ...
