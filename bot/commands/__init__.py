from discord.ext import commands

from .admin import AdminCommands
from .general import GeneralCommands
from .context import ContextCommands

async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCommands(bot))
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(ContextCommands(bot))