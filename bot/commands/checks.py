from typing import TYPE_CHECKING

from discord import Interaction, app_commands

from bot.apis.supabase import get_character_owner, is_admin
from bot.consts import BOT_CREATION_CHANNEL

if TYPE_CHECKING:
    from bot.bot import Talky


def is_in_creation_channel():
    async def predicate(interaction: Interaction) -> bool:
        bot: "Talky" = interaction.client

        if interaction.channel_id == BOT_CREATION_CHANNEL:
            return True

        raise app_commands.CheckFailure(
            f"Must be used in the {bot.get_channel(BOT_CREATION_CHANNEL).mention} !"
        )

    return app_commands.check(predicate)


def is_in_chatbot_channel():
    async def predicate(interaction: Interaction) -> bool:
        bot: "Talky" = interaction.client

        if str(interaction.channel_id) in bot.running_bots.keys():
            return True

        raise app_commands.CheckFailure(
            "Not allowed in this channel, make sure your in a chatbot channel!"
        )

    return app_commands.check(predicate)


def is_chat_admin():
    async def predicate(interaction: Interaction) -> bool:

        bot: "Talky" = interaction.client

        am_admin = await _validate_admin(
            bot=bot, channel_id=interaction.channel_id, user_id=interaction.user.id
        )

        if am_admin:
            return True

        raise app_commands.CheckFailure("You must be an admin to use this command!")

    return app_commands.check(predicate)


async def _validate_admin(bot: "Talky", channel_id: int, user_id: int) -> bool:
    admins = bot.running_bots.get(str(channel_id), {}).get("admins", None)

    am_admin = False

    if admins is None:
        am_admin = await is_admin(bot.supabase, channel_id, user_id)
    else:
        am_admin = str(user_id) in admins

    return am_admin


async def is_character_owner(bot: "Talky", character_id: int, user_id: int) -> bool:
    try:
        res: int = await get_character_owner(bot.supabase, character_id)

        return res == user_id
    except Exception as e:
        print("Error validating character ownership: ", str(e))
        return False
