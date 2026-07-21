import os

import discord

from dotenv import load_dotenv

load_dotenv()

GUILD = discord.Object(id=int(os.getenv("GUILD_ID")))

BOTS_CATEGORY_ID = int(os.getenv("BOTS_CATEGORY_ID"))

BOT_CREATION_CHANNEL = int(os.getenv("BOT_CREATION_CHANNEL_ID"))

DESCRITPTION = """Bot to talk to ai characters!"""

DELETE_DELAY = 15

MESSAGE_HISTOY_LIMIT = 100
