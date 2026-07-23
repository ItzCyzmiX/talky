from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Talky
from bot.commands.checks import is_in_creation_channel
from bot.consts import GUILD
from bot.ui.create_character import NewCharModal


class CharacterCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot

    @app_commands.command(name="create", description="Create a character")
    @app_commands.guilds(GUILD)
    @is_in_creation_channel()
    async def create(
        self,
        interaction: discord.Interaction,
    ):
        try:
            await interaction.response.send_modal(NewCharModal(bot=self.bot))

        except Exception as e:
            print("ERROR CREATING: ", str(e))

    @app_commands.command(name="create", description="Create a character")
    @app_commands.guilds(GUILD)
    @is_in_creation_channel()
    async def create(
        self,
        interaction: discord.Interaction,
    ):
        try:
            await interaction.response.send_modal(NewCharModal(bot=self.bot))

        except Exception as e:
            print("ERROR CREATING: ", str(e))
