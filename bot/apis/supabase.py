import os
from typing import Literal

import aiofiles
import aiofiles.os
import aiohttp
from postgrest.exceptions import APIError
from supabase import AsyncClient, acreate_client

from bot.types import Character, DBBot, Message


async def create_supabase() -> AsyncClient | None:
    if os.getenv("SUPABASE_URL") is None or os.getenv("SUPABASE_SECRET_KEY") is None:
        return None

    supabase: AsyncClient = await acreate_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY")
    )
    return supabase


async def update_messages(supabase: AsyncClient, _id: int, new_msgs: dict) -> bool:
    try:
        _ = (
            await supabase.from_("chats")
            .update({"messages": new_msgs})
            .eq("id", _id)
            .execute()
        )
        return True
    except APIError as e:
        print("Error updating messages by channel id: ", str(e))
        return False


async def get_messages(supabase: AsyncClient, _id: int) -> list[Message] | None:

    try:
        res = await supabase.from_("chats").select("messages").eq("id", _id).execute()
        return res.model_dump()["data"][0]["messages"]["messages"]
    except APIError as e:
        print("Error getting messages by channel id: ", str(e))
        return None


async def new_bot(
    supabase: AsyncClient,
    _id: int,
    bot_name: str,
    admins: list[int],
    messages: dict[Literal["messages"], list[Message]],
    custom_char_id: str | None = None,
) -> bool:
    try:
        _ = (
            await supabase.from_("chats")
            .upsert(
                {
                    "id": _id,
                    "admins": admins,
                    "bot_name": bot_name,
                    "messages": messages,
                    "custom_character_id": custom_char_id,
                }
            )
            .execute()
        )
        return True
    except APIError as e:
        print("Error creating bot: ", str(e))
        return False


async def is_admin(supabase: AsyncClient, _id: int, user_id: int) -> bool:

    res = (
        await supabase.from_("chats")
        .select("admins")
        .eq("id", _id)
        .contains("admins", [str(user_id)])
        .execute()
    )
    dict_ = res.model_dump()

    try:
        return str(user_id) in dict_["data"][0]["admins"]
    except APIError as e:
        print("Error checking if user is admin: ", str(e))
        return False


async def get_admins(supabase: AsyncClient, _id: int) -> list[str]:
    res = await supabase.from_("chats").select("admins").eq("id", _id).execute()
    dict_ = res.model_dump()

    try:
        return dict_["data"][0]["admins"]
    except APIError as e:
        print("Error checking if user is admin: ", str(e))
        return []


async def remove_bot(supabase: AsyncClient, _id: int) -> bool:
    try:
        _ = await supabase.from_("chats").delete().eq("id", _id).execute()
        return True
    except APIError as e:
        print("Error removing bot by id: ", str(e))
        return False


async def add_admin(supabase: AsyncClient, _id: int, user_id: int) -> bool:
    try:
        res = await supabase.from_("chats").select("admins").eq("id", _id).execute()
        admins = [*res.model_dump()["data"][0]["admins"], str(user_id)]
        _ = (
            await supabase.from_("chats")
            .update({"admins": admins})
            .eq("id", _id)
            .execute()
        )
        return True
    except APIError as e:
        print("Error giving admin: ", str(e))
        return False


async def get_bots_with_ids(supabase: AsyncClient, ids: list[int]) -> list[int]:
    try:
        res = await supabase.from_("chats").select("id").in_("id", ids).execute()
        json = res.model_dump()

        return [x["id"] for x in json["data"]]
    except APIError as e:
        print("Error getting bots by ids: ", str(e))
        return []


async def get_bot(supabase: AsyncClient, _id: int) -> DBBot | None:

    try:
        res = await supabase.from_("chats").select("id").eq("id", _id).execute()
        return res.model_dump()["data"][0]

    except (KeyError, IndexError, APIError) as e:
        print(f"No such bot: {str(e)}")
        return None


async def get_chats(supabase: AsyncClient) -> list[DBBot] | None:

    res = await supabase.from_("chats").select("*").execute()
    try:
        return res.model_dump()["data"]
    except (KeyError, IndexError) as e:
        print("No bots found: ", str(e))
        return None


async def refresh_character_chats(
    supabase: AsyncClient, _id: str, new_char: Character
) -> bool:

    try:
        from bot.utils import character_sys_message

        res = (
            await supabase.from_("chats")
            .select("messages, id")
            .eq("custom_character_id", _id)
            .execute()
        )

        chats = res.model_dump()["data"]

        for chat in chats:
            chat["messages"][0] = character_sys_message(new_char)

            _ = (
                await supabase.from_("chats")
                .update(
                    {
                        "bot_name": new_char["name"],
                        "messages": chat["messages"],
                    }
                )
                .eq("custom_character_id", _id)
                .execute()
            )

        return True

    except (KeyError, IndexError, APIError) as e:
        print("No such character, or no chats assigned to it: ", str(e))
        return False


async def new_character(
    supabase: AsyncClient,
    _id: str,
    message_id: int,
    creator_id: int,
    name: str,
    bio: str,
    personality: str,
    relationship: str,
    start_message: str,
    forkable: bool,
) -> bool:
    try:
        _ = (
            await supabase.from_("characters")
            .upsert(
                {
                    "id": _id,
                    "message_id": message_id,
                    "creator_id": creator_id,
                    "name": name,
                    "bio": bio,
                    "personality": personality,
                    "relationship": relationship,
                    "start_message": start_message,
                    "forkable": forkable,
                }
            )
            .execute()
        )
        return True
    except APIError as e:
        print("Error creating character: ", str(e))
        return False


async def get_character(supabase: AsyncClient, _id: str) -> Character | None:
    try:
        res = await supabase.from_("characters").select("*").eq("id", _id).execute()
        json = res.model_dump()
        return json["data"][0]

    except (APIError, IndexError) as e:
        print("Error retreiving character: ", str(e))
        return None


async def remove_character(supabase: AsyncClient, _id: str) -> bool:
    try:
        await supabase.from_("characters").delete().eq("id", _id).execute()

        return True
    except APIError as e:
        print("Error retreiving character: ", str(e))
        return False


async def upload_character_profile(
    supabase: AsyncClient, url: str, character_id: str
) -> str | None:
    try:
        async with aiohttp.ClientSession() as session, session.get(url) as res:
            if res.status != 200:
                return None

            await aiofiles.os.makedirs("temp/profiles", exist_ok=True)

            content = await res.read()

            res = await supabase.storage.from_("characters").upload(
                file=content,
                path=f"profiles/{character_id}.png",
                file_options={
                    "content-type": "image/png",
                    "cache-control": "3600",
                    "x-upsert": "true",
                },
            )

            public_url = await supabase.storage.from_("characters").get_public_url(
                f"profiles/{character_id}.png"
            )

            return public_url

    except APIError as e:
        print("error getting pulbic link: ", str(e))
        return None


async def delete_character_profile(supabase: AsyncClient, character_id: str):
    try:
        await supabase.storage.from_("characters").remove(
            paths=[f"profiles/{character_id}.png"]
        )
    except APIError as e:
        print("error deleting character profile: ", str(e))


async def get_character_owner(supabase: AsyncClient, _id: str) -> int | None:
    try:
        res = (
            await supabase.from_("characters")
            .select("creator_id")
            .eq("id", _id)
            .execute()
        )
        json = res.model_dump()

        return int(json["data"][0]["creator_id"])

    except (APIError, KeyError, IndexError) as e:
        print("Error retreiving character: ", str(e))
        return None


async def get_characters(
    supabase: AsyncClient,
) -> list[Character] | None:
    try:
        res = await supabase.from_("characters").select("*").execute()
        json = res.model_dump()

        return json["data"]
    except APIError as e:
        print("Error retreiving characters message ids: ", str(e))
        return None
