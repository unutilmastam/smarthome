"""Outbox flushing must never send the same item twice at the same time (CI hub 3.10:
the flush loop and a direct flush_once() raced and posted one telemetry batch twice)."""

import asyncio

from conftest import CONTRACTS
from gateway.config import GatewaySettings
from gateway.core import Gateway
from gateway.store import Store


class SlowBackend:
    def __init__(self):
        self.telemetry_calls = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def telemetry(self, batch):
        self.telemetry_calls += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.05)
        self.in_flight -= 1
        return {"accepted": len(batch["items"])}

    async def acks(self, acks):
        return {}

    async def report(self, r):
        return {}

    async def events(self, e):
        return {}


def test_concurrent_flushes_send_each_item_once(tmp_path):
    async def main():
        settings = GatewaySettings(_env_file=None, backend_url="http://x", hub_token="hub_test",
                                   signing_key_hex="00" * 32, contracts_dir=CONTRACTS,
                                   db_path=str(tmp_path / "hub.sqlite3"))
        backend = SlowBackend()
        gw = Gateway(settings, backend=backend, store=Store(str(tmp_path / "hub.sqlite3")))
        gw.store.enqueue("telemetry", {"schema": 1, "items": [{"device_key": "m"}]})
        results = await asyncio.gather(gw.flush_once(), gw.flush_once(), gw.flush_once())
        assert all(results)
        assert backend.telemetry_calls == 1
        assert backend.max_in_flight == 1
        assert gw.store.outbox_size() == 0
    asyncio.run(main())
