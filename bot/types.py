from typing import TypedDict, Literal
import asyncio


class Message(TypedDict):
    discord_message_id: int
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
