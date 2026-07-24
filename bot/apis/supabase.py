import os
from typing import Literal

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
    except Exception as e:
        print("Error updating messages by channel id: ", str(e))
        return False


async def get_messages(supabase: AsyncClient, _id: int) -> list[Message] | None:
    res = await supabase.from_("chats").select("messages").eq("id", _id).execute()

    try:
        return res.model_dump()["data"][0]["messages"]["messages"]
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
        print("Error checking if user is admin: ", str(e))
        return False


async def get_admins(supabase: AsyncClient, _id: int) -> list[str]:
    res = await supabase.from_("chats").select("admins").eq("id", _id).execute()
    dict_ = res.model_dump()

    try:
        return dict_["data"][0]["admins"]
    except Exception as e:
        print("Error checking if user is admin: ", str(e))
        return []


async def remove_bot(supabase: AsyncClient, _id: int) -> bool:
    try:
        _ = await supabase.from_("chats").delete().eq("id", _id).execute()
        return True
    except Exception as e:
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
    except Exception as e:
        print("Error giving admin: ", str(e))
        return False


async def get_bots_with_ids(supabase: AsyncClient, ids: list[int]) -> list[int]:
    try:
        res = await supabase.from_("chats").select("id").in_("id", ids).execute()
        json = res.model_dump()

        return [x["id"] for x in json["data"]]
    except Exception as e:
        print("Error getting bots by ids: ", str(e))
        return []


async def get_bot(supabase: AsyncClient, _id: int) -> DBBot | None:

    res = await supabase.from_("chats").select("id").eq("id", _id).execute()
    try:
        return res.model_dump()["data"][0]
    except (KeyError, IndexError) as e:
        print(f"No such bot: {str(e)}")
        return None


async def get_chats(supabase: AsyncClient) -> list[DBBot] | None:

    res = await supabase.from_("chats").select("*").execute()
    try:
        return res.model_dump()["data"]
    except (KeyError, IndexError) as e:
        print(f"No such bot: {str(e)}")
        return None


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
                }
            )
            .execute()
        )
        return True
    except Exception as e:
        print("Error creating character: ", str(e))
        return False


async def get_character(supabase: AsyncClient, _id: str) -> Character | None:
    try:
        res = await supabase.from_("characters").select("*").eq("id", _id).execute()
        json = res.model_dump()
        return json["data"][0]

    except Exception as e:
        print("Error retreiving character: ", str(e))
        return None


async def remove_character(supabase: AsyncClient, _id: str) -> bool:
    try:
        res = await supabase.from_("characters").delete().eq("id", _id).execute()

        return True
    except Exception as e:
        print("Error retreiving character: ", str(e))
        return False


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

    except Exception as e:
        print("Error retreiving character: ", str(e))
        return None


async def get_characters_ids(
    supabase: AsyncClient,
) -> list[dict[Literal["id"], str]] | None:
    try:
        res = await supabase.from_("characters").select("id").execute()
        json = res.model_dump()

        return json["data"]
    except Exception as e:
        print("Error retreiving characters message ids: ", str(e))
        return None
