from dataclasses import dataclass
from decimal import Decimal

from .message import Message
from commons import Side

type PriceQty = tuple[Decimal, int]

@dataclass(kw_only=True, frozen=True)
class L1Quote(Message):
    bid: PriceQty | None
    ask: PriceQty | None

    @property
    def bid_px(self) -> Decimal | None:
        if not self.bid:
            return None
        return self.bid[0]

    @property
    def bid_qty(self) -> int | None:
        if not self.bid:
            return None
        return self.bid[1]

    @property
    def ask_px(self) -> Decimal | None:
        if not self.ask:
            return None
        return self.ask[0]

    @property
    def ask_qty(self) -> int | None:
        if not self.ask:
            return None
        return self.ask[1]

    @property
    def mid_px(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None

        return (self.bid_px + self.ask_px) / 2

    def __str__(self) -> str:
        return f"[{self.ts}] bid=${self.bid_px} x{self.bid_qty} ask=${self.ask_px} x{self.ask_qty}"

@dataclass(kw_only=True, frozen=True)
class L2Snapshot(Message):
    bids: list[PriceQty]
    asks: list[PriceQty]

@dataclass(kw_only=True, frozen=True)
class L2Update(Message):
    bids: list[PriceQty]
    asks: list[PriceQty]

@dataclass(kw_only=True, frozen=True)
class Trade(Message):
    px: int
    qty: int