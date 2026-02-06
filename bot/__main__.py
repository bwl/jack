from __future__ import annotations

import logging

from dotenv import load_dotenv

from .config import Config
from .telegram import JackBot


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    )
    config = Config.from_env()
    bot = JackBot(config)
    bot.run()


if __name__ == "__main__":
    main()
