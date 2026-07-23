from typing import TypedDict, Literal
import asyncio


class Message(TypedDict):
    discord_message_id: int  # all system messages have a discrord_message_id of -1 for easy access in case we want to alter it mid convo
    content: str
    role: Literal["assistant", "user", "system"]


class RunningBot(TypedDict):
    admins: list[str]
    messages: list[Message]
    lock: asyncio.Lock


type RunningBots = dict[str, RunningBot]


class DBBot(TypedDict):
    id: int
    admins: list[str]
    messages: list[Message]


class Character(TypedDict):
    _id: str
    creator_id: int
    message_id: str
    name: str
    bio: str
    personality: str
    relationship: str
    start_message: str
