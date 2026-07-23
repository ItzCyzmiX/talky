from datetime import datetime
import asyncio

from discord.ext import tasks, commands

from bot.consts import BOTS_CATEGORY_ID
from bot.apis.supabase import get_bots_with_ids, get_admins, get_messages
from bot.utils import get_status
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import Talky


class CacheCog(commands.Cog):
    def __init__(self, bot):
        self.bot: "Talky" = bot

        self.sync_cache.start()

    @tasks.loop(minutes=30)
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

            self.bot.running_bots[str(c.id)] = {
                "admins": admins,
                "messages": messages,
                "lock": asyncio.Lock(),
            }

        await asyncio.sleep(0.3)
        print(get_status(bot=self.bot))

    def cog_unload(self):
        self.sync_cache.cancel()
