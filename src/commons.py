from enum import Enum

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class RejectReason(Enum):
    ILLEGAL_OP = "ILLEGAL_OP"
    NOT_FOUND = "NOT_FOUND"
