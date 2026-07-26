import asyncio
import logging
import os
import sys
import threading

from bot.bot import run_bot

logging.basicConfig(level=logging.INFO)


def restart_bot():
    while True:
        cmd = input()
        match cmd.strip().lower():
            case "r":
                logging.info("Restarting...")
                os.execv(sys.executable, ["python"] + sys.argv)
            case _:
                pass


threading.Thread(target=restart_bot, daemon=True).start()

runner = asyncio.run(run_bot())
