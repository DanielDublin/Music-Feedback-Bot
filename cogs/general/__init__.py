"""Signature module for the General cog.

Each method here is a thin shim: it carries the discord.py decorators and
cooldown wiring, then delegates the body to one of three impl objects
(feedback / queries / music). Read this file like a table of contents —
implementations live in the sibling modules.

The cog is registered as `cogs.general` (this package). bot.py's extension
loader treats the package and the old flat module identically.
"""

import logging

import discord
from discord.ext import commands, tasks

from modules.cooldowns import admin_bypass_cooldown

from .feedback import FeedbackImpl
from .music import MusicLookupImpl
from .queries import QueriesImpl

logger = logging.getLogger(__name__)


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.feedback = FeedbackImpl(bot)
        self.queries = QueriesImpl(bot)
        self.music = MusicLookupImpl(bot)
        self.cleanup_deleted_messages.start()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(help="Use to check how many MF points you have.")
    @admin_bypass_cooldown(1, 10)
    async def points(self, ctx: commands.Context, user: discord.Member = None):
        await self.queries.show_points(ctx, user)

    @commands.command(aliases=["leaderboard"], help="(Use to see the leaderboard.")
    @admin_bypass_cooldown(1, 10)
    async def top(self, ctx: commands.Context):
        await self.queries.show_top(ctx)

    @commands.command(name="R", help="Use to submit feedback.", brief="@username")
    @admin_bypass_cooldown(1, 10)
    async def MFR_command(self, ctx: commands.Context):
        await self.feedback.handle_mfr(ctx)

    @commands.command(name="S", help="Use to ask for feedback.", brief="(link, file, text)")
    @admin_bypass_cooldown(1, 10)
    async def MFs_command(self, ctx: commands.Context):
        await self.feedback.handle_mfs(ctx)

    @commands.command(help="Use to present the band's genres.", brief='(Band Name)')
    @admin_bypass_cooldown(1, 60)
    async def genres(self, ctx: commands.Context, *, band_name: str):
        await self.music.show_genres(ctx, band_name)

    @commands.command(help="Use to present 10 similar bands to a wanted band.", brief='(Band Name)')
    @admin_bypass_cooldown(1, 60)
    async def similar(self, ctx: commands.Context, *, band_name: str):
        await self.music.show_similar(ctx, band_name)

    @tasks.loop(hours=1)
    async def cleanup_deleted_messages(self):
        """Periodically clear stale message IDs — entries older than ~1 hour were never matched."""
        if self.feedback.deleted_messages:
            self.feedback.deleted_messages.clear()

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{ctx.author.mention}, this command is on cooldown. Try again in {error.retry_after:.1f}s.",
                delete_after=10,
            )
        elif isinstance(error, commands.CheckFailure):
            pass  # guild_only check — silently ignore DM attempts
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention}, missing required argument: `{error.param.name}`.",
                delete_after=10,
            )
        else:
            raise error  # let the global handler deal with it


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
