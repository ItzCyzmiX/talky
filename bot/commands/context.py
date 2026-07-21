import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import GUILD
from bot.bot import Talky
from bot.supabase import update_messages
from bot.utils import alter_msg

class ContextCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot

        self.delete_ctx = app_commands.ContextMenu(
            name="Delete AI message", callback=self.delete, guild_ids=[GUILD.id]
        )

        self.edit_ctx = app_commands.ContextMenu(
            name="Edit AI message", callback=self.edit, guild_ids=[GUILD.id]
        )

        self.bot.tree.add_command(self.delete_ctx)
        self.bot.tree.add_command(self.edit_ctx)


    # not using alter_msg because the callback is gonna be async
    async def edit(self, interaction: discord.Interaction, message: discord.Message):
        if str(interaction.channel.id) in self.bot.running_bots.keys():
            if message.author == self.bot.user:
                for i in range(
                    len(self.bot.running_bots[str(message.channel.id)]["messages"])
                ):
                    index = (
                        len(self.bot.running_bots[str(message.channel.id)]["messages"])
                        - i
                        - 1
                    )

                    if (
                        self.bot.running_bots[str(message.channel.id)]["messages"][index][
                            "discord_message_id"
                        ]
                        == message.id
                        and self.bot.running_bots[str(message.channel.id)]["messages"][
                            index
                        ]["role"]
                        == "assistant"
                    ):

                        await interaction.response.send_modal(
                            AIEdit(self.bot, message, index, interaction.channel.name)
                        )
                        await asyncio.sleep(0.3)
                        return

            await interaction.response.send_message(
                "Couldn't edit the message", ephemeral=True, delete_after=10
            )

    async def delete(self, interaction: discord.Interaction, message: discord.Message):
        if str(interaction.channel.id) in self.bot.running_bots.keys():
            if message.author == self.bot.user:
                ok = await alter_msg(
                    bot=self.bot,
                    channel_id=interaction.channel.id,
                    message_id=message.id,
                    role="assistant",
                    callback=lambda msg: None
                )

                if ok:
                    await message.delete()
                    await interaction.response.send_message(
                        "delted ai message!", ephemeral=True, delete_after=5
                    )

                else:
                    await interaction.response.send_message(
                        "Couldn't delete the message", ephemeral=True, delete_after=10
                    )


class AIEdit(
    discord.ui.Modal,
):
    def __init__(self, bot: Talky, message: discord.Message, index: int, bot_name: str):
        super().__init__(title="Edit Ai Response")
        self.bot = bot
        self.message = message
        self.index = index
        self.bot_name = bot_name
        self.new_message_input = discord.ui.TextInput(
            label="new message",
            default="".join(self.message.content.split(":")[1:]),  # trim the bot name
            style=discord.TextStyle.paragraph,
        )

        self.add_item(self.new_message_input)

    async def on_submit(self, interaction: discord.Interaction):

        if (
            not self.new_message_input.value
            or self.new_message_input.value == self.message.content
        ):
            return

        new_messages = self.bot.running_bots[self.message.channel.id]["messages"].copy()
        new_messages[self.index] = {
            "role": "assistant",
            "content": f"{self.bot_name}: {self.new_message_input.value}",  # add the bot name back
            "discord_message_id": self.message.id,
        }

        ok = await update_messages(
            self.bot.supabase,
            self.message.channel.id,
            {"messages": new_messages},
        )

        if ok:
            self.bot.running_bots[self.message.channel.id]["messages"] = new_messages
            await self.message.edit(content=self.new_message_input.value)
            await interaction.response.send_message(
                "Edited ai message!", ephemeral=True, delete_after=5
            )