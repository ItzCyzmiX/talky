from dotenv import load_dotenv
import os
from openrouter import OpenRouter

load_dotenv()


async def send_msg_to_bot(messages: [dict]) -> str:
    try:
        async with OpenRouter(api_key=os.getenv("OPENROUTER_KEY")) as client:
            res = await client.chat.send_async(
                model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                messages=messages,
            )

            return res.choices[0].message.content
    except:
        return None
