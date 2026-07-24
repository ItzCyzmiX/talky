import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bot.apis.character_api import send_msg_to_bot
from bot.apis.supabase import (
    create_supabase,
    get_characters_ids,
    get_messages,
    update_messages,
)
from bot.cache import CacheCog
from bot.consts import (
    DELETE_DELAY,
    DESCRITPTION,
    GUILD,
    MESSAGE_HISTOY_LIMIT,
)
from bot.types import RunningBots
from bot.ui.create_character import ChatToCharacterView
from bot.utils import alter_msg, sanitize
from bot.webhooks.github_webhook import start_github_webhook

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

        await self.add_cog(CacheCog(bot=self))

        # loads all persistent custom characters views after restart
        char_ids = await get_characters_ids(self.supabase)

        if char_ids is not None:
            for char in char_ids:
                self.add_view(ChatToCharacterView(character_id=char["id"], bot=self))

    async def on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                str(error), ephemeral=True, delete_after=DELETE_DELAY
            )
            return

        # Fallback for all other unhandled slash command errors
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

        if str(message.channel.id) not in self.running_bots.keys():
            return

        # i hate this function, but im too lazy and dumb to rewrite it
        try:
            async with self.running_bots[str(message.channel.id)]["lock"]:
                async with message.channel.typing():
                    all_overwrites = message.channel.overwrites_for(
                        message.guild.default_role
                    )

                    all_overwrites.send_messages = False

                    await message.channel.set_permissions(
                        message.guild.default_role, overwrite=all_overwrites
                    )

                    model = "llama"

                    msg = sanitize(message.content)

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

                        global_size = sum([x.size for x in message.attachments]) / (
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
                                "text": f"({sanitize(message.author.name)}) {msg}",
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
                        content = f"({sanitize(message.author.name)}) {msg}"

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
                        f"{message.channel.name}: {sanitize(response)}"
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
                            "content": sanitize(response),
                            "discord_message_id": response_message.id,
                        },
                    ]
                )

                did_update = await update_messages(
                    self.supabase, message.channel.id, {"messages": new_msgs}
                )

                if not did_update:
                    await response_message.delete()
                    await message.delete()

                self.running_bots[str(message.channel.id)]["messages"] = new_msgs
        except:
            await message.channel.send(
                "Error while generating response, try again!", delete_after=10
            )

        finally:
            all_overwrites = message.channel.overwrites_for(message.guild.default_role)

            all_overwrites.send_messages = True

            await message.channel.set_permissions(
                message.guild.default_role, overwrite=all_overwrites
            )

            await self.process_commands(message)


async def run_bot():
    supabase_client = await create_supabase()
    bot = Talky(supabase=supabase_client)
    await bot.start(os.getenv("DISCORD_TOKEN"))
