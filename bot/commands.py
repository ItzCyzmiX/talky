import discord
from discord import app_commands
from discord.ext import commands

import asyncio
from typing import Optional

from bot.consts import BOT_CREATION_CHANNEL, GUILD, BOTS_CATEGORY_ID, DELETE_DELAY
from bot.bot import Talky
from bot.utils import sys_message, fetch_gif
from bot.supabase import (
    new_bot,
    remove_bot,
    is_admin,
    add_admin,
    change_bot_gpt,
    update_messages,
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


class ModelSelect(discord.ui.Select):
    def __init__(self, ai_models: list[str], channel_id: int, bot: Talky):
        options = [
            discord.SelectOption(label=model, value=model.lower())
            for model in ai_models
        ]

        self._channel_id = channel_id
        self.bot = bot

        super().__init__(
            placeholder="Select AI Model", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):

        chosen_model = (
            "llama"
            if self.values[0].lower() == "llama (default)"
            else self.values[0].lower()
        )

        ok = await change_bot_gpt(self.bot.supabase, self._channel_id, chosen_model)
        await asyncio.sleep(0.3)
        if not ok:
            await interaction.response.send_message(
                "Couldn't change chat AI model, using default llama",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        self.bot.running_bots[self._channel_id]["gpt"] = chosen_model

        await interaction.response.send_message(
            f"This chat will now use {chosen_model}, in case of any error it will fall back to llama",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


class ModelView(discord.ui.View):
    def __init__(self, models: list[str], channel_id, bot):
        super().__init__(timeout=180)

        self.add_item(ModelSelect(ai_models=models, channel_id=channel_id, bot=bot))


class Commands(commands.Cog):
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
                "- `/gpt` — Select AI model for this channel *(Admin only)*\n"
                "- `/add <user>` — Add user to private chat *(Admin only)*\n"
                "- `/kick <user>` — Remove user from private chat *(Admin only)*\n"
                "- `/kill` — Delete the chatbot channel permanently *(Admin only)*\n\n"
                "### Context Menu Commands (Right-Click)\n"
                "- **Delete AI message** (On Bot response) — Delete the AI's message from history *(Anyone)*\n"
                "- **Edit AI message** (On Bot response) — Edit the AI's response via modal popup *(Anyone)*"
            ),
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )

    @app_commands.command(name="status", description="Get if you are admin or not")
    @app_commands.guilds(GUILD)
    async def status(self, interaction: discord.Interaction):
        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
            "admins", None
        )

        am_admin = False

        if admins is None:
            am_admin = await is_admin(
                self.bot.supabase, interaction.channel.id, interaction.user.id
            )
        else:
            am_admin = interaction.user.id in admins

        msg = "You are" + (" " if am_admin else " not ") + "admin"
        await interaction.response.send_message(
            msg,
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )

    @app_commands.command(name="admin", description="Gives admin to selected users")
    @app_commands.describe(target="The user you want to give admin to")
    @app_commands.guilds(GUILD)
    async def admin(self, interaction: discord.Interaction, target: discord.Member):

        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        try:
            admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
                "admins", None
            )

            can_give_admin = False

            if admins is None:
                can_give_admin = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
            else:
                can_give_admin = interaction.user.id in admins

            if not can_give_admin:
                await interaction.response.send_message(
                    "You must be admin of this conversation!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            if target.id == interaction.user.id:
                await interaction.response.send_message(
                    "You are already admin!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            target_can_give_admin = await is_admin(
                self.bot.supabase, interaction.channel.id, target.id
            )
            if target_can_give_admin:
                await interaction.response.send_message(
                    f"{target.mention} is already admin!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            ok = await add_admin(self.bot.supabase, interaction.channel.id, target.id)

            if ok:
                self.bot.running_bots[interaction.channel.id]["admins"] = [
                    *self.bot.running_bots[interaction.channel.id]["admins"],
                    target.id,
                ]
                await interaction.response.send_message(
                    f"{target.mention} is now an admin of this conversation!",
                    delete_after=10,
                )
            else:
                await interaction.response.send_message(
                    f"Couldnt give {target.mention} admin access, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )

        except Exception as e:
            await interaction.response.send_message(
                "Error while deleting this convo, try again",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            print("Error giving admin: ", str(e))

    @app_commands.command(name="kill", description="Kill this conversation")
    @app_commands.guilds(GUILD)
    async def kill(self, interaction: discord.Interaction):

        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
                "admins", None
            )

            can_kill = False

            if admins is None:
                can_kill = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
            else:
                can_kill = interaction.user.id in admins

            if not can_kill:
                await interaction.response.send_message(
                    "You must be admin of this conversation!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            removed = await remove_bot(self.bot.supabase, interaction.channel.id)
            if not removed:
                await interaction.response.send_message(
                    "Error while deleting this convo, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return
            del self.bot.running_bots[interaction.channel.id]
            await interaction.channel.delete()

        except Exception as e:
            await interaction.response.send_message(
                "Error while deleting this convo, try again",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            print(f"Cant kill conversation: {str(e)}")

    @app_commands.command(name="add", description="Add user to private chat")
    @app_commands.describe(user="User to add to this private chat")
    @app_commands.guilds(GUILD)
    async def add(self, interaction: discord.Interaction, user: discord.Member):

        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        if user == self.bot.user:
            await interaction.response.send_message(
                "Im already in every conversation :)",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
                "admins", None
            )

            am_admin = False

            if admins is None:
                am_admin = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
            else:
                am_admin = interaction.user.id in admins

            if not am_admin:
                await interaction.response.send_message(
                    "You must be admin of this conversation!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            guild = interaction.guild
            all_overwrites = interaction.channel.overwrites_for(guild.default_role)
            selected_user_overwrites = interaction.channel.overwrites_for(user)

            if all_overwrites.view_channel:  # chat is public
                await interaction.response.send_message(
                    "This conversation is public!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            if selected_user_overwrites.view_channel:
                await interaction.response.send_message(
                    "This user is already in the private conversation",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            user_overwrite = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, embed_links=True
            )

            await interaction.channel.set_permissions(
                user, overwrite=user_overwrite, reason="Added to private chat"
            )

            await interaction.response.send_message(
                f"{user.mention} has been added to the private conversation!",
                delete_after=DELETE_DELAY,
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Couldn't add {user.name} to private chat",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            print("Error adding user to private chat: ", str(e))
            return

    @app_commands.command(name="gpt", description="Change ai model used in chat")
    @app_commands.guilds(GUILD)
    async def gpt(self, interaction: discord.Interaction):

        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
                "admins", None
            )

            am_admin = False

            if admins is None:
                am_admin = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
            else:
                am_admin = interaction.user.id in admins

            if not am_admin:
                await interaction.response.send_message(
                    "You must be admin of this conversation!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            view = ModelView(
                models=["llama (default)", *self.bot.openrouter_models],
                channel_id=interaction.channel.id,
                bot=self.bot,
            )

            await interaction.response.send_message(
                "Select an AI model:",
                view=view,
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )

        except Exception as e:
            await interaction.response.send_message(
                "Couldnt change ai model",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            print("Error changing ai model: ", str(e))
            return

    @app_commands.command(name="kick", description="kick user from private chat")
    @app_commands.describe(user="User to add to this private chat")
    @app_commands.guilds(GUILD)
    async def kick(self, interaction: discord.Interaction, user: discord.Member):

        if interaction.channel.id not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        if user == self.bot.user:
            await interaction.response.send_message(
                "You cant kick me :)",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            admins = self.bot.running_bots.get(interaction.channel.id, {}).get(
                "admins", None
            )

            am_admin = False

            if admins is None:
                am_admin = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
            else:
                am_admin = interaction.user.id in admins

            if not am_admin:
                await interaction.response.send_message(
                    "You must be admin of this conversation!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            guild = interaction.guild
            all_overwrites = interaction.channel.overwrites_for(guild.default_role)
            selected_user_overwrites = interaction.channel.overwrites_for(user)

            if all_overwrites.view_channel:  # chat is public
                await interaction.response.send_message(
                    "This conversation is public!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            if not selected_user_overwrites.view_channel:
                await interaction.response.send_message(
                    "This user is not in the private conversation",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            user_overwrite = discord.PermissionOverwrite(
                view_channel=False, send_messages=False, embed_links=False
            )

            await interaction.channel.set_permissions(
                user, overwrite=user_overwrite, reason="Kicked from private chat"
            )

            await interaction.response.send_message(
                f"{user.mention} has been kicked from the private conversation!",
                delete_after=DELETE_DELAY,
            )

            await user.send(
                f"{interaction.user.mention} has kicked you from there private chat with {interaction.channel.name}!"
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Couldnt kick {user.name} to private chat",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            print("Error adding user to private chat: ", str(e))
            return

    @app_commands.command(name="talk", description="Create a new chat bot")
    @app_commands.describe(
        bot_name="Name of the bot", private="If the chat is private or public"
    )
    @app_commands.guilds(GUILD)
    async def talk(
        self,
        interaction: discord.Interaction,
        bot_name: str,
        private: Optional[bool],
    ):
        try:
            if interaction.channel.id != BOT_CREATION_CHANNEL:
                await interaction.response.send_message(
                    f"Must be used in {self.bot.get_channel(BOT_CREATION_CHANNEL).mention}!",
                    ephemeral=True,
                )
                return

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
                    name=bot_name, overwrites=overwrites, slowmode_delay=5
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

            self.bot.running_bots[new_channel.id] = {
                "admins": [interaction.user.id],
                "messages": [sys_message(bot_name)],
                "gpt": "llama",
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

    async def edit(self, interaction: discord.Interaction, message: discord.Message):
        if interaction.channel.id in self.bot.running_bots.keys():
            if message.author == self.bot.user:
                for i in range(
                    len(self.bot.running_bots[message.channel.id]["messages"])
                ):
                    index = (
                        len(self.bot.running_bots[message.channel.id]["messages"])
                        - i
                        - 1
                    )  # bottom up for better performance

                    if (
                        self.bot.running_bots[message.channel.id]["messages"][index][
                            "discord_message_id"
                        ]
                        == message.id
                        and self.bot.running_bots[message.channel.id]["messages"][
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
        if interaction.channel.id in self.bot.running_bots.keys():
            if message.author == self.bot.user:
                for i in range(
                    len(self.bot.running_bots[message.channel.id]["messages"])
                ):
                    index = (
                        len(self.bot.running_bots[message.channel.id]["messages"])
                        - i
                        - 1
                    )  # bottom up for better performance

                    if (
                        self.bot.running_bots[message.channel.id]["messages"][index][
                            "discord_message_id"
                        ]
                        == message.id
                        and self.bot.running_bots[message.channel.id]["messages"][
                            index
                        ]["role"]
                        == "assistant"
                    ):
                        new_messages = self.bot.running_bots[message.channel.id][
                            "messages"
                        ].copy()
                        new_messages.pop(index)

                        ok = await update_messages(
                            self.bot.supabase,
                            message.channel.id,
                            {"messages": new_messages},
                        )

                        if ok:
                            self.bot.running_bots[message.channel.id][
                                "messages"
                            ] = new_messages
                            await message.delete()
                            await interaction.response.send_message(
                                "delted ai message!", ephemeral=True, delete_after=5
                            )

                        await asyncio.sleep(0.3)
                        return

            await interaction.response.send_message(
                "Couldn't delete the message", ephemeral=True, delete_after=10
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
