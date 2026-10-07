"""Per-minute aggregation of numeric readings (ARCHITECTURE 6: Hub aggregates, sends 60 s).

Raw readings are kept in the hub SQLite for 7 days; only 1-minute aggregates go to
the cloud (POST /hub/telemetry:batch), through the offline outbox.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from gateway.timeutil import utcnow

RAW_RETENTION = timedelta(days=7)


@dataclass
class Bucket:
    values: List[float] = field(default_factory=list)

    def add(self, v: float) -> None:
        self.values.append(float(v))

    def to_item(self, key: str, metric: str, minute: datetime) -> dict:
        vals = self.values
        return {"device_key": key, "metric": metric,
                "ts": minute.strftime("%Y-%m-%dT%H:%M:00Z"),
                "avg": sum(vals) / len(vals), "min": min(vals), "max": max(vals),
                "last": vals[-1], "count": len(vals)}


class Aggregator:
    def __init__(self, store):
        self.store = store
        self.buckets: Dict[Tuple[str, str, datetime], Bucket] = {}

    def add(self, key: str, metric: str, value: float, ts: datetime) -> None:
        minute = ts.replace(second=0, microsecond=0)
        self.buckets.setdefault((key, metric, minute), Bucket()).add(value)
        self.store.add_raw(key, metric, ts, float(value))

    def close_minutes(self, now: Optional[datetime] = None) -> List[dict]:
        """Return aggregates for every minute that is over."""
        current = (now or utcnow()).replace(second=0, microsecond=0)
        done = [k for k in self.buckets if k[2] < current]
        items = [self.buckets.pop(k).to_item(k[0], k[1], k[2]) for k in sorted(done, key=lambda x: x[2])]
        return items
