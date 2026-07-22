import os

import discord
from discord.ext import commands
from discord import app_commands

from dotenv import load_dotenv

from bot.character_api import send_msg_to_bot
from bot.cron import CronCog
from bot.supabase import (
    get_messages,
    update_messages,
    create_supabase,
)
from bot.consts import GUILD, DESCRITPTION, MESSAGE_HISTOY_LIMIT, DELETE_DELAY
from bot.utils import alter_msg, sanitize_msg
from bot.github_webhook import start_github_webhook
from bot.types import RunningBots

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
        self.running_bots: RunningBots = {}
        self.version: str = "v1"

    async def setup_hook(self):
        self.tree.on_error = self.on_tree_error

        await self.load_extension("bot.commands")

        await start_github_webhook(bot=self)

    async def on_ready(self):

        await self.tree.sync(guild=GUILD)

        await self.add_cog(CronCog(bot=self))

    async def on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                str(error), ephemeral=True, delete_after=DELETE_DELAY
            )
            return

        # Fallback for all other unhandled slash command errors
        print(f"Error in slash command: {error}")  # Or use your logger
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred.",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if (
            payload.cached_message is None
        ):  # message is out cache (and probably out of the bot's memory anyways)
            return

        if payload.cached_message.author == self.user:
            return

        if str(payload.channel_id) in self.running_bots.keys():
            await alter_msg(
                bot=self,
                channel_id=payload.channel_id,
                message_id=payload.message_id,
                role="user",
                callback=lambda msg: None,
            )

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.message.author.bot:
            return

        if str(payload.channel_id) in self.running_bots.keys():
            await alter_msg(
                bot=self,
                channel_id=payload.channel_id,
                message_id=payload.message_id,
                role="user",
                callback=lambda msg: {
                    "content": payload.data["content"],
                    "discord_message_id": payload.message_id,
                    "role": "user",
                },
            )

    async def on_message(self, message: discord.Message):

        if message.author == self.user:
            return

        if str(message.channel.id) in self.running_bots.keys():

            async with message.channel.typing():

                all_overwrites = message.channel.overwrites_for(
                    message.guild.default_role
                )

                all_overwrites.send_messages = False

                await message.channel.set_permissions(
                    message.guild.default_role, overwrite=all_overwrites
                )

                model = "llama"

                msg = sanitize_msg(message.content)

                content = None

                old_msgs = self.running_bots.get(str(message.channel.id), {}).get(
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
                        if a.content_type is None:
                            continue
                        if (
                            not a.content_type.startswith("image/")
                            or a.content_type == "image/gif"
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

                new_msgs = old_msgs.copy()

                new_msgs.append(
                    {
                        "role": "user",
                        "content": content,
                        "discord_message_id": message.id,
                    },
                )

                new_msgs = new_msgs[-MESSAGE_HISTOY_LIMIT:]

                response = await send_msg_to_bot(new_msgs, model)

                if response is None:
                    if model == "vision":
                        await message.channel.send(
                            "Uploaded image failed, try again",
                            delete_after=10,
                        )
                        return

                    await message.channel.send(
                        f"{model} failed to generate a response, try again...",
                        delete_after=10,
                    )
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

            new_msgs.extend(
                [
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
            )

            did_update = await update_messages(
                self.supabase, message.channel.id, {"messages": new_msgs}
            )

            if not did_update:
                await response_message.delete()

            self.running_bots[str(message.channel.id)]["messages"] = new_msgs


async def run_bot():
    supabase_client = await create_supabase()
    bot = Talky(supabase=supabase_client)
    await bot.start(os.getenv("DISCORD_TOKEN"))
