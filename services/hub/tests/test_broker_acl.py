"""The real broker config: anonymous refused, devices confined to their own topics."""

import threading
import time

import paho.mqtt.client as mqtt

from conftest import GW_PASSWORD, SIM_PASSWORD


def connect(broker, user=None, password=None):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    result = {}
    ready = threading.Event()

    def on_connect(client, userdata, flags, rc, props=None):
        result["rc"] = rc
        ready.set()
    c.on_connect = on_connect
    if user:
        c.username_pw_set(user, password)
    c.connect(broker["host"], broker["port"])
    c.loop_start()
    ready.wait(5)
    return c, result.get("rc")


def collect(broker, topic):
    c, rc = connect(broker, "gateway", GW_PASSWORD)
    got = []
    c.on_message = lambda cl, u, m: got.append((m.topic, m.payload.decode()))
    c.subscribe(topic, qos=1)
    time.sleep(0.2)
    return c, got


def test_anonymous_and_bad_password_rejected(broker):
    c, rc = connect(broker)
    assert rc is not None and rc.is_failure
    c.loop_stop()
    c, rc = connect(broker, "gateway", "wrong")
    assert rc.is_failure
    c.loop_stop()


def test_device_cannot_write_other_devices_or_cmd(broker):
    gw, got = collect(broker, "home/#")
    dev, rc = connect(broker, "garden_lights", SIM_PASSWORD)
    assert not rc.is_failure
    dev.publish("home/garden_lights/state", '{"ok":1}', qos=1).wait_for_publish(2)
    dev.publish("home/front_gate/cmd", '{"evil":1}', qos=1).wait_for_publish(2)
    dev.publish("home/front_gate/state", '{"evil":1}', qos=1).wait_for_publish(2)
    dev.publish("home/garden_lights/cmd", '{"evil":1}', qos=1).wait_for_publish(2)
    time.sleep(0.5)
    topics = [t for t, _ in got]
    assert "home/garden_lights/state" in topics
    assert "home/front_gate/cmd" not in topics
    assert "home/front_gate/state" not in topics
    assert "home/garden_lights/cmd" not in topics
    for c in (gw, dev):
        c.loop_stop()


def test_device_receives_only_its_own_cmd(broker):
    dev, _ = connect(broker, "garden_lights", SIM_PASSWORD)
    got = []
    dev.on_message = lambda cl, u, m: got.append(m.topic)
    dev.subscribe("home/#", qos=1)
    time.sleep(0.2)
    gw, _ = connect(broker, "gateway", GW_PASSWORD)
    gw.publish("home/garden_lights/cmd", "{}", qos=1).wait_for_publish(2)
    gw.publish("home/front_gate/cmd", "{}", qos=1).wait_for_publish(2)
    time.sleep(0.5)
    assert got == ["home/garden_lights/cmd"]
    for c in (gw, dev):
        c.loop_stop()
