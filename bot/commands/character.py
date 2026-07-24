import discord
from discord import app_commands
from discord.ext import commands

from bot.apis.supabase import get_character, remove_character
from bot.bot import Talky
from bot.commands.checks import is_in_creation_channel
from bot.consts import (
    CUSTOM_CHARACTERS_CHANNEL_ID,
    DELETE_DELAY,
    GUILD,
)
from bot.ui.create_character import NewCharModal


class CharacterCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot

    @app_commands.command(name="create", description="Create a character")
    @app_commands.guilds(GUILD)
    @is_in_creation_channel()
    async def create(self, interaction: discord.Interaction, forkable: bool = True):
        try:
            await interaction.response.send_modal(
                NewCharModal(bot=self.bot, forkable=forkable)
            )

        except Exception as e:
            print("ERROR CREATING: ", str(e))

    @app_commands.command(name="edit", description="Edits a character")
    @app_commands.describe(character_id="The Character's ID")
    @app_commands.guilds(GUILD)
    @is_in_creation_channel()
    async def edit(self, interaction: discord.Interaction, character_id: str):
        try:
            if len(character_id) > 8:
                await interaction.response.send_message(
                    content="Invalid character ID (8 characters max)",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            char = await get_character(
                supabase=self.bot.supabase,
                _id=character_id,
            )

            if not char:
                await interaction.response.send_message(
                    content="Invalid character ID!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            owner = int(char["creator_id"]) == interaction.user.id

            if not owner:
                await interaction.response.send_message(
                    content="You MUST be owner of this character to edit it!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            await interaction.response.send_modal(
                NewCharModal(bot=self.bot, defaults=char)
            )

        except Exception as e:
            print("ERROR EDITING: ", str(e))

    @app_commands.command(name="delete", description="Deletes a character")
    @app_commands.describe(character_id="The Character's ID")
    @app_commands.guilds(GUILD)
    @is_in_creation_channel()
    async def delete(self, interaction: discord.Interaction, character_id: str):
        try:
            if len(character_id) > 8:
                await interaction.response.send_message(
                    content="Invalid character ID (8 characters max)",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            char = await get_character(
                supabase=self.bot.supabase,
                _id=character_id,
            )

            if not char:
                await interaction.response.send_message(
                    content="Invalid character ID!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            owner = int(char["creator_id"]) == interaction.user.id

            if not owner:
                await interaction.response.send_message(
                    content="You MUST be owner of this character to delete it!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            ok = await remove_character(supabase=self.bot.supabase, _id=character_id)

            if not ok:
                await interaction.response.send_message(
                    content="Couldn't delete character, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            channel = interaction.client.get_channel(CUSTOM_CHARACTERS_CHANNEL_ID)

            message = await channel.fetch_message(char["message_id"])

            await message.delete()

            for k in list(interaction.client.running_bots.keys()):
                v = interaction.client.running_bots[k]
                if (
                    v.get("custom_character_id", None) is not None
                    and v.get("custom_character_id", None) == char["id"]
                ):
                    c = interaction.client.get_channel(int(k))
                    if c is not None:
                        await c.delete()

                    del interaction.client.running_bots[k]

            await interaction.user.send(
                f"Your character {char['name']} has been removed!\nIts's ID will no longer be functional"
            )

            await interaction.response.send_message(
                content="Character removed!", ephemeral=True, delete_after=DELETE_DELAY
            )

        except Exception as e:
            print("ERROR DELETING: ", str(e))
