import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import BOT_CREATION_CHANNEL, GUILD, BOTS_CATEGORY_ID, DELETE_DELAY
from bot.bot import Talky
from bot.utils import sys_message, fetch_gif
from bot.supabase import new_bot, remove_bot, is_admin, add_admin

import asyncio


class Commands(commands.Cog):
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
            "\n- ```!talk <bot_name>``` (starts a conversation with the bot) \n- ```!add <new_bot_name>``` (adds a new bot to the conversation **NOT IMPLEMENTED YET**) \n- ```!kill``` (deletes the conversation in the channel)\n",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )

    @app_commands.command(name="status", description="Get if you are admin or not")
    @app_commands.guilds(GUILD)
    async def status(self, interaction: discord.Interaction):
        if interaction.channel.id in self.bot.running_bots:
            am_admin = await is_admin(
                self.bot.supabase, interaction.channel.id, interaction.user.id
            )
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
        if interaction.channel.id in self.bot.running_bots:

            try:
                can_give_admin = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )
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

                ok = await add_admin(
                    self.bot.supabase, interaction.channel.id, target.id
                )

                if ok:
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

        if interaction.channel.id in self.bot.running_bots:
            try:
                can_kill = await is_admin(
                    self.bot.supabase, interaction.channel.id, interaction.user.id
                )

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
                self.bot.running_bots.remove(interaction.channel.id)
                await interaction.channel.delete()

            except Exception as e:
                await interaction.response.send_message(
                    "Error while deleting this convo, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                print(f"Cant kill conversation: {str(e)}")
        else:
            await interaction.response.send_message(
                "Must be used within a conversation channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )

    @app_commands.command(name="talk", description="Create a new chat bot")
    @app_commands.guilds(GUILD)
    async def talk(self, interaction: discord.Interaction, bot_name: str):
        try:
            if interaction.channel.id != BOT_CREATION_CHANNEL:
                await interaction.response.send_message(
                    f"Must be used in {self.bot.get_channel(BOT_CREATION_CHANNEL).mention}!",
                    ephemeral=True,
                )
                return

            bot_category = self.bot.get_channel(BOTS_CATEGORY_ID)

            for c in bot_category.text_channels:
                if c.name == bot_name:
                    await interaction.response.send_message(
                        f"Character channel already created! {c.mention} (kill it with !kill to create a new chat)",
                        ephemeral=True,
                    )
                    return

            new_channel = await bot_category.create_text_channel(name=bot_name)

            while not new_channel:
                asyncio.sleep(0.4)

            self.bot.running_bots.append(new_channel.id)

            ok = await new_bot(
                self.bot.supabase,
                new_channel.id,
                bot_name,
                [interaction.user.id],
                {
                    "messages": [sys_message(bot_name)],
                },
            )

            if not ok:
                await interaction.response.send_message(
                    "Couldnt create the chat bot, try again",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )
                return

            await new_channel.send(
                f"{interaction.user.mention} has started a conversation with {bot_name}!"
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
