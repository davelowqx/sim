from dataclasses import dataclass, field
from datetime import datetime

@dataclass(kw_only=True, frozen=True)
class Message:
    ts: datetime = field(default_factory=datetime.now)
