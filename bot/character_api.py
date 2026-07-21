import os

from openrouter import OpenRouter
from groq import AsyncGroq

from dotenv import load_dotenv
load_dotenv()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

VISION_MODEL = "qwen/qwen3.6-27b"


async def send_msg_to_bot(messages: list[dict], model="llama") -> str | None:

    filtred_msgs = list(
        map(lambda x: {"role": x["role"], "content": x["content"]}, messages)
    )

    if model == "vision":
        return await _use_groq(filtred_msgs, VISION_MODEL)
    elif model == "llama":
        return await _use_groq(filtred_msgs)
    else:
        return await _use_openrouter(filtred_msgs, model)


async def _get_openrouter_models() -> list:
    try:
        async with OpenRouter(api_key=os.getenv("OPENROUTER_KEY")) as client:
            res = await client.models.list_async(
                min_price=0,
                max_price=0,
                output_modalities="text",
                input_modalities="text",
                limit=24,
            )

            return list(map(lambda model: model.id, res.result.data))[:24]

    except Exception as e:
        print(f"Openrouter errored out ({str(e)})")
        return []


async def _use_openrouter(
    messages: list[dict], model: str = "poolside/laguna-xs-2.1:free"
) -> str | None:
    try:
        async with OpenRouter(api_key=os.getenv("OPENROUTER_KEY")) as client:
            res = await client.chat.send_async(
                model=model.lower(),
                messages=messages,
            )

            return res.choices[0].message.content
    except Exception as e:
        print(f"Openrouter errored out ({str(e)}), using groq...")
        return None


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
