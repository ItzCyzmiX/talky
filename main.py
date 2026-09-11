import asyncio
import logging
import os
import sys
import threading

from bot.bot import run_bot

logging.basicConfig(level=logging.INFO)

asyncio.run(run_bot())