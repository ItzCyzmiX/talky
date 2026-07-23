import discord
import datetime
import string
import secrets
import asyncio

from bot.consts import DELETE_DELAY, CUSTOM_CHARACTERS_CHANNEL_ID, BOTS_CATEGORY_ID
from bot.utils import sanitize_msg, character_sys_message
from bot.apis.supabase import new_character, get_character, new_bot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import Talky


class NewCharModal(discord.ui.Modal):
    def __init__(self, bot: "Talky"):
        super().__init__(title="Create Ai Character")

        self.bot = bot

        self.name_input = discord.ui.TextInput(
            label="Bot Name", style=discord.TextStyle.short, required=True
        )

        self.bio_input = discord.ui.TextInput(
            label="Bot Bio",
            placeholder="a ceo at a tech company",
            style=discord.TextStyle.long,
            required=True,
        )

        self.personality_input = discord.ui.TextInput(
            label="Bot Personality",
            placeholder="strict yet sweet, loves to chat...",
            style=discord.TextStyle.paragraph,
            required=True,
        )

        self.relationship_input = discord.ui.TextInput(
            label="Bot Relationship",
            placeholder="the users are your coworkers",
            style=discord.TextStyle.long,
            required=True,
        )

        self.start_message = discord.ui.TextInput(
            label="Start Message",
            placeholder="You are late again!",
            style=discord.TextStyle.long,
            required=True,
        )

        self.add_item(self.name_input)
        self.add_item(self.bio_input)
        self.add_item(self.personality_input)
        self.add_item(self.relationship_input)
        self.add_item(self.start_message)

    async def on_submit(self, interaction: discord.Interaction):
        character_id = _generate_character_id()

        embed = discord.Embed(
            title=f"{self.name_input.value}",
            description=f"{self.bio_input.value}",
            color=0xFF5733,  # Hex color code
            timestamp=datetime.datetime.now(datetime.timezone.utc),  # Bottom timestamp
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )

        view = ChatToCharacterView(character_id=character_id)

        channel = interaction.client.get_channel(CUSTOM_CHARACTERS_CHANNEL_ID)

        message = await channel.send(embed=embed, view=view)

        ok = await new_character(
            supabase=self.bot.supabase,
            _id=character_id,
            message_id=message.id,
            creator_id=interaction.user.id,
            name=self.name_input.value,
            bio=self.bio_input.value,
            personality=self.personality_input.value,
            relationship=self.relationship_input.value,
            start_message=self.start_message.value,
        )

        if not ok:
            await interaction.response.send_message(
                "Couldn't create ai character!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            await message.delete()
            return

        await interaction.response.send_message(
            "Created ai character!", ephemeral=True, delete_after=DELETE_DELAY
        )


class ChatToCharacterView(discord.ui.View):
    def __init__(self, character_id: str):
        super().__init__(timeout=None)

        self.add_item(CharacterChatButton(character_id=character_id))


class CharacterChatButton(discord.ui.Button):
    def __init__(self, character_id: str):
        super().__init__(
            label="Chat",
            style=discord.ButtonStyle.blurple,
            custom_id=f"char_id:{character_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        _, char_id = self.custom_id.split(":")

        char_id = sanitize_msg(char_id.strip())

        character = await get_character(interaction.client.supabase, char_id)

        bot_category = interaction.client.get_channel(BOTS_CATEGORY_ID)

        new_channel = await bot_category.create_text_channel(name=character["name"])

        sys_message = character_sys_message(character)

        while not new_channel:
            await asyncio.sleep(0.3)

        starting_message = await new_channel.send(
            content=f"{interaction.user.mention} {character["start_message"]}"
        )

        ok = await new_bot(
            interaction.client.supabase,
            new_channel.id,
            character["name"],
            [interaction.user.id],
            {
                "messages": [
                    sys_message,
                    {
                        "role": "assistant",
                        "content": character["start_message"],
                        "discord_message_id": starting_message.id,
                    },
                ],
            },
            char_id,
        )

        await asyncio.sleep(0.3)

        if not ok:
            await interaction.response.send_message(
                "Couldnt create the chat bot, try again",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        interaction.client.running_bots[str(new_channel.id)] = {
            "admins": [str(interaction.user.id)],
            "messages": [
                sys_message,
                {
                    "role": "assistant",
                    "content": character["start_message"],
                    "discord_message_id": starting_message.id,
                },
            ],
            "lock": asyncio.Lock(),
        }

        await interaction.response.send_message(
            content=f"Go chat with {character["name"]} in {new_channel.mention}",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


def _generate_character_id(length=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
