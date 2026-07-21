import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import GUILD, DELETE_DELAY
from bot.bot import Talky
from bot.supabase import (
    remove_bot,
    is_admin,
    add_admin,
    change_bot_gpt,
)

from pprint import pprint


class AdminCommands(commands.Cog):
    def __init__(self, bot: Talky):
        self.bot = bot


    @app_commands.command(name="admin", description="Gives admin to selected users")
    @app_commands.describe(target="The user you want to give admin to")
    @app_commands.guilds(GUILD)
    async def admin(self, interaction: discord.Interaction, target: discord.Member):

        if str(interaction.channel.id) not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        try:
            can_give_admin = await validate_admin(bot=self.bot, interaction=interaction)

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
                self.bot.running_bots[str(interaction.channel.id)]["admins"] = [
                    *self.bot.running_bots[str(interaction.channel.id)]["admins"],
                    str(target.id),
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

        if str(interaction.channel.id) not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            can_kill = await validate_admin(bot=self.bot, interaction=interaction)

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
            del self.bot.running_bots[str(interaction.channel.id)]
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
        
        if str(interaction.channel.id) not in self.bot.running_bots.keys():
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
            am_admin = await validate_admin(bot=self.bot, interaction=interaction)

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

        if str(interaction.channel.id) not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return
        try:
            am_admin = await validate_admin(bot=self.bot, interaction=interaction)

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

        if str(interaction.channel.id) not in self.bot.running_bots.keys():
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
            
            am_admin = await validate_admin(bot=self.bot, interaction=interaction)

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

    @app_commands.command(name="private", description="Make this chat private")
    @app_commands.guilds(GUILD)
    async def private(self, interaction: discord.Interaction):
        
        if str(interaction.channel.id) not in self.bot.running_bots.keys():
            await interaction.response.send_message(
                "Use this in a chat bot channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        am_admin = await validate_admin(bot=self.bot, interaction=interaction)

        if not am_admin:
            await interaction.response.send_message(
                "You must be admin of this conversation!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        guild = interaction.guild
        all_overwrites = interaction.channel.overwrites_for(guild.default_role)
        user_overwrites = interaction.channel.overwrites_for(interaction.user)
        
        all_overwrites.view_channel = False
        all_overwrites.send_messages = False
        
        user_overwrites.view_channel = True 
        user_overwrites.send_messages = True


        await interaction.channel.set_permissions(
            target=guild.default_role, overwrite=all_overwrites
        )
        await interaction.channel.set_permissions(
            target=interaction.user, overwrite=user_overwrites
        )
        await interaction.channel.set_permissions(
            target=guild.me, overwrite=user_overwrites
        )

        await interaction.response.send_message(
            "This chat is now private!", 
            ephemeral=True, 
            delete_after=10
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

        self.bot.running_bots[str(self._channel_id)]["gpt"] = chosen_model

        await interaction.response.send_message(
            f"This chat will now use {chosen_model}, in case of any error it will fall back to llama",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


class ModelView(discord.ui.View):
    def __init__(self, models: list[str], channel_id, bot):
        super().__init__(timeout=180)

        self.add_item(ModelSelect(ai_models=models, channel_id=channel_id, bot=bot))

async def validate_admin(bot: Talky, interaction: discord.Interaction) -> bool:
    admins = bot.running_bots.get(str(interaction.channel.id), {}).get(
        "admins", None
    )

    pprint(str(interaction.user.id) in admins)

    if admins is None:
        am_admin = await is_admin(
            bot.supabase, interaction.channel.id, interaction.user.id
        )
    else:
        am_admin = str(interaction.user.id) in admins
    
    return am_admin