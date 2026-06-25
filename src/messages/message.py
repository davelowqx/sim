from datetime import datetime
from dataclasses import dataclass

@dataclass(frozen=True)
class Message:
    ts: datetime