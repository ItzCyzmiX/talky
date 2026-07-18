import discord
from discord.ext import commands
import os
import groq
from dotenv import load_dotenv
from requests import request

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.messages = True
intents.guilds = True

DESCRITPTION = """Bot to talk to ai characters!"""

client = commands.Bot(command_prefix="!", description=DESCRITPTION, intents=intents)
groq_client = groq.Groq(api_key=os.getenv("GROQ_KEY"))

running_bots = {}

BOTS_CATEGORY_ID = 1527758935916937409
BOT_CREATION_CHANNEL = 1527794645336199308


def sys_message(bot_name: str):
    return {
        "role": "system",
        "content": f"You are the infamous character {bot_name}, some people are talking to you, act and behave like {bot_name} would, answer in short concice real life like answers, dont sound robotic, follow {bot_name}'s personality and mindset in every respons and action, in need of mentioning a certain user include there name in the response there name will be between () in every message they send, when mentioning them use the name inside the parentheses without the actual parenthesis, you can use markdown formating for feelings, actions etc...",
    }


async def _grab_chat_history(c, limit=20):
    old = []
    async for message in c.history(limit=limit):
        old.insert(
            0,
            {
                "role": "assistant" if message.author == client.user else "user",
                "content": (
                    f"({message.author.name}) {message.content}"
                    if ":" not in message.content
                    else message.content.split(":")[1].strip()
                ),
            },
        )
    return old[1:]


@client.command(description="General chat bot help")
async def help(ctx: discord.Context):
    if ctx.channel.id != BOT_CREATION_CHANNEL:
        return
    await ctx.reply(
        "\n- ```!talk <bot_name>``` (starts a conversation with the bot) \n- ```!add <new_bot_name>``` (adds a new bot to the conversation **NOT IMPLEMENTED YET**) \n- ```!kill``` (deletes the conversation in the channel)\n",
        delete_after=3,
    )


@client.command(description="Create a new chat bot")
async def talk(ctx: discord.Context, *args: str):
    if ctx.channel.id != BOT_CREATION_CHANNEL:
        return

    bot_name = " ".join(args).strip()
    bot_category = client.get_channel(BOTS_CATEGORY_ID)

    for c in bot_category.text_channels:
        if c.name == bot_name:
            await ctx.reply(
                f"Character channel already created! {c.mention} (kill it with !kill to create a new chat)"
            )
            return

    new_channel = await bot_category.create_text_channel(name=bot_name)

    running_bots[new_channel.id] = {
        "bot_name": bot_name,
        "messages": [sys_message(bot_name)],
    }

    res = request(
        "GET",
        f"https://api.giphy.com/v1/gifs/search?api_key={os.getenv('GIPHY_KEY')}&q={bot_name}",
    )

    json = res.json()

    gifs = json.get("data", [])

    gif_url = ""

    if len(gifs) != 0:
        try:
            gif_url = gifs[0]["images"]["original"]["url"]
        except Exception as e:
            print(f"No gif was found: {str(e)}")

    if gif_url:
        await new_channel.send(f"{gif_url}")

    await new_channel.send(f"{ctx.author.mention} started a convo with {bot_name}")

    await ctx.reply(
        f"Go chat with {bot_name} in {new_channel.mention}!", delete_after=3
    )
    await ctx.message.delete(delay=3)


@client.event
async def on_ready():

    print(f"We have logged in as {client.user}")

    bot_category = client.get_channel(BOTS_CATEGORY_ID)
    for c in bot_category.text_channels:

        old = await _grab_chat_history(c)

        running_bots[c.id] = {
            "bot_name": c.name,
            "messages": [sys_message(c.name), *old],
        }


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.channel.id in running_bots:

        if message.content.startswith("!"):
            cmd = message.content.replace("!", "")
            if cmd == "kill":
                await message.channel.delete()
                del running_bots[message.channel.id]
            else:
                await message.delete()

            return

        msg = message.content

        new_msgs = [
            *running_bots[message.channel.id]["messages"],
            {"role": "user", "content": f"({message.author.name}) {msg}"},
        ]

        completion = groq_client.chat.completions.create(
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


client.run(os.getenv("DISCORD_TOKEN"))
