import discord
from discord import app_commands
from discord.ext import commands

from bot.consts import BOT_CREATION_CHANNEL, GUILD, BOTS_CATEGORY_ID, DELETE_DELAY
from bot.bot import running_bots
from bot.utils import sys_message, fetch_gif


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
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

    @app_commands.command(name="kill", description="Kill this conversation")
    @app_commands.guilds(GUILD)
    async def kill(self, interaction: discord.Interaction):

        if interaction.channel.id in running_bots:
            del running_bots[interaction.channel.id]
            await interaction.channel.delete()
        else:
            await interaction.response.send_message(
                "Must be used within a conversation channel!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )

    @app_commands.command(name="talk", description="Create a new chat bot")
    @app_commands.guilds(GUILD)
    async def talk(self, interaction: discord.Interaction, bot_name: str):

        if interaction.channel.id != BOT_CREATION_CHANNEL:
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

        running_bots[new_channel.id] = {
            "bot_name": bot_name,
            "messages": [sys_message(bot_name)],
        }

        gif_url = fetch_gif(bot_name)

        if gif_url:
            await new_channel.send(f"{gif_url}")

        await interaction.response.send_message(
            f"Go chat with {bot_name} in {new_channel.mention}!",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
