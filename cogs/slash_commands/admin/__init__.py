"""Signature module for the Admin slash-command cog.

Each method here is a thin shim: it carries the discord.py app_commands
decorators (group, autocomplete, permissions) and delegates the body to one
of two impl objects (points_ops / runtime). Read this file as a table of
contents of every admin slash command the bot registers.

The cog is registered as `cogs.slash_commands.admin` (this package). The
extension loader treats the package and the old flat module identically.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .points_ops import AdminPointsImpl
from .runtime import AdminRuntimeImpl, extension_autocomplete

logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.points_ops = AdminPointsImpl(bot)
        self.runtime = AdminRuntimeImpl(bot)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        return True

    group = app_commands.Group(
        name="mfpoints",
        description="Alter any user's points.",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

    @group.command(
        name='add',
        description="Use to add more points to a user.\n```/mfpoints add @user/user_id amount(optional)```",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member to add points to", points="Number of points to add (default: 1)")
    async def add(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        await self.points_ops.handle_add(interaction, user, points)

    @group.command(
        name='remove',
        description="Use to remove points from a user.\n```/mfpoints remove @user/user_id amount(optional)```",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member to remove points from", points="Number of points to remove (default: 1)")
    async def remove(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        await self.points_ops.handle_remove(interaction, user, points)

    @group.command(
        name="clear",
        description="Use to reset all the points from a user.\n```/mfpoints clear @user/user_id```",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member whose points to clear")
    async def clear(self, interaction: discord.Interaction, user: discord.Member):
        await self.points_ops.handle_clear(interaction, user)

    @app_commands.command(name="reload", description="Reload a bot extension by name")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(extension="Extension path (e.g. cogs.general)")
    @app_commands.autocomplete(extension=extension_autocomplete)
    async def reload_extension(self, interaction: discord.Interaction, extension: str):
        await self.runtime.handle_reload(interaction, extension)

    @app_commands.command(name="status", description="Show bot status")
    @app_commands.checks.has_permissions(administrator=True)
    async def status(self, interaction: discord.Interaction):
        await self.runtime.handle_status(interaction)


async def setup(bot: commands.Bot):
    # await bot.add_cog(Admin(bot), guild=discord.Object(id=SERVER_ID)) # for debug
    await bot.add_cog(Admin(bot))
