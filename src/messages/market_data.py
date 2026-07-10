from dataclasses import dataclass
from decimal import Decimal

from commons import Side
from .message import Message

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
        bid_str = f"${self.bid_px}x{self.bid_qty}" if self.bid else "-"
        ask_str = f"${self.ask_px}x{self.ask_qty}" if self.ask else "-"
        return f"L1Quote: [{self.ts.time()}] bid={bid_str} ask={ask_str}"

@dataclass(kw_only=True, frozen=True)
class L2Snapshot(Message):
    bids: list[PriceQty]
    asks: list[PriceQty]

    def __str__(self) -> str:
        bids = ",".join([f"${px}x{qty}" for px, qty in self.bids])
        asks = ",".join([f"${px}x{qty}" for px, qty in self.asks])
        return f"[{self.ts.time()}] bids=[{bids}] asks=[{asks}]"

@dataclass(kw_only=True, frozen=True)
class L2Update(Message):
    bids: list[PriceQty]
    asks: list[PriceQty]

    def __str__(self) -> str:
        bids = ",".join([f"${px}x{qty}" for px, qty in self.bids])
        asks = ",".join([f"${px}x{qty}" for px, qty in self.asks])
        return f"L2Update: [{self.ts.time()}] bids=[{bids}] asks=[{asks}]"

@dataclass(kw_only=True, frozen=True)
class Trade(Message):
    px: Decimal
    qty: int
    aggressor_side: Side

    def __str__(self) -> str:
        return f"Trade: ${self.px}x{self.qty}"