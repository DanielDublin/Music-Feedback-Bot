import asyncio
import io
import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from data.constants import (
    AUDIO_FEEDBACK,
    FEEDBACK_DISCUSSION_CHANNEL_ID,
    GENERAL_CHAT_CHANNEL_ID,
    LYRIC_FEEDBACK,
)

logger = logging.getLogger(__name__)

_ANNOUNCEMENT_CHANNELS = (GENERAL_CHAT_CHANNEL_ID, AUDIO_FEEDBACK, LYRIC_FEEDBACK)
_ASSETS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'assets')
_START_GIF = os.path.join(_ASSETS, 'prime_time_start.gif')
_END_IMG = os.path.join(_ASSETS, 'prime_time_end.png')

_MAX_MINUTES = 480


def _build_start_text(minutes: int) -> str:
    duration_str = "the next hour" if minutes == 60 else f"the next {minutes} minutes"
    return (
        f"# PRIME TIME\n"
        f"2x the MF points for {duration_str} .... *STARTING NOW!!!*\n\n"
        f"Simply use <MFR in the feedback channels to get 2 points for every feedback given.\n"
        f"Each feedback submission is still 1 point with <MFS.\n\n"
        f"Feedback __must be quality__ and greater than 300 characters!\n"
        f"Check your available <MF points in <#{FEEDBACK_DISCUSSION_CHANNEL_ID}>."
    )


def _log_task_error(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and task.exception():
        logger.error("[PrimeTime] Timer task raised: %r", task.exception())


class PrimeTime(commands.Cog):
    primetime_group = app_commands.Group(
        name="primetime",
        description="Prime Time double-points event",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._active: bool = False
        self._start_time: datetime | None = None
        self._duration: int = 60
        self._timer_task: asyncio.Task[None] | None = None

    # ── Public API used by other cogs ────────────────────────────────────────

    def is_active(self) -> bool:
        return self._active

    def was_during_prime_time(self, created_at: datetime) -> bool:
        """True if created_at falls within the last (or current) Prime Time window."""
        if self._start_time is None:
            return False
        end_time = self._start_time + timedelta(minutes=self._duration)
        return self._start_time <= created_at <= end_time

    def time_remaining(self) -> int | None:
        """Seconds until event ends; None if inactive."""
        if not self._active or self._start_time is None:
            return None
        end_time = self._start_time + timedelta(minutes=self._duration)
        remaining = (end_time - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _post_to_channels(self, filepath: str, text: str | None = None) -> None:
        def _read() -> bytes:
            with open(filepath, 'rb') as f:
                return f.read()
        raw = await asyncio.to_thread(_read)
        filename = os.path.basename(filepath)
        for channel_id in _ANNOUNCEMENT_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.warning("[PrimeTime] Channel %s not found", channel_id)
                continue
            try:
                disc_file = discord.File(io.BytesIO(raw), filename=filename)
                if text:
                    await channel.send(text, file=disc_file)
                else:
                    await channel.send(file=disc_file)
            except Exception:
                logger.error("[PrimeTime] Failed to post to channel %s", channel_id, exc_info=True)

    async def _run_timer(self, seconds: int) -> None:
        await asyncio.sleep(seconds)
        self._timer_task = None  # clear before calling _end so it doesn't cancel itself
        await self._end_prime_time()

    async def _end_prime_time(self) -> None:
        self._active = False
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = None
        logger.info("[PrimeTime] Event ended")
        await self._post_to_channels(_END_IMG)

    # ── Slash commands ────────────────────────────────────────────────────────

    @primetime_group.command(name="start", description="Start a Prime Time double-points event")
    @app_commands.describe(minutes="Duration in minutes (default: 60, max: 480)")
    async def primetime_start(self, interaction: discord.Interaction, minutes: int = 60) -> None:
        if self._active:
            await interaction.response.send_message("Prime Time is already active.", ephemeral=True)
            return

        if minutes <= 0 or minutes > _MAX_MINUTES:
            await interaction.response.send_message(
                f"Duration must be between 1 and {_MAX_MINUTES} minutes.", ephemeral=True
            )
            return

        self._active = True
        self._start_time = datetime.now(timezone.utc)
        self._duration = minutes

        self._timer_task = asyncio.create_task(self._run_timer(minutes * 60))
        self._timer_task.add_done_callback(_log_task_error)

        await interaction.response.send_message(
            f"Prime Time started for {minutes} minute(s).", ephemeral=True
        )
        await self._post_to_channels(_START_GIF, _build_start_text(minutes))
        logger.info("[PrimeTime] Started for %d minutes", minutes)

    @primetime_group.command(name="stop", description="Stop the active Prime Time event early")
    async def primetime_stop(self, interaction: discord.Interaction) -> None:
        if not self._active:
            await interaction.response.send_message("No Prime Time event is active.", ephemeral=True)
            return

        await interaction.response.send_message("Prime Time stopped.", ephemeral=True)
        await self._end_prime_time()
        logger.info("[PrimeTime] Manually stopped")

    @primetime_group.command(name="status", description="Check current Prime Time status")
    async def primetime_status(self, interaction: discord.Interaction) -> None:
        if not self._active:
            await interaction.response.send_message("Prime Time is not active.", ephemeral=True)
            return

        remaining = self.time_remaining() or 0
        mins, secs = divmod(remaining, 60)
        await interaction.response.send_message(
            f"Prime Time is active. Time remaining: {mins}m {secs}s.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrimeTime(bot))
