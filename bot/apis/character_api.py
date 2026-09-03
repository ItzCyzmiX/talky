import os
from typing import Literal

from dotenv import load_dotenv
from groq import AsyncGroq, RateLimitError
from bot.types import RateLimit

load_dotenv()

VISION_MODEL = "qwen/qwen3.8-27b"
DEFAULT_MODEL = "qwen/qwen3.8-27b"  # since qwen3.6-27b has been discomisioned by Groq


async def send_msg_to_bot(
    messages: list[dict], api_key: str, model: Literal["llama", "vision"] = "llama"
) -> str | RateLimit | None:

    filtred_msgs = [{"role": x["role"], "content": x["content"]} for x in messages]

    if model == "vision":
        return await _use_groq(filtred_msgs, api_key, VISION_MODEL)

    return await _use_groq(filtred_msgs, api_key)


async def _use_groq(
    messages: list[dict], api_key: str, model: str = DEFAULT_MODEL
) -> str | RateLimit | None:

    try:
        groq_client = AsyncGroq(api_key=api_key)

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

        # completion.usage.total_tokens

        return completion.choices[0].message.content

    except RateLimitError as e:
        return {"retry_after": 0}

    except Exception as e:
        print("Groq error:", e)
        return None
