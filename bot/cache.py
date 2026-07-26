import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from bot.apis.supabase import get_chats, remove_bot
from bot.consts import BOTS_CATEGORY_ID
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
        channel_ids = [channel.id for channel in channels]

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

            chat = [chat for chat in chats if int(chat["id"]) == c.id][0]

            msgs = []

            if isinstance(chat["messages"], list):
                msgs = chat["messages"]
            elif isinstance(chat["messages"], dict):
                msgs = chat["messages"].get("messages", [])

            self.bot.running_bots[str(c.id)] = {
                "admins": chat["admins"],
                "messages": msgs,
                "custom_character_id": chat.get("custom_character_id", None),
                "lock": asyncio.Lock(),
            }

        # mainly used for removing chats, from the db, with characters that have been deleted
        for _id in db_bots_ids:
            if _id not in channel_ids:
                await remove_bot(self.bot.supabase, _id)

        await asyncio.sleep(1)  # JWT clock skew issues fix

        print(get_status(bot=self.bot))

    async def cog_unload(self):
        self.sync_cache.cancel()
