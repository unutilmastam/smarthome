import asyncio
import logging

from gateway.config import GatewaySettings
from gateway.core import Gateway


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    gw = Gateway(GatewaySettings())
    asyncio.run(gw.run())


if __name__ == "__main__":
    main()
