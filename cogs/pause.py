"""Dev-only kill switch so a second instance (same token) can be run locally for testing.

<mf pause_commands  - this instance ignores all gateway events, slash commands and log
                      mirroring, and stops its cog background loops. It still hears
                      the owner's <mf resume_commands.
<mf resume_commands - back to normal.

Close the local instance BEFORE resuming, or both will answer. Pause state survives a
watchdog restart (data/paused.flag). Raw asyncio.create_task timers inside cogs are not
stopped, only discord.ext.tasks loops.
"""

import asyncio
import inspect
import logging
from pathlib import Path

from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

PAUSE_FLAG = Path(__file__).resolve().parent.parent / "data" / "paused.flag"


class Pause(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._stopped_loops: list[tasks.Loop] = []
        bot.paused = PAUSE_FLAG.exists()
        bot.tree.interaction_check = self._tree_gate
        if bot.paused:
            logger.warning("Started in PAUSED mode (data/paused.flag present)")

    async def _tree_gate(self, interaction) -> bool:
        if self.bot.paused:
            raise app_commands.AppCommandError("paused")  # swallowed in bot.on_app_command_error
        return True

    def _loops(self):
        for cog in self.bot.cogs.values():
            for _, loop in inspect.getmembers(cog, lambda v: isinstance(v, tasks.Loop)):
                yield loop

    def _stop_loops(self):
        for loop in self._loops():
            if loop.is_running() and loop not in self._stopped_loops:
                loop.cancel()
                self._stopped_loops.append(loop)

    @commands.Cog.listener()
    async def on_ready(self):
        # Cogs start their loops in their own on_ready; re-stop them if we booted paused.
        if self.bot.paused:
            await asyncio.sleep(15)
            self._stop_loops()

    @commands.is_owner()
    @commands.command(name="pause_commands")
    async def pause_commands(self, ctx):
        PAUSE_FLAG.parent.mkdir(parents=True, exist_ok=True)
        PAUSE_FLAG.touch()
        self._stop_loops()
        self.bot.paused = True
        logger.warning("Bot PAUSED by %s", ctx.author)
        await ctx.send("⏸️ Paused: events, commands, slash commands, loops and log mirroring are off. "
                       "Close your local instance, then `<mf resume_commands`.")

    @commands.is_owner()
    @commands.command(name="resume_commands")
    async def resume_commands(self, ctx):
        self.bot.paused = False
        PAUSE_FLAG.unlink(missing_ok=True)
        for loop in self._stopped_loops:
            try:
                loop.start()
            except RuntimeError:
                pass  # already running
        self._stopped_loops.clear()
        logger.warning("Bot RESUMED by %s", ctx.author)
        await ctx.send("▶️ Resumed.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Pause(bot))
