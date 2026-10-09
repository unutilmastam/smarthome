"""ADR 0015 [SIM]: smart breaker in the panel. Phone -> cloud -> hub -> breaker, confirmed
only by the breaker's own `closed`; a tripped breaker cannot be closed remotely."""

from gateway.expectations import expectation
from simulator.devices import BreakerSim
from conftest import SIM_PASSWORD
from test_integration import DEVICES, PIN, Stack, run
from test_phase11 import attr, cmd, wait_event

BREAKER = {"capabilities": {"breaker": {"panel": "Asosiy shit", "position": 1, "rating_a": 16,
                                        "curve": "C", "poles": 1, "confirm_timeout_s": 2}}}


def test_breaker_expectation_uses_its_own_contact():
    close = expectation("breaker", "close", {})
    assert close({"closed": True}) is True and close({"closed": False}) is False
    assert close({"tripped": False}) is None          # not reported yet: no guess
    assert expectation("breaker", "open", {})({"closed": False}) is True


def test_breaker_switch_trip_refuse_and_reset(broker, tmp_path):
    DEVICES["breaker_kitchen"] = BREAKER
    try:
        st = Stack(broker, tmp_path)
        sim = BreakerSim("breaker_kitchen", host=broker["host"], port=broker["port"],
                         password=SIM_PASSWORD)
        st.sims["breaker_kitchen"] = sim

        async def scenario(st):
            await st.wait(lambda: attr(st, "breaker_kitchen", "breaker", "closed")["quality"] == "good",
                          "initial breaker state")
            # High risk: without the PIN the cloud refuses.
            r = await st.send("breaker_kitchen", "breaker", "open")
            assert r.status_code in (400, 403, 422), r.text
            c = await cmd(st, "breaker_kitchen", "breaker", "open", confirm_pin=PIN)
            assert c["status"] == "confirmed"
            await st.wait(lambda: attr(st, "breaker_kitchen", "breaker", "closed")["value"] is False,
                          "open state reported to the cloud")
            c = await cmd(st, "breaker_kitchen", "breaker", "close", confirm_pin=PIN)
            assert c["status"] == "confirmed"

            # Overcurrent: the breaker trips by itself.
            sim.trip()
            ev = await wait_event(st, "breaker.tripped")
            assert ev["severity"] == "critical"
            await st.wait(lambda: attr(st, "breaker_kitchen", "breaker", "tripped")["value"] is True,
                          "tripped reported")
            assert attr(st, "breaker_kitchen", "breaker", "closed")["value"] is False   # same report
            # Remote close is refused by the firmware until someone resets it on site.
            c = await cmd(st, "breaker_kitchen", "breaker", "close", confirm_pin=PIN)
            assert (c["status"], c["reason"]) == ("rejected", "safety_rule")
            await wait_event(st, "breaker.close_refused")
            sim.reset_on_site()
            await st.wait(lambda: attr(st, "breaker_kitchen", "breaker", "tripped")["value"] is False,
                          "reset reported")
            c = await cmd(st, "breaker_kitchen", "breaker", "close", confirm_pin=PIN)
            assert c["status"] == "confirmed"

            # Position contact broken: the command is never shown as done.
            sim.set_fault("aux_broken")
            c = await cmd(st, "breaker_kitchen", "breaker", "open", confirm_pin=PIN, timeout=10)
            assert (c["status"], c["reason"]) == ("failed", "no_feedback")
        run(st, scenario)
    finally:
        DEVICES.pop("breaker_kitchen", None)
