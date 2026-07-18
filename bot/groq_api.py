from dotenv import load_dotenv
import os
import groq

load_dotenv()


def create_groq():
    return groq.AsyncGroq(api_key=os.getenv("GROQ_KEY"))


async def send_msg_to_bot(groq_client: groq._client.AsyncGroq, messages: [dict]) -> str:
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
    except:
        return None
