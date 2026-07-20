import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.character_api import send_msg_to_bot, _get_openrouter_models
from bot.supabase import (
    get_messages,
    update_messages,
    create_supabase,
    get_bots_with_ids,
    get_chat_model,
    change_bot_gpt,
    get_admins,
)
import os
from bot.consts import GUILD, DESCRITPTION, BOTS_CATEGORY_ID, MESSAGE_HISTOY_LIMIT
from asyncio import sleep

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
        self.running_bots = {}
        self.openrouter_models = []

    async def setup_hook(self):
        await self.load_extension("bot.commands")

    async def on_ready(self):
        print(f"We have logged in as {self.user}")

        await self.tree.sync(guild=GUILD)

        bot_category = self.get_channel(BOTS_CATEGORY_ID)

        channels = bot_category.text_channels
        channel_ids = list(map(lambda x: x.id, channels))

        await sleep(0.3)

        db_bot_ids = await get_bots_with_ids(self.supabase, channel_ids)

        for c in channels:
            if c.id not in db_bot_ids:
                await c.delete()
                continue

            admins = await get_admins(self.supabase, c.id)
            messages = await get_messages(self.supabase, c.id)
            gpt = await get_chat_model(self.supabase, c.id)

            self.running_bots[c.id] = {
                "admins": admins,
                "messages": messages,
                "gpt": gpt,
            }

        await sleep(0.3)
        self.openrouter_models = await _get_openrouter_models()

    async def on_message_delete(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.channel.id in self.running_bots.keys():

            for i in range(len(self.running_bots[message.channel.id]["messages"])):
                index = (
                    len(self.running_bots[message.channel.id]["messages"]) - i - 1
                )  # bottom up for better performance

                if (
                    self.running_bots[message.channel.id]["messages"][index][
                        "discord_message_id"
                    ]
                    == message.id
                ):
                    new_messages = self.running_bots[message.channel.id][
                        "messages"
                    ].copy()
                    new_messages.pop(index)

                    ok = await update_messages(
                        self.supabase, message.channel.id, {"messages": new_messages}
                    )
                    if ok:
                        self.running_bots[message.channel.id]["messages"] = new_messages
                    await sleep(0.3)
                    break

    async def on_message(self, message: discord.Message):

        if message.author == self.user:
            return

        if message.channel.id in self.running_bots.keys():

            async with message.channel.typing():

                revert_to_llama = False

                msg = message.content

                model = self.running_bots.get(message.channel.id, {}).get("gpt", None)

                old_msgs = self.running_bots.get(message.channel.id, {}).get(
                    "messages", None
                )

                if model is None:
                    model = await get_chat_model(self.supabase, message.channel.id)

                    if model is None:
                        model = "llama"
                        revert_to_llama = True

                if old_msgs is None:
                    old_msgs = await get_messages(self.supabase, message.channel.id)

                    if old_msgs is None:
                        await message.channel.send(
                            "Couldn't retreive messages data, try again",
                            delete_after=10,
                        )
                        return

                new_msgs = [
                    *old_msgs,
                    {
                        "role": "user",
                        "content": f"({message.author.name}) {msg}",
                        "discord_message_id": message.id,
                    },
                ]

                new_msgs = new_msgs[-MESSAGE_HISTOY_LIMIT:]

                response = await send_msg_to_bot(new_msgs, model)

                if response is None:
                    if model != "llama":

                        await message.channel.send(
                            f"{model} failed to generate a response, using llama...",
                            delete_after=10,
                        )

                        response = await send_msg_to_bot(new_msgs, "llama")
                        revert_to_llama = True

                        if response is None:
                            await message.channel.send(
                                f"{model} failed to generate a response, try again",
                                delete_after=10,
                            )
                            await change_bot_gpt(message.channel.id, "llama")

                        return

                response_message = await message.channel.send(
                    f"{message.channel.name}: {response}"
                )

                new_msgs = [
                    *new_msgs,
                    {
                        "role": "assistant",
                        "content": response,
                        "discord_message_id": response_message.id,
                    },
                ]

                did_update = await update_messages(
                    self.supabase, message.channel.id, {"messages": new_msgs}
                )

                if not did_update:
                    await response_message.delete()

                self.running_bots[message.channel.id]["messages"] = new_msgs

                if revert_to_llama:
                    await change_bot_gpt(message.channel.id, "llama")


async def run_bot():
    supabase_client = await create_supabase()
    bot = Talky(supabase=supabase_client)
    await bot.start(os.getenv("DISCORD_TOKEN"))
