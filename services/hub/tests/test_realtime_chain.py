"""Phase 5 [SIM]: commands and state over a managed-broker stand-in, polling as fallback."""

import asyncio
import json
import time

import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqtt_publish

from test_integration import Stack, run



class MqttRealtime:
    """Backend realtime double: publishes like EMQX's HTTP API would, via the test broker."""

    enabled = True

    def __init__(self, broker):
        self.b = broker

    def publish(self, topic, payload, qos=1, retain=False):
        from app.services.realtime import RealtimeError
        try:
            mqtt_publish.single(topic, json.dumps(payload), qos=qos, retain=retain,
                                hostname=self.b["host"], port=self.b["port"],
                                auth={"username": "backend", "password": "backend-pw"})
        except OSError as exc:
            raise RealtimeError(str(exc))

    def set_read_only_user(self, username, password, topics):
        return None


def cloud_settings(cb):
    return dict(cloud_mqtt_host=cb["host"], cloud_mqtt_port=cb["port"], cloud_mqtt_tls=False,
                cloud_mqtt_username="hub", cloud_mqtt_password="hub-pw")


def test_command_arrives_via_broker_when_polling_is_slow(broker, cloud_broker, tmp_path):
    # Polling every 30 s: only the broker can make this fast.
    st = Stack(broker, tmp_path, realtime=MqttRealtime(cloud_broker), poll_interval_s=30,
               **cloud_settings(cloud_broker))

    async def scenario(st):
        await st.wait(st.gateway.cloud_connected.is_set, "hub connected to cloud broker")
        await asyncio.sleep(0.3)
        t0 = time.monotonic()
        r = await st.send("garden_lights", "switch", "turn_on")
        cid = r.json()["data"]["id"]
        c = await st.wait_status(cid, {"confirmed", "failed"}, timeout=5)
        elapsed = time.monotonic() - t0
        assert c["status"] == "confirmed"
        assert elapsed < 2.0, f"took {elapsed:.2f}s"
        assert any(e["detail"] == "delivered via realtime broker" for e in c["events"])
        assert len(st.sims["garden_lights"].commands_seen) == 1
    run(st, scenario)


def test_state_reaches_app_subscriber_under_2s(broker, cloud_broker, tmp_path):
    st = Stack(broker, tmp_path, realtime=MqttRealtime(cloud_broker),
               **cloud_settings(cloud_broker))
    got = []
    app = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    app.username_pw_set("app", "app-pw")
    app.on_message = lambda c, u, m: got.append((time.monotonic(), m.topic, json.loads(m.payload)))

    async def scenario(st):
        await st.wait(st.gateway.cloud_connected.is_set, "hub connected to cloud broker")
        app.connect(cloud_broker["host"], cloud_broker["port"])
        app.loop_start()
        app.subscribe(f"sh/v1/{st.home_id}/#", qos=1)
        await asyncio.sleep(0.5)
        got.clear()
        t0 = time.monotonic()
        await st.send("garden_lights", "switch", "turn_off")
        light_id = st.ids["garden_lights"]

        def seen_off():
            for t, topic, msg in got:
                if topic == f"sh/v1/{st.home_id}/dev/{light_id}/state" and \
                        msg["states"].get("switch", {}).get("on", {}).get("value") is False:
                    return t
            return None
        t_seen = await st.wait(seen_off, "state on cloud broker", timeout=5)
        assert t_seen - t0 < 2.0, f"state took {t_seen - t0:.2f}s"
        msg = next(m for _, tp, m in got if tp.endswith(f"{light_id}/state"))
        on = msg["states"]["switch"]["on"]
        assert on["source"] == "reported" and on["quality"] == "good"
        # No telemetry/video ever goes to the cloud broker.
        assert all("/telemetry" not in tp for _, tp, _ in got)
        app.loop_stop()
    run(st, scenario)


def test_broker_down_everything_still_works_by_polling(broker, cloud_broker, tmp_path):
    st = Stack(broker, tmp_path, realtime=MqttRealtime(cloud_broker),
               **cloud_settings(cloud_broker))

    async def scenario(st):
        await st.wait(st.gateway.cloud_connected.is_set, "hub connected to cloud broker")
        cloud_broker.stop()
        await st.wait(lambda: not st.gateway.cloud_connected.is_set(), "cloud link lost")
        r = await st.send("garden_lights", "switch", "turn_on")
        assert r.status_code == 201
        c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"})
        assert c["status"] == "confirmed"
        assert any("polling will deliver" in (e["detail"] or "") for e in c["events"])
    run(st, scenario)


def test_same_command_from_both_paths_runs_once(broker, cloud_broker, tmp_path):
    # Fast polling AND broker: both deliver every command.
    st = Stack(broker, tmp_path, realtime=MqttRealtime(cloud_broker), poll_interval_s=0.1,
               **cloud_settings(cloud_broker))

    async def scenario(st):
        await st.wait(st.gateway.cloud_connected.is_set, "hub connected to cloud broker")
        ids = []
        for action in ("turn_on", "turn_off", "turn_on"):
            r = await st.send("garden_lights", "switch", action)
            ids.append(r.json()["data"]["id"])
            await st.wait_status(ids[-1], {"confirmed", "failed", "rejected"})
        for cid in ids:
            c = st.command(cid)
            assert c["status"] == "confirmed"
            assert not any(e["status"] == "rejected" for e in c["events"])
        seen = [m["command_id"] for m in st.sims["garden_lights"].commands_seen]
        assert sorted(seen) == sorted(ids)
    run(st, scenario)


def test_hub_restart_without_internet_uses_cached_config(broker, tmp_path):
    st = Stack(broker, tmp_path)

    async def scenario(st):
        assert st.gateway.devices  # loaded from backend
        from gateway.core import Gateway
        st.transport.down = True
        gw2 = Gateway(st.gw_settings, backend=st.gateway.backend)
        assert set(gw2.devices) == set(st.gateway.devices)
        assert gw2.home_id == str(st.home_id)
        gw2.store.close()
    run(st, scenario)

