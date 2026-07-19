from dotenv import load_dotenv
import os
from openrouter import OpenRouter
from groq import AsyncGroq

load_dotenv()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


async def send_msg_to_bot(messages: list[dict], model="llama") -> str | None:

    if model == "llama":
        return await _use_groq(messages)
    else:
        return await _use_openrouter(messages, model)


async def _get_openrouter_models() -> list:
    try:
        async with OpenRouter(api_key=os.getenv("OPENROUTER_KEY")) as client:
            res = await client.models.list_async(
                min_price=0,
                max_price=0,
                output_modalities="text",
                input_modalities="text",
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


async def _use_groq(messages: list[dict]) -> str | None:
    global groq_client
    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )

        return completion.choices[0].message.content

    except Exception as groq_e:
        print(f"Groq errored out ({str(groq_e)})")
        return None
