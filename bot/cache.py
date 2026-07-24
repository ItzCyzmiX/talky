import asyncio
from datetime import date, datetime
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from bot.apis.supabase import get_chats
from bot.consts import BOTS_CATEGORY_ID, CUSTOM_CHARACTERS_CHANNEL_ID
from bot.utils import get_status

if TYPE_CHECKING:
    from bot.bot import Talky


class CacheCog(commands.Cog):
    def __init__(self, bot: "Talky"):
        self.bot = bot

        self.sync_cache.start()

    @tasks.loop(minutes=30)
    async def sync_cache(self):
        print(f"[{datetime.now()}] Syncing cache...")

        await self.bot.wait_until_ready()

        bot_category = self.bot.get_channel(BOTS_CATEGORY_ID)

        if not bot_category:
            return

        channels = bot_category.text_channels

        await asyncio.sleep(0.3)

        chats = await get_chats(self.bot.supabase)

        if chats is None:
            print("error loading chats")
            return

        db_bots_ids = [chat["id"] for chat in chats]

        await asyncio.sleep(0.5)

        for c in channels:
            if c.id not in db_bots_ids:
                await c.delete()
                continue

            chat = next(chat for chat in chats if int(chat["id"]) == c.id)

            self.bot.running_bots[str(c.id)] = {
                "admins": chat["admins"],
                "messages": chat["messages"],
                "custom_character_id": chat.get("custom_character_id", None),
                "lock": asyncio.Lock(),
            }

        await asyncio.sleep(0.3)

        print(get_status(bot=self.bot))

    async def cog_unload(self):
        self.sync_cache.cancel()
