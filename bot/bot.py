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
from bot.consts import GUILD, DESCRITPTION, BOTS_CATEGORY_ID, MESSAGE_HISTOY_LIMIT
from bot.utils import sanitize_msg
import os
import asyncio

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

        await asyncio.sleep(0.3)

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

        await asyncio.sleep(0.3)
        self.openrouter_models = await _get_openrouter_models()

    async def on_message_delete(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.channel.id in self.running_bots.keys():
            try:
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
                            self.supabase,
                            message.channel.id,
                            {"messages": new_messages},
                        )
                        if ok:
                            self.running_bots[message.channel.id][
                                "messages"
                            ] = new_messages
                        await asyncio.sleep(0.3)
                        break
            except KeyError:
                pass  # message delted from early messages (not in chat history anymore) or by the bot due to an error

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        if after.channel.id in self.running_bots.keys():
            if before != after:
                try:
                    for i in range(
                        len(self.running_bots[after.channel.id]["messages"])
                    ):
                        index = (
                            len(self.running_bots[after.channel.id]["messages"]) - i - 1
                        )

                        if (
                            self.running_bots[after.channel.id]["messages"][index][
                                "discord_message_id"
                            ]
                            == after.id
                        ):
                            new_messages = self.running_bots[after.channel.id][
                                "messages"
                            ].copy()

                            new_messages[index] = {
                                "role": "user",
                                "discord_message_id": after.id,
                                "content": after.content,
                            }

                            ok = await update_messages(
                                self.supabase,
                                after.channel.id,
                                {"messages": new_messages},
                            )
                            if ok:
                                self.running_bots[after.channel.id][
                                    "messages"
                                ] = new_messages
                            await asyncio.sleep(0.3)
                            break
                except KeyError:
                    pass  # message edited from early messages (not in chat history anymore)

    async def on_message(self, message: discord.Message):

        if message.author == self.user:
            return

        if message.channel.id in self.running_bots.keys():

            async with message.channel.typing():

                all_overwrites = message.channel.overwrites_for(
                    message.guild.default_role
                )

                all_overwrites.send_messages = False

                await message.channel.set_permissions(
                    message.guild.default_role, overwrite=all_overwrites
                )

                revert_to_llama = False

                msg = sanitize_msg(message.content)

                content = None

                model = self.running_bots.get(message.channel.id, {}).get("gpt", None)

                old_msgs = self.running_bots.get(message.channel.id, {}).get(
                    "messages", None
                )

                if message.attachments:

                    if len(message.attachments) > 4:
                        await message.channel.send(
                            "Only 4 at max attachment per message!",
                            delete_after=10,
                        )
                        await message.delete()
                        return

                    for a in message.attachments:
                        if (
                            not a.content_type.startswith("image/")
                            or a.content_type == "iamge/gif"
                        ):
                            await message.channel.send(
                                "File type invalid (make sure its an image not a GIF)!",
                                delete_after=10,
                            )
                            await message.delete()
                            return

                    global_size = sum(
                        list(map(lambda x: x.size, message.attachments))
                    ) / (
                        1024 * 1024
                    )  # bytes to mb

                    if global_size >= 20:
                        await message.channel.send(
                            "Files too large (20mb max in total)!",
                            delete_after=10,
                        )
                        await message.delete()
                        return

                    model = "vision"

                    content = [
                        {
                            "type": "text",
                            "text": f"({sanitize_msg(message.author.name)}) {msg}",
                        },
                        *[
                            {
                                "type": "image_url",
                                "image_url": {"url": i.url},
                            }
                            for i in message.attachments
                        ],
                    ]

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

                if content is None:
                    content = f"({sanitize_msg(message.author.name)}) {msg}"

                new_msgs = [
                    *old_msgs,
                    {
                        "role": "user",
                        "content": content,
                        "discord_message_id": message.id,
                    },
                ]

                new_msgs = new_msgs[-MESSAGE_HISTOY_LIMIT:]

                try:
                    response = await send_msg_to_bot(new_msgs, model)
                except:
                    if model == "vision":
                        await message.channel.send(
                            "Uploaded image failed, try again",
                            delete_after=10,
                        )
                        return

                if response is None:
                    if model != "llama" and model != "vision":

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
                    f"{message.channel.name}: {sanitize_msg(response)}"
                )

                all_overwrites = message.channel.overwrites_for(
                    message.guild.default_role
                )

                all_overwrites.send_messages = True

                await message.channel.set_permissions(
                    message.guild.default_role, overwrite=all_overwrites
                )

            new_msgs = new_msgs[:-1]
            new_msgs = [
                *new_msgs,
                {
                    "role": "user",
                    "content": msg,
                    "discord_message_id": message.id,
                },
                {
                    "role": "assistant",
                    "content": sanitize_msg(response),
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
