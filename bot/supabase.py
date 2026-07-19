from supabase import acreate_client, AsyncClient
import os


async def create_supabase():
    supabase: AsyncClient = await acreate_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY")
    )
    return supabase


async def update_messages(supabase: AsyncClient, _id: int, new_msgs: dict):
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


async def get_messages(supabase: AsyncClient, _id: int):
    res = await supabase.from_("chats").select("messages").eq("id", _id).execute()

    try:
        return res.dict()["data"][0]["messages"]["messages"]
    except Exception as e:
        print("Error getting messages by channel id: ", str(e))
        return None


async def new_bot(
    supabase: AsyncClient, _id: int, bot_name: str, admins: [int], messages: dict
):
    try:
        _ = (
            await supabase.from_("chats")
            .upsert(
                {
                    "id": _id,
                    "admins": admins,
                    "bot_name": bot_name,
                    "messages": messages,
                }
            )
            .execute()
        )
        return True
    except Exception as e:
        print("Error creating bot: ", str(e))
        return False


async def is_admin(supabase: AsyncClient, _id: int, user_id: int):

    res = (
        await supabase.from_("chats")
        .select("admins")
        .eq("id", _id)
        .contains("admins", [str(user_id)])
        .execute()
    )
    dict_ = res.dict()

    try:
        return str(user_id) in dict_["data"][0]["admins"]
    except Exception as e:
        print("Error checking if user is admin: ", str(e))
        return False


async def remove_bot(supabase: AsyncClient, _id: int):
    try:
        _ = await supabase.from_("chats").delete().eq("id", _id).execute()
        return True
    except Exception as e:
        print("Error removing bot by id: ", str(e))
        return False


async def add_admin(supabase: AsyncClient, _id: int, user_id: int):
    try:
        res = await supabase.from_("chats").select("admins").eq("id", _id).execute()
        admins = [*res.dict()["data"][0]["admins"], str(user_id)]
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


async def get_bots_with_ids(supabase: AsyncClient, ids: [int]):
    res = await supabase.from_("chats").select("id").in_("id", ids).execute()
    json = res.dict()
    try:
        return list(map(lambda x: x["id"], json["data"]))
    except Exception as e:
        print("Error getting bots by ids: ", str(e))
        return None


async def get_bot(supabase: AsyncClient, _id: int):

    res = await supabase.from_("chats").select("id").eq("id", _id).execute()
    try:
        return res.dict()["data"][0]
    except (KeyError, IndexError) as e:
        print(f"No such bot: {str(e)}")
        return None


async def change_bot_gpt(supabase: AsyncClient, _id: int, model: str = "llama"):
    try:
        _ = await supabase.from_("chats").update({"gpt": model}).eq("id", _id).execute()
        return True
    except Exception as e:
        print("Error changing bot's model: ", str(e))
        return False


async def get_chat_model(supabase: AsyncClient, _id: int):

    res = await supabase.from_("chats").select("gpt").eq("id", _id).execute()
    try:
        return res.dict()["data"][0]["gpt"]
    except (KeyError, IndexError) as e:
        print(f"No such bot: {str(e)}")
        return None
