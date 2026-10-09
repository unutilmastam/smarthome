import asyncio
import logging

from gateway.config import GatewaySettings
from gateway.core import Gateway


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per poll is noise
    settings = GatewaySettings()
    factory = None
    if settings.tuya_simulator:
        # [SIM] only (e2e stack, demos): fake Tuya devices instead of the LAN. Never in production.
        from simulator.tuya_fake import FakeTuya
        logging.getLogger("gateway").warning("TUYA_SIMULATOR is on: Tuya devices are simulated")
        fakes: dict = {}
        factory = lambda cfg: fakes.setdefault(cfg.key, FakeTuya(cfg.profile, auto_learn=True))  # noqa: E731
    gw = Gateway(settings, tuya_client_factory=factory)
    asyncio.run(gw.run())


if __name__ == "__main__":
    main()
