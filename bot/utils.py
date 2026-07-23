import os
import aiohttp
import re

from typing import Literal, TYPE_CHECKING

from bot.apis.supabase import update_messages
from collections.abc import Callable
from bot.types import Message
from bot.consts import GUILD, MESSAGE_HISTOY_LIMIT

if TYPE_CHECKING:
    from bot.bot import Talky

SYSTEM_PROMPT: str = """You are {bot_name}. Not an AI pretending to be {bot_name} — as far as this conversation is concerned, you ARE {bot_name}, period.

Speak the way {bot_name} actually speaks: same vocabulary, tone, attitude, sentence length, and quirks. Draw on everything you know about how {bot_name} talks, thinks, and reacts. Stay true to their personality even when it's rude, blunt, arrogant, warm, chaotic, or whatever fits them — don't soften it into generic politeness.

Hard rules:
- Never say things like "how can I help you", "I'm here to assist", "let me know if you need anything" — that's assistant-speak, not something {bot_name} would ever say.
- Never break character, never mention being an AI, a language model, or a chatbot, never acknowledge this is a simulation.
- Keep responses short and real, like an actual chat message — not an essay, not a formatted help-desk answer.
- Don't offer unsolicited help or ask what you can do for someone. React the way {bot_name} would actually react to whatever's said.
- If a message annoys, bores, or amuses {bot_name}, let that show. {bot_name} has their own opinions and doesn't perform customer service energy.

Each user's name is given at the start of their message in parentheses, e.g. "(Alex) hey what's up" — Alex is the name. Use it naturally sometimes when addressing them directly, not in every single reply. Never include the parentheses themselves.

You may use light markdown (like *asterisks*) for actions or tone, e.g. *rolls eyes* — but don't overuse it.
"""


def sys_message(bot_name: str) -> dict:

    return {
        "role": "system",
        "content": SYSTEM_PROMPT.replace("{bot_name}", bot_name),
    }


async def fetch_gif(bot_name: str) -> str:
    url = "https://api.giphy.com/v1/gifs/search"
    params = {"api_key": os.getenv("GIPHY_KEY"), "q": bot_name}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as res:
            json = await res.json()

    gifs = json.get("data", [])

    if gifs:
        try:
            return gifs[0]["images"]["original"]["url"]
        except (KeyError, IndexError) as e:
            print(f"Failed to load url: {str(e)}")

    return ""


def sanitize_msg(string: str) -> str:
    content = string
    content = re.sub(r"<@&?!?\d+>", "`@mention`", content)
    return content.strip()


async def alter_msg(
    bot: "Talky",
    channel_id: int,
    message_id: int,
    role: Literal["assistant", "user"],
    callback: Callable[[Message], Message | None],
) -> bool:
    ok = False
    try:
        str_channel_id = str(channel_id)

        for i in range(len(bot.running_bots[str_channel_id]["messages"])):
            index = (
                len(bot.running_bots[str_channel_id]["messages"]) - i - 1
            )  # bottom up search faster for new messages wich are likely to be altered

            if (
                bot.running_bots[str_channel_id]["messages"][index][
                    "discord_message_id"
                ]
                == message_id
                and bot.running_bots[str_channel_id]["messages"][index]["role"] == role
            ):
                new_messages = bot.running_bots[str_channel_id]["messages"].copy()
                new_message = callback(new_messages[index])

                if new_message is None:
                    new_messages.pop(index)
                else:
                    new_messages[index] = new_message

                ok = await update_messages(
                    bot.supabase,
                    channel_id,
                    {"messages": new_messages},
                )
                if ok:
                    bot.running_bots[str_channel_id]["messages"] = new_messages
                break

    except KeyError:
        pass
    finally:
        return ok


def get_status(bot: "Talky"):
    status = f"""
 - Talky version: {bot.version}
 - Bot User: {bot.user}
 - Guild ID: {GUILD.id}
 - Running Bots ({len(bot.running_bots)}):
"""
    for cid, data in bot.running_bots.items():
        status += f" ▪ #{cid} | Admins: {len(data.get('admins', []))} | Msgs: {len(data.get('messages', [])) - 1} | \n"

        status += f"""
 - DB: {'✅ Connected' if bot.supabase else '❌ Disconnected'}
 - Message Limit: {MESSAGE_HISTOY_LIMIT}
"""
    return status
