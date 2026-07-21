from datetime  import datetime
import asyncio

from discord.ext import tasks, commands

from bot.character_api import _get_openrouter_models
from bot.consts import BOTS_CATEGORY_ID
from bot.supabase import get_bots_with_ids, get_admins, get_messages, get_chat_model
from bot.utils import startup_print


class CronCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.sync_cache.start()
        self.update_openrouter_models.start()

    @tasks.loop(hours=12)
    async def update_openrouter_models(self):
        print(f"[{datetime.now()}] Fetching new openrouter models...")
        
        await self.bot.wait_until_ready()

        self.bot.openrouter_models = await _get_openrouter_models()


    @tasks.loop(hours=1)
    async def sync_cache(self):
        print(f"[{datetime.now()}] Syncing cache...")
        
        await self.bot.wait_until_ready()

        bot_category = self.bot.get_channel(BOTS_CATEGORY_ID)

        if bot_category is None:
            return

        channels = bot_category.text_channels
        channel_ids = list(map(lambda x: x.id, channels))

        await asyncio.sleep(0.3)

        db_bot_ids = await get_bots_with_ids(self.bot.supabase, channel_ids)

        for c in channels:

            if c.id not in db_bot_ids:
                await c.delete()
                continue

            admins = await get_admins(self.bot.supabase, c.id)
            messages = await get_messages(self.bot.supabase, c.id)
            gpt = await get_chat_model(self.bot.supabase, c.id)

            self.bot.running_bots[str(c.id)] = {
                "admins": admins,
                "messages": messages,
                "gpt": gpt,
            }
        await asyncio.sleep(0.3)
        startup_print(bot=self.bot)
    
    def cog_unload(self):
        self.update_openrouter_models.cancel()
        self.sync_cache.cancel()
