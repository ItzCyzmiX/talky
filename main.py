import asyncio
import logging
import os
import sys
import threading

from bot.bot import run_bot

logging.basicConfig(level=logging.INFO)


def restart_bot():
    while True:
        _ = input()
        if _.strip().lower() == "r":
            print("Restarting...")
            os.execv(sys.executable, ["python"] + sys.argv)


threading.Thread(target=restart_bot, daemon=True).start()

asyncio.run(run_bot())
