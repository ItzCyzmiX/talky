import asyncio
from bot.bot import run_bot
import logging

logging.basicConfig(level=logging.INFO)

asyncio.run(run_bot())
