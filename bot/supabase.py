from supabase import acreate_client, AsyncClient
import os
import asyncio
from pprint import pprint


async def create_supabase():
    supabase: AsyncClient = await acreate_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY")
    )
    return supabase


async def update_messages(supabase: AsyncClient, id: int, new_msgs: dict):
    try:
        _ = (
            await supabase.from_("chats")
            .update({"messages": new_msgs})
            .eq("id", id)
            .execute()
        )
        return True
    except:
        return False


async def get_messages(supabase: AsyncClient, id: int):
    res = await supabase.from_("chats").select("messages").eq("id", id).execute()

    try:
        return res.dict()["data"][0]["messages"]["messages"]
    except:
        return None


async def new_bot(
    supabase: AsyncClient, id: int, bot_name: str, admins: [int], messages: dict
):
    try:
        _ = (
            await supabase.from_("chats")
            .upsert(
                {"id": id, "admins": admins, "bot_name": bot_name, "messages": messages}
            )
            .execute()
        )
        return True
    except:
        return False


async def is_admin(supabase: AsyncClient, id: int, user_id: int):

    res = (
        await supabase.from_("chats")
        .select("admins")
        .eq("id", id)
        .contains("admins", [str(user_id)])
        .execute()
    )
    dict_ = res.dict()

    try:
        return str(user_id) in dict_["data"][0]["admins"]
    except:
        return False


async def remove_bot(supabase: AsyncClient, id: int):
    try:
        _ = await supabase.from_("chats").delete().eq("id", id).execute()
        return True
    except:
        return False


async def add_admin(supabase: AsyncClient, id: int, user_id: int):
    try:
        res = await supabase.from_("chats").select("admins").eq("id", id).execute()
        admins = [*res.dict()["data"][0]["admins"], str(user_id)]
        _ = (
            await supabase.from_("chats")
            .update({"admins": admins})
            .eq("id", id)
            .execute()
        )
        return True
    except Exception as e:
        print("Error giving admin: ", str(e))
        return False


async def get_bots_with_ids(supabase: AsyncClient, ids: [int]):
    res = await supabase.from_("chats").select("id").in_("id", ids).execute()
    json = res.dict()
    try:
        return list(map(lambda x: x["id"], json["data"]))
    except:
        return []


async def get_bot(supabase: AsyncClient, id: int):

    res = await supabase.from_("chats").select("id").eq("id", id).execute()
    try:
        return res.dict()["data"][0]
    except (KeyError, IndexError) as e:
        print(f"No such bot: {str(e)}")
        return None
