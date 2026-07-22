from typing import TypedDict, Literal


class Message(TypedDict):
    discord_message_id: int
    content: str
    role: Literal["assistant", "user", "system"]


class RunningBot(TypedDict):
    admins: list[str]
    messages: list[Message]


type RunningBots = dict[str, RunningBot]


class DBBot(TypedDict):
    id: int
    admins: list[str]
    messages: list[Message]
