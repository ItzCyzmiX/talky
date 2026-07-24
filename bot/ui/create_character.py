import asyncio
import datetime
import secrets
import string
from typing import TYPE_CHECKING

import discord

from bot.apis.supabase import get_character, new_bot, new_character
from bot.consts import BOTS_CATEGORY_ID, CUSTOM_CHARACTERS_CHANNEL_ID, DELETE_DELAY
from bot.types import Character
from bot.utils import character_sys_message, sanitize

if TYPE_CHECKING:
    from bot.bot import Talky


# defaults are used when modifying an already exisisting character
class NewCharModal(discord.ui.Modal):
    def __init__(
        self, bot: "Talky", forkable: bool = True, defaults: Character | dict = {}
    ):
        super().__init__(title="Create Ai Character")
        self.bot = bot
        self.forkable = forkable

        self.is_edit = defaults.get("message_id", None) is not None
        self.og_message_id = defaults.get("message_id", None)
        self.og_character_id = defaults.get("id", None)

        self.name_input = discord.ui.TextInput(
            label="Bot Name",
            default=defaults.get("name", None),
            style=discord.TextStyle.short,
            required=True,
        )

        self.bio_input = discord.ui.TextInput(
            label="Bot Bio",
            placeholder="a ceo at a tech company",
            default=defaults.get("bio", None),
            style=discord.TextStyle.long,
            required=True,
        )

        self.personality_input = discord.ui.TextInput(
            label="Bot Personality",
            default=defaults.get("personality", None),
            placeholder="strict yet sweet, loves to chat...",
            style=discord.TextStyle.paragraph,
            required=True,
        )

        self.relationship_input = discord.ui.TextInput(
            label="Bot Relationship",
            default=defaults.get("relationship", None),
            placeholder="the users are your coworkers",
            style=discord.TextStyle.long,
            required=True,
        )

        self.start_message = discord.ui.TextInput(
            label="Start Message",
            default=defaults.get("start_message", None),
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

        if self.is_edit:
            await interaction.response.defer()

        character_id = (
            _generate_character_id()
            if self.og_character_id is None
            else self.og_character_id
        )

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

        view = ChatToCharacterView(
            character_id=character_id, bot=self.bot, forkable=self.forkable
        )

        channel = interaction.client.get_channel(CUSTOM_CHARACTERS_CHANNEL_ID)

        if self.is_edit and self.og_message_id is not None:
            message = await channel.fetch_message(self.og_message_id)
            await message.edit(embed=embed, view=view)
        else:
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
        )  # both updates and creates new characters (UPSERT)

        if not ok:
            if self.is_edit:
                await interaction.followup.send(
                    "Couldn't create ai character!",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Couldn't create ai character!",
                    ephemeral=True,
                    delete_after=DELETE_DELAY,
                )

            await message.delete()
            return

        msg = f"Your character, {self.name_input.value}, has been been {'edited' if self.is_edit else 'created'}! \nCharacter ID: ```{character_id}```\n"
        msg = msg + (
            f"Share this so other people can chat with {self.name_input.value}, or from the {interaction.client.get_channel(CUSTOM_CHARACTERS_CHANNEL_ID).mention} channel!\nYou can also use it for various commands to edit and delete your character!"
            if not self.is_edit
            else ""
        )
        await interaction.user.send(content=msg)
        if self.is_edit:
            await interaction.followup.send(
                content="Edited ai character!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                content="Created ai character!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )


class ChatToCharacterView(discord.ui.View):
    def __init__(self, character_id: str, bot: "Talky", forkable: bool = True):
        super().__init__(timeout=None)

        self.add_item(CharacterChatButton(character_id=character_id))

        if forkable:
            self.add_item(CharacterForkButton(character_id=character_id, bot=bot))


class CharacterForkButton(discord.ui.Button):
    def __init__(self, character_id: str, bot: "Talky"):
        super().__init__(
            label="Fork",
            style=discord.ButtonStyle.secondary,
            custom_id=f"fork_char_id:{character_id}",  # used for persistence
        )

        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        _, char_id = self.custom_id.split(":")

        char_id = sanitize(char_id.strip())

        character = await get_character(interaction.client.supabase, char_id)

        if character is None:
            await interaction.response.send_message(
                "Couldnt Find Character info!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        og_creator = interaction.client.get_user(character["creator_id"])

        character_id = _generate_character_id()

        embed = discord.Embed(
            title=f"{character['name']} Forked From {og_creator.mention if og_creator else 'unknown'}",
            description=character["bio"],
            color=0xFF5733,  # Hex color code
            timestamp=datetime.datetime.now(datetime.timezone.utc),  # Bottom timestamp
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )

        view = ChatToCharacterView(character_id=character_id, bot=self.bot)

        channel = interaction.client.get_channel(CUSTOM_CHARACTERS_CHANNEL_ID)

        message = await channel.send(embed=embed, view=view)

        ok = await new_character(
            supabase=self.bot.supabase,
            _id=character_id,
            message_id=message.id,
            creator_id=interaction.user.id,
            name=character["name"],
            bio=character["bio"],
            personality=character["personality"],
            relationship=character["relationship"],
            start_message=character["start_message"],
        )

        if not ok:
            await interaction.response.send_message(
                "Couldnt Find Character info!",
                ephemeral=True,
                delete_after=DELETE_DELAY,
            )
            return

        await interaction.user.send(
            f"You have forked the character {character['name']}! \nCharacter ID: ```{character_id}```\nRun /edit {character_id} to make it your own!"
        )

        await interaction.response.send_message(
            content="Created ai character!",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


class CharacterChatButton(discord.ui.Button):
    def __init__(self, character_id: str):
        super().__init__(
            label="Chat",
            style=discord.ButtonStyle.blurple,
            custom_id=f"char_id:{character_id}",  # used for persistence
        )

    async def callback(self, interaction: discord.Interaction):

        _, char_id = self.custom_id.split(":")

        char_id = sanitize(char_id.strip())

        character = await get_character(interaction.client.supabase, char_id)

        bot_category = interaction.client.get_channel(BOTS_CATEGORY_ID)

        new_channel = await bot_category.create_text_channel(name=character["name"])

        sys_message = character_sys_message(character)

        while not new_channel:
            await asyncio.sleep(0.3)

        starting_message = await new_channel.send(
            content=f"{interaction.user.mention} {character['start_message']}"
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
                    },  # append the starting message
                ],
            },
            char_id,
        )

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
            "custom_character_id": character["id"],
        }

        await interaction.response.send_message(
            content=f"Go chat with {character['name']} in {new_channel.mention}",
            ephemeral=True,
            delete_after=DELETE_DELAY,
        )


def _generate_character_id(length=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
