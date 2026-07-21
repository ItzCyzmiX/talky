import os
import aiohttp
import re

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
    content = re.sub(r"@(everyone|here)", r"@\u200b\1", content)
    content = re.sub(r"<@&?!?\d+>", "`@mention`", content)
    content = re.sub(r"[\u200B-\u200D\uFEFF\u2060]", "", content)
    return content.strip()
