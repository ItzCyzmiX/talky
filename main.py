import asyncio
import logging

from bot.bot import run_bot

logging.basicConfig(level=logging.INFO)

asyncio.run(run_bot())