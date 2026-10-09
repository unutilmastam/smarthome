"""Run virtual devices: python -m simulator devices.json

devices.json: [{"type": "light", "key": "garden_lights"}, ...]  (see devices.example.json)
"""

import json
import logging
import os
import signal
import sys
import threading

from simulator.devices import TYPES


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO)
    argv = argv or sys.argv[1:]
    path = argv[0] if argv else os.environ.get("SIM_DEVICES", "simulator/devices.example.json")
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    host = os.environ.get("MQTT_HOST", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    password = os.environ.get("SIM_DEVICE_PASSWORD")
    devices = []
    for d in spec:
        d = dict(d)
        cls = TYPES[d.pop("type")]
        dev = cls(host=host, port=port, password=password, **d)
        dev.start()
        devices.append(dev)
        logging.info("started %s (%s)", dev.key, cls.__name__)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    for dev in devices:
        dev.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
