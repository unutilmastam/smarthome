"""Tuya bridge (ADR 0016) [SIM]: DPS mapping, confirmation only from the device's own
answer, breaker safety, IR learn/press. Real devices: docs/hardware/tests/tuya.md."""

import asyncio

from gateway.expectations import expectation
from gateway.tuya import TuyaBridge, TuyaConfig, decode_phase, dps_to_states
from simulator.tuya_fake import FakeTuya, phase_raw


def device(key, profile, **conn):
    return {"key": key, "adapter": "tuya", "enabled": True, "secret": "fakefakefakefake",
            "connection": {"profile": profile, "device_id": "bf" + key, "ip": "192.168.1.50",
                           "version": "3.4", "poll_s": 0.05, **conn},
            "capabilities": {}}


class Harness:
    def __init__(self, fakes):
        self.fakes = fakes
        self.states = {}
        self.avail = {}
        self.kv = {}
        self.bridge = TuyaBridge(publish=self.publish, availability=self.set_avail,
                                 store_get=self.kv.get, store_put=self.kv.__setitem__,
                                 client_factory=lambda cfg: self.fakes[cfg.key])

    def publish(self, key, msg):
        assert msg["source"] == "reported"
        self.states[key] = msg["states"]

    def set_avail(self, key, status):
        self.avail[key] = status


async def settle(cond, timeout=3.0):
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while loop.time() < end:
        if cond():
            return True
        await asyncio.sleep(0.02)
    return False


def test_profiles_report_only_what_the_device_sent():
    assert dps_to_states("switch", {"switch": 1}, {"1": True}) == {"switch": {"on": True}}
    assert dps_to_states("switch", {"switch": 1}, {"2": True}) == {}          # unknown, not "off"
    assert dps_to_states("switch", {"switch": 1}, {"1": "on"}) == {}          # wrong type: not guessed
    s = dps_to_states("plug_meter", {"switch": 1, "current_ma": 18, "power_w10": 19, "voltage_v10": 20,
                                     "energy_wh": 17}, {"1": True, "19": 1205, "20": 2301})
    assert s == {"switch": {"on": True}, "power_meter": {"power": 120.5, "voltage": 230.1}}
    assert decode_phase(phase_raw(229.8, 1.25, 280)) == {"voltage": 229.8, "current": 1.25, "power": 280.0}
    assert decode_phase("@@@") is None


def test_breaker_tripped_needs_a_fault_and_open_contacts():
    m = {"breaker": 16, "fault": 9}
    assert dps_to_states("breaker", m, {"16": False, "9": 1})["breaker"] == {"closed": False, "tripped": True}
    assert dps_to_states("breaker", m, {"16": True, "9": 1})["breaker"] == {"closed": True, "tripped": False}
    assert dps_to_states("breaker", m, {"16": False})["breaker"] == {"closed": False}  # no fault DP: unknown
    assert "tripped" not in dps_to_states("breaker", {"breaker": 16}, {"16": False, "9": 1})["breaker"]


def test_config_needs_ip_id_and_key_and_takes_dps_overrides():
    assert TuyaConfig.from_device({**device("r", "switch"), "secret": None}) is None
    assert TuyaConfig.from_device({**device("r", "nope")}) is None
    cfg = TuyaConfig.from_device(device("b", "breaker", dps={"breaker": 1, "energy_kwh100": 17}))
    assert cfg.dps["breaker"] == 1 and cfg.dps["energy_kwh100"] == 17 and cfg.version == 3.4


def test_relay_confirmed_by_its_own_answer_and_offline_is_offline():
    async def go():
        h = Harness({"rele": FakeTuya("switch")})
        h.bridge.sync({"rele": device("rele", "switch")})
        assert await settle(lambda: h.states.get("rele") == {"switch": {"on": False}})
        assert h.avail["rele"] == "online"
        check = expectation("switch", "turn_on", {})
        assert await h.bridge.command("rele", "switch", "turn_on", {}) == {"status": "acked"}
        assert await settle(lambda: check(h.states["rele"]["switch"]) is True)
        h.fakes["rele"].online = False
        assert await settle(lambda: h.avail["rele"] == "offline")
        res = await h.bridge.command("rele", "switch", "turn_off", {})
        assert res["status"] == "failed"
        await h.bridge.stop()
    asyncio.run(go())


def test_device_that_ignores_the_write_is_never_confirmed():
    async def go():
        h = Harness({"rele": FakeTuya("switch", ignore_writes=True)})
        h.bridge.sync({"rele": device("rele", "switch")})
        assert await settle(lambda: "rele" in h.states)
        assert (await h.bridge.command("rele", "switch", "turn_on", {}))["status"] == "acked"
        await asyncio.sleep(0.3)
        assert expectation("switch", "turn_on", {})(h.states["rele"]["switch"]) is False
        await h.bridge.stop()
    asyncio.run(go())


def test_tripped_breaker_is_not_closed_remotely():
    async def go():
        fake = FakeTuya("breaker")
        h = Harness({"avt": fake})
        h.bridge.sync({"avt": device("avt", "breaker")})
        assert await settle(lambda: h.states.get("avt", {}).get("power_meter", {}).get("voltage") == 229.8)
        assert h.states["avt"]["power_meter"]["energy"] == 123.45
        fake.trip()
        assert await settle(lambda: h.states["avt"]["breaker"] == {"closed": False, "tripped": True})
        res = await h.bridge.command("avt", "breaker", "close", {})
        assert res["status"] == "rejected" and res["reason"] == "safety_rule"
        assert fake.dps["16"] is False
        fake.reset_on_site()
        assert await settle(lambda: h.states["avt"]["breaker"]["tripped"] is False)
        assert (await h.bridge.command("avt", "breaker", "close", {}))["status"] == "acked"
        assert await settle(lambda: h.states["avt"]["breaker"]["closed"] is True)
        await h.bridge.stop()
    asyncio.run(go())


def test_ir_learn_is_confirmed_press_is_only_sent():
    async def go():
        fake = FakeTuya("ir")
        h = Harness({"pult": fake})
        h.kv["ir:pult"] = {"power": "AAAA"}   # learned earlier, kept on the hub
        h.bridge.sync({"pult": device("pult", "ir")})
        assert await settle(lambda: h.states.get("pult") == {"remote": {"buttons": ["power"]}})
        res = await h.bridge.command("pult", "remote", "press", {"button": "vol_up"})
        assert res["status"] == "rejected"                    # not learned: nothing is sent
        assert (await h.bridge.command("pult", "remote", "press", {"button": "power"})) == {"status": "acked"}
        assert fake.sent == ["AAAA"]
        learned = expectation("remote", "learn", {"button": "vol_up"})
        assert (await h.bridge.command("pult", "remote", "learn", {"button": "vol_up"}))["status"] == "acked"
        assert learned(h.states["pult"]["remote"]) is False
        fake.next_ir = "BBBB"                                  # the owner presses the original remote
        assert await settle(lambda: learned(h.states["pult"]["remote"]) is True)
        assert h.kv["ir:pult"] == {"power": "AAAA", "vol_up": "BBBB"}
        await h.bridge.command("pult", "remote", "forget", {"button": "power"})
        assert await settle(lambda: h.states["pult"]["remote"]["buttons"] == ["vol_up"])
        await h.bridge.stop()
    asyncio.run(go())


def test_learning_nothing_does_not_add_a_button():
    async def go():
        h = Harness({"pult": FakeTuya("ir")})
        h.bridge.sync({"pult": device("pult", "ir")})
        assert await settle(lambda: "pult" in h.states)
        await h.bridge.command("pult", "remote", "learn", {"button": "ok"})
        await asyncio.sleep(2.3)                              # the fake waits 2 s, nobody pressed
        assert h.states["pult"]["remote"]["buttons"] == []
        await h.bridge.stop()
    asyncio.run(go())


def test_config_change_restarts_and_removed_device_stops():
    async def go():
        h = Harness({"rele": FakeTuya("switch")})
        h.bridge.sync({"rele": device("rele", "switch")})
        first = h.bridge.devices["rele"]
        h.bridge.sync({"rele": device("rele", "switch", ip="192.168.1.51")})
        assert h.bridge.devices["rele"] is not first
        h.bridge.sync({})
        assert not h.bridge.has("rele")
        await h.bridge.stop()
    asyncio.run(go())
