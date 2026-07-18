import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.groq_api import groq_client
import os

from bot.utils import _grab_chat_history, sys_message
from bot.consts import BOTS_CATEGORY_ID, GUILD, DESCRITPTION

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", description=DESCRITPTION, intents=intents)

running_bots = {}


@bot.event
async def on_ready():

    print(f"We have logged in as {bot.user}")

    bot_category = bot.get_channel(BOTS_CATEGORY_ID)

    for c in bot_category.text_channels:

        old = await _grab_chat_history(c)

        running_bots[c.id] = {
            "bot_name": c.name,
            "messages": [sys_message(c.name), *old],
        }

    await bot.tree.sync(guild=GUILD)


@bot.event
async def on_message(message: discord.Message):

    if message.author == bot.user:
        return

    if message.channel.id in running_bots:

        msg = message.content

        new_msgs = [
            *running_bots[message.channel.id]["messages"],
            {"role": "user", "content": f"({message.author.name}) {msg}"},
        ]

        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=new_msgs,
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )

        response = completion.choices[0].message.content

        new_msgs = [*new_msgs, {"role": "assistant", "content": response}]

        running_bots[message.channel.id]["messages"] = new_msgs

        await message.channel.send(
            f"{running_bots[message.channel.id]['bot_name']}: {response}"
        )


async def run_bot():
    async with bot:
        await bot.load_extension("bot.commands")
        await bot.start(os.getenv("DISCORD_TOKEN"))
