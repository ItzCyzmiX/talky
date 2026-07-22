import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import GUILD, BOTS_CATEGORY_ID
from bot.bot import Talky
from bot.supabase import update_messages, get_messages
from bot.character_api import send_msg_to_bot
from bot.utils import alter_msg


class ContextCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot

        self.delete_ctx = app_commands.ContextMenu(
            name="Delete AI message", callback=self.delete, guild_ids=[GUILD.id]
        )

        self.delete_ctx.add_check(is_in_a_chat)

        self.edit_ctx = app_commands.ContextMenu(
            name="Edit AI message", callback=self.edit, guild_ids=[GUILD.id]
        )

        self.delete_ctx.add_check(is_in_a_chat)

        self.regenerate_ctx = app_commands.ContextMenu(
            name="Regenerate AI message", callback=self.regenerate, guild_ids=[GUILD.id]
        )

        self.delete_ctx.add_check(is_in_a_chat)

        self.bot.tree.add_command(self.delete_ctx)
        self.bot.tree.add_command(self.edit_ctx)
        self.bot.tree.add_command(self.regenerate_ctx)

    # not using alter_msg because the callback is gonna be async
    async def edit(self, interaction: discord.Interaction, message: discord.Message):
        if str(interaction.channel.id) in self.bot.running_bots.keys():
            if message.author != self.bot.user:

                await interaction.response.send_message(
                    "Can only be used on bot's messages!",
                    ephemeral=True,
                    delete_after=5,
                )
                return

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
            if message.author != self.bot.user:
                await interaction.response.send_message(
                    "Can only be used on bot's messages!",
                    ephemeral=True,
                    delete_after=5,
                )

            ok = await alter_msg(
                bot=self.bot,
                channel_id=interaction.channel.id,
                message_id=message.id,
                role="assistant",
                callback=lambda msg: None,
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

    async def regenerate(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        if str(interaction.channel.id) in self.bot.running_bots.keys():
            if message.author != self.bot.user:
                await interaction.response.send_message(
                    "Can only be used on bot's messages!",
                    ephemeral=True,
                    delete_after=5,
                )

            old_msgs = self.bot.running_bots.get(str(message.channel.id), {}).get(
                "messages", None
            )

            if old_msgs is None:
                old_msgs = await get_messages(self.bot.supabase, message.channel.id)

            if old_msgs is None:
                await interaction.response.send_message(
                    "Couldn't regenerate the message", ephemeral=True, delete_after=10
                )
                return

            message_index = -1

            for i in range(len(old_msgs)):
                index = len(old_msgs) - i - 1

                if old_msgs[index]["discord_message_id"] == message.id:
                    message_index = index
                    break

            if message_index == -1:
                await interaction.response.send_message(
                    "Couldn't locate the message", ephemeral=True, delete_after=10
                )
                return

            cut_msgs = old_msgs[:message_index]

            response = await send_msg_to_bot(cut_msgs, "llama")

            if response is None:
                await interaction.response.send_message(
                    "Couldn't regenerate the message", ephemeral=True, delete_after=10
                )
                return

            ok = await alter_msg(
                bot=self.bot,
                channel_id=interaction.channel.id,
                message_id=message.id,
                role="assistant",
                callback=lambda msg: {
                    "discord_message_id": message.id,
                    "content": response,
                    "role": "assistant",
                },
            )

            if ok:
                await message.edit(content=response)
                await interaction.response.send_message(
                    "Edited ai message!", ephemeral=True, delete_after=5
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


def is_in_a_chat(interaction: discord.Interaction) -> bool:
    if (
        hasattr(interaction.channel, "category")
        and interaction.channel.category is not None
    ):
        return interaction.channel.category.id == BOTS_CATEGORY_ID

    return False
