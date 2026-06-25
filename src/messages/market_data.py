from dataclasses import dataclass
from decimal import Decimal

from .message import Message
from commons import Side

@dataclass(frozen=True)
class L1Quote(Message):
    bid: tuple[int, int] | None
    ask: tuple[int, int] | None

    @property
    def midprice(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None

        return (self.bid[0] + self.ask[0]) / 2

    def __str__(self) -> str:
        return f"[{self.ts}] bid=${self.bid[0]} x{self.bid[1]} ask=${self.ask[0]} x{self.ask[1]}"

@dataclass(frozen=True)
class L2Snapshot(Message):
    bids: list[tuple[int, int]]
    asks: list[tuple[int, int]]

@dataclass(frozen=True)
class L2Update(Message):
    bids: list[tuple[int, int]]
    asks: list[tuple[int, int]]

@dataclass(frozen=True)
class Trade(Message):
    side: Side
    px: int
    qty: int