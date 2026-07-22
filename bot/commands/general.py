import asyncio

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import BOT_CREATION_CHANNEL, GUILD, DELETE_DELAY
from bot.bot import Talky
from bot.utils import (
    sys_message,
    sanitize_msg,
    fetch_gif,
    is_in_chatbot_channel,
    _validate_admin,
)
from bot.consts import BOT_CREATION_CHANNEL, BOTS_CATEGORY_ID
from bot.supabase import new_bot


class GeneralCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot

    @app_commands.command(name="help", description="Get commands")
    @app_commands.guilds(GUILD)
    async def help(self, interaction: discord.Interaction):

        if interaction.channel.id != BOT_CREATION_CHANNEL:
            await interaction.response.send_message(
                "must be used in a conversation channel!"
            )
            return

        await interaction.response.send_message(
            (
                "## 🛠️ Commands\n"
                "- `/talk <bot_name> [private]` — Create a new chatbot channel *(Anyone)*\n"
                "- `/help` — Show all available commands *(Anyone)*\n"
                "- `/status` — Check if you're an admin in current channel *(Anyone)*\n"
                "- `/admin <user>` — Promote a user to admin *(Admin only)*\n"
                "- `/add <user>` — Add user to private chat *(Admin only)*\n"
                "- `/kick <user>` — Remove user from private chat *(Admin only)*\n"
                "- `/kill` — Delete the chatbot channel permanently *(Admin only)*\n\n"
                "### Context Menu Commands (Right-Click)\n"
                "- **Delete AI message** (On Bot response) — Delete the AI's message from history *(Anyone)*\n"
                "- **Edit AI message** (On Bot response) — Edit the AI's response via modal popup *(Anyone)*"
            ),
            ephemeral=True,
            delete_after=DELETE_DELAY * 3,
        )

    @app_commands.command(name="status", description="Get if you are admin or not")
    @app_commands.guilds(GUILD)
    @is_in_chatbot_channel()
    async def status(self, interaction: discord.Interaction):

        am_admin = await _validate_admin(
            bot=self.bot, channel_id=interaction.channel_id, user_id=interaction.user.id
        )

        msg = "You are" + (" " if am_admin else " not ") + "admin"

        await interaction.response.send_message(
            msg,
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )

    @app_commands.command(name="talk", description="Create a new chat bot")
    @app_commands.describe(
        bot_name="Name of the bot",
        private="If the chat will be private",
    )
    @app_commands.guilds(GUILD)
    async def talk(
        self,
        interaction: discord.Interaction,
        bot_name: str,
        private: Optional[bool],
    ):

        if interaction.channel_id != BOT_CREATION_CHANNEL:
            await interaction.response.send_message(
                f"Must be used in the {self.bot.get_channel(BOT_CREATION_CHANNEL).mention0} !",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        try:

            bot_category = self.bot.get_channel(BOTS_CATEGORY_ID)

            if private:
                guild = interaction.guild

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    ),
                }

                new_channel = await bot_category.create_text_channel(
                    name=sanitize_msg(bot_name), overwrites=overwrites, slowmode_delay=5
                )
            else:
                new_channel = await bot_category.create_text_channel(name=bot_name)

            while not new_channel:
                await asyncio.sleep(0.3)

            ok = await new_bot(
                self.bot.supabase,
                new_channel.id,
                bot_name,
                [interaction.user.id],
                {
                    "messages": [sys_message(bot_name)],
                },
            )

            await asyncio.sleep(0.3)

            if not ok:
                await interaction.response.send_message(
                    "Couldnt create the chat bot, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            self.bot.running_bots[str(new_channel.id)] = {
                "admins": [str(interaction.user.id)],
                "messages": [sys_message(bot_name)],
            }

            await new_channel.send(
                f"{interaction.user.mention} has started a{' private ' if private else ' '}conversation with {bot_name}!"
            )

            await interaction.response.send_message(
                f"Go chat with {bot_name} in {new_channel.mention}!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )

            gif_url = await fetch_gif(bot_name)

            if gif_url:
                await new_channel.send(f"{gif_url}")

        except Exception as e:
            print("ERROR TALKING: ", str(e))
