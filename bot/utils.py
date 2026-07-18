def sys_message(bot_name: str):

    return {
        "role": "system",
        "content": f"You are the infamous character {bot_name}, some people are talking to you, act and behave like {bot_name} would, answer in short concice real life like answers, dont sound robotic, follow {bot_name}'s personality and mindset in every respons and action, in need of mentioning a certain user include there name in the response there name will be between () in every message they send, when mentioning them use the name inside the parentheses without the actual parenthesis, you can use markdown formating for feelings, actions etc...",
    }


async def _grab_chat_history(bot, c, limit=20):

    old = []

    async for message in c.history(limit=limit):

        old.insert(
            0,
            {
                "role": "assistant" if message.author == bot.user else "user",
                "content": (
                    f"({message.author.name}) {message.content}"
                    if ":" not in message.content
                    else message.content.split(":")[1].strip()
                ),
            },
        )

    return old[1:]
