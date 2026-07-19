import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.character_api import send_msg_to_bot, _get_openrouter_models
from bot.supabase import (
    get_messages,
    update_messages,
    create_supabase,
    get_bots_with_ids,
)
import os
from bot.consts import GUILD, DESCRITPTION, BOTS_CATEGORY_ID, MESSAGE_HISTOY_LIMIT
import asyncio
from pprint import pprint

load_dotenv()


class Talky(commands.Bot):
    def __init__(self, *, supabase, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True
        intents.messages = True
        intents.guilds = True

        super().__init__(command_prefix="!", description=DESCRITPTION, intents=intents)

        self.supabase = supabase
        self.running_bots = []

    async def setup_hook(self):
        await self.load_extension("bot.commands")

    async def on_ready(self):
        print(f"We have logged in as {self.user}")

        await self.tree.sync(guild=GUILD)

        bot_category = self.get_channel(BOTS_CATEGORY_ID)

        channels = bot_category.text_channels
        channel_ids = list(map(lambda x: x.id, channels))

        await asyncio.sleep(0.3)

        db_bot_ids = await get_bots_with_ids(self.supabase, channel_ids)

        for c in channels:
            if c.id not in db_bot_ids:
                await c.delete()
                continue

            self.running_bots.append(c.id)
        await asyncio.sleep(0.5)
        res = await _get_openrouter_models()
        pprint(res)

    async def on_message(self, message: discord.Message):

        if message.author == self.user:
            return

        if message.channel.id in self.running_bots:
            async with message.channel.typing():

                msg = message.content

                old_msgs = await get_messages(self.supabase, message.channel.id)

                if old_msgs is None:
                    return

                new_msgs = [
                    *old_msgs,
                    {"role": "user", "content": f"({message.author.name}) {msg}"},
                ]

                new_msgs = new_msgs[-MESSAGE_HISTOY_LIMIT:]

                response = await send_msg_to_bot(new_msgs)

                if response is None:
                    return

                new_msgs = [*new_msgs, {"role": "assistant", "content": response}]

                did_update = await update_messages(
                    self.supabase, message.channel.id, {"messages": new_msgs}
                )

                if not did_update:
                    return

                await message.channel.send(f"{message.channel.name}: {response}")


async def run_bot():
    supabase_client = await create_supabase()
    bot = Talky(supabase=supabase_client)
    await bot.start(os.getenv("DISCORD_TOKEN"))
