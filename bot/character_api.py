from dotenv import load_dotenv
import os
from openrouter import OpenRouter
from groq import AsyncGroq

load_dotenv()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API"))

starting_router = "Openrouter"


async def send_msg_to_bot(messages: [dict]) -> str:
    global groq_client, starting_router

    print(f"Using {starting_router}")

    if starting_router == "Openrouter":
        or_ok = await _use_openrouter(messages)
        if or_ok is not None:
            return or_ok
        else:
            gk_ok = await _use_groq(messages)
            if gk_ok is not None:
                starting_router = "Groq"
                return gk_ok
    else:
        gk_ok = await _use_groq(messages)
        if gk_ok is not None:
            return gk_ok
        else:
            or_ok = await _use_openrouter(messages)
            if or_ok is not None:
                starting_router = "Openrouter"
                return or_ok

    return False


async def _use_openrouter(messages: [dict]):
    try:
        async with OpenRouter(api_key=os.getenv("OPENROUTER_KEY")) as client:
            res = await client.chat.send_async(
                model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                messages=messages,
            )

            return res.choices[0].message.content
    except Exception as e:
        print(f"Openrouter errored out ({str(e)}), using groq...")
        return None


async def _use_groq(messages: [dict]):
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
        return False
