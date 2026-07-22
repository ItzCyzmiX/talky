from typing import Literal
import os
from groq import AsyncGroq

from dotenv import load_dotenv

load_dotenv()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

VISION_MODEL = "qwen/qwen3.6-27b"


async def send_msg_to_bot(
    messages: list[dict], model: Literal["llama", "vision"] = "llama"
) -> str | None:

    filtred_msgs = list(
        map(lambda x: {"role": x["role"], "content": x["content"]}, messages)
    )

    if model == "vision":
        return await _use_groq(filtred_msgs, VISION_MODEL)

    return await _use_groq(filtred_msgs)


async def _use_groq(
    messages: list[dict], model: str = "llama-3.3-70b-versatile"
) -> str | None:
    global groq_client

    try:

        params = {
            "model": model,
            "messages": messages,
            "temperature": 1,
            "max_completion_tokens": 2048,
            "top_p": 1,
            "stream": False,
            "stop": None,
        }

        if model == VISION_MODEL:
            params["reasoning_format"] = "hidden"

        completion = await groq_client.chat.completions.create(**params)

        return completion.choices[0].message.content

    except Exception as groq_e:
        print(f"Groq errored out ({str(groq_e)})")
        return None
