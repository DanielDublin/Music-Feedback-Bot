# Prime Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a timed double-points event (`/mf primetime start|stop|status`) that awards 2 pts for quality MFR feedback (≥300 chars) and deducts 2 pts on delete during the event window.

**Architecture:** A new `PrimeTime` cog owns all event state and exposes a small public API (`is_active`, `was_during_prime_time`, `time_remaining`). Two existing files (`general.py`, `points_logic.py`) call that API — no state is duplicated. A background `asyncio.Task` ends the event automatically.

**Tech Stack:** discord.py 2.x, `asyncio`, standard `discord.File` for image delivery.

---

## File Map

| File | Change |
|------|--------|
| `data/assets/prime_time_start.gif` | New — copy from Downloads |
| `data/assets/prime_time_end.png` | New — copy from Downloads |
| `cogs/slash_commands/prime_time.py` | New cog with all event state + commands |
| `bot.py` | Add cog to `slash_extensions` |
| `cogs/general.py` | Modify `MFR_command` — Prime Time pts logic |
| `cogs/feedback_threads/modules/points_logic.py` | Modify `MFR_delete` — 2-pt removal |

---

### Task 1: Copy image assets

**Files:**
- Create: `data/assets/prime_time_start.gif`
- Create: `data/assets/prime_time_end.png`

- [ ] **Step 1: Copy the assets**

Run from the project root:
```bash
cp "C:/Users/Daniel/Downloads/starting gif.gif" data/assets/prime_time_start.gif
cp "C:/Users/Daniel/Downloads/PRIME TIME IS OVER.png" data/assets/prime_time_end.png
```

- [ ] **Step 2: Verify files exist**

```bash
ls data/assets/prime_time_start.gif data/assets/prime_time_end.png
```

Expected: both paths print without error.

---

### Task 2: Create the PrimeTime cog

**Files:**
- Create: `cogs/slash_commands/prime_time.py`

- [ ] **Step 1: Write the cog**

Create `cogs/slash_commands/prime_time.py` with this exact content:

```python
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from data.constants import (
    AUDIO_FEEDBACK,
    GENERAL_CHAT_CHANNEL_ID,
    LYRIC_FEEDBACK,
)

logger = logging.getLogger(__name__)

_ANNOUNCEMENT_CHANNELS = (GENERAL_CHAT_CHANNEL_ID, AUDIO_FEEDBACK, LYRIC_FEEDBACK)
_ASSETS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'assets')
_START_GIF = os.path.join(_ASSETS, 'prime_time_start.gif')
_END_IMG = os.path.join(_ASSETS, 'prime_time_end.png')

_START_TEXT = (
    "# PRIME TIME\n"
    "2x the MF points for the next hour .... *STARTING NOW!!!*\n\n"
    "Simply use <MFR in the feedback channels to get 2 points for every feedback given.\n"
    "Each feedback submission is still 1 point with <MFS.\n\n"
    "Feedback __must be quality__ and greater than 300 characters!\n"
    "Check your available <MF points in <#799751702529572876>."
)


def _log_task_error(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("[PrimeTime] Timer task raised: %r", task.exception())


class PrimeTime(commands.Cog):
    mf_group = app_commands.Group(
        name="mf",
        description="MF Bot commands",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )
    primetime_group = app_commands.Group(
        name="primetime",
        description="Prime Time double-points event",
        parent=mf_group,
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._active: bool = False
        self._start_time: datetime | None = None
        self._duration: int = 60
        self._timer_task: asyncio.Task | None = None

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
        for channel_id in _ANNOUNCEMENT_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.warning("[PrimeTime] Channel %s not found", channel_id)
                continue
            try:
                with open(filepath, 'rb') as f:
                    disc_file = discord.File(f)
                    if text:
                        await channel.send(text, file=disc_file)
                    else:
                        await channel.send(file=disc_file)
            except Exception:
                logger.error("[PrimeTime] Failed to post to channel %s", channel_id, exc_info=True)

    async def _run_timer(self, seconds: int) -> None:
        await asyncio.sleep(seconds)
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
    @app_commands.describe(minutes="Duration in minutes (default: 60)")
    async def primetime_start(self, interaction: discord.Interaction, minutes: int = 60) -> None:
        if self._active:
            await interaction.response.send_message("Prime Time is already active.", ephemeral=True)
            return

        self._active = True
        self._start_time = datetime.now(timezone.utc)
        self._duration = minutes

        self._timer_task = asyncio.create_task(self._run_timer(minutes * 60))
        self._timer_task.add_done_callback(_log_task_error)

        await interaction.response.send_message(
            f"Prime Time started for {minutes} minute(s).", ephemeral=True
        )
        await self._post_to_channels(_START_GIF, _START_TEXT)
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

        remaining = self.time_remaining()
        mins, secs = divmod(remaining, 60)
        await interaction.response.send_message(
            f"Prime Time is active. Time remaining: {mins}m {secs}s.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrimeTime(bot))
```

---

### Task 3: Register cog in bot.py

**Files:**
- Modify: `bot.py:110-116`

- [ ] **Step 1: Add to slash_extensions**

In `bot.py`, find the `slash_extensions` list and add `'cogs.slash_commands.prime_time'` as the last entry before the closing bracket:

```python
slash_extensions = [
    'cogs.slash_commands.timer',
    'cogs.slash_commands.admin',
    'cogs.slash_commands.rank_commands',
    'cogs.slash_commands.threads',
    'cogs.slash_commands.get_member_card',
    'cogs.slash_commands.aotw_event',
    'cogs.slash_commands.prime_time',
    # Add more slash command cogs as needed
]
```

---

### Task 4: Double points in general.py MFR_command

**Files:**
- Modify: `cogs/general.py:131-161`

- [ ] **Step 1: Replace MFR_command with Prime Time-aware version**

Replace the entire `MFR_command` method (lines 128–161) with:

```python
@commands.command(name="R",
                  help=f"Use to submit feedback.", brief="@username")
@admin_bypass_cooldown(1, 10)
async def MFR_command(self, ctx: commands.Context):

    mention = ctx.author.mention
    if not await self.handle_feedback_command_validity(ctx, mention):
        return

    # Strip <MFR prefix to get the feedback body for length check
    feedback_text = ctx.message.content
    if feedback_text.upper().startswith("<MFR"):
        feedback_text = feedback_text[4:].lstrip()

    prime_time_cog = self.bot.get_cog("PrimeTime")
    if prime_time_cog and prime_time_cog.is_active() and len(feedback_text) >= 300:
        pts = 2
    else:
        pts = 1

    await self.bot.db.add_points(str(ctx.author.id), pts)
    points = int(await self.bot.db.fetch_points(str(ctx.author.id)))
    channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)

    if pts == 2:
        await ctx.channel.send(
            f"{mention} has gained 2 MF points (Prime Time bonus). You now have **{points}** MF point(s).",
            delete_after=4
        )
    else:
        await ctx.channel.send(
            f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).",
            delete_after=4
        )
        if prime_time_cog and prime_time_cog.is_active():
            await ctx.channel.send(
                f"{mention}, your feedback is under 300 characters — quality threshold not met for the Prime Time bonus.",
                delete_after=10
            )

    feedback_cog = self.bot.get_cog("FeedbackThreads")
    result = await feedback_cog.record_feedback(ctx)
    if result is None:
        return
    thread, ticket_counter = result

    embed = discord.Embed(color=0x7e016f)
    embed.add_field(
        name=f"Feedback Notice - {self.helpers.get_formatted_time()}",
        value=(
            f"{mention} has **given feedback** and now has **{points}** MF point(s).\n\n"
            f"🔗 [Feedback Reply]({ctx.message.jump_url})\n"
            f"🟢 [Ticket #{ticket_counter}]({thread.jump_url})"
        ),
        inline=False
    )
    embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
    await channel.send(embed=embed)
```

---

### Task 5: 2-point deduction in points_logic.py MFR_delete

**Files:**
- Modify: `cogs/feedback_threads/modules/points_logic.py:202-287`

- [ ] **Step 1: Replace MFR_delete with Prime Time-aware version**

Replace the entire `MFR_delete` method (lines 202–287) with:

```python
async def MFR_delete(self, message: discord.Message, thread: discord.Thread, ticket_counter: int):
    channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
    if not channel:
        return

    deleted_content = self.helpers.shorten_message(message.content, 1000)
    user_id = str(message.author.id)

    # If message was posted during an active Prime Time window and content is cached,
    # check whether it qualified for double points.
    prime_time_cog = self.bot.get_cog("PrimeTime")
    if prime_time_cog and message.content and prime_time_cog.was_during_prime_time(message.created_at):
        feedback_text = message.content
        if feedback_text.upper().startswith("<MFR"):
            feedback_text = feedback_text[4:].lstrip()
        points_to_remove = 2 if len(feedback_text) >= 300 else 1
    else:
        points_to_remove = 1

    points_available = await self.bot.db.fetch_points(user_id)
    await self.bot.db.reduce_points(user_id, points_to_remove)
    total_points = await self.bot.db.fetch_points(user_id)

    if points_available > 0:

        delete_notice = await message.channel.send(
            f"{message.author.mention} deleted their feedback and lost **{points_to_remove}** MF Points. You now have **{total_points}** MF Points.\n\n"
            f"You will need to repost the feedback or give feedback again to regain the point. Visit <#{FEEDBACK_ACCESS_CHANNEL_ID}> for more information."
        )
        await delete_notice.delete(delay=60)

        embed = await self.embeds.MFR_to_delete_embed(
            deleted_content=deleted_content,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
        )
        try:
            await thread.send(embed=embed)
        except Exception:
            logger.error("Error sending thread embed", exc_info=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(
            name=f"Feedback Deletion - {self.helpers.get_formatted_time()}",
            value=(
                f"<@{user_id}> has **deleted** their feedback containing `<MFR`. "
                f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
            ),
            inline=False
        )
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await channel.send(embed=embed)

    elif points_available == 0:

        await self.bot.db.reset_points(user_id)
        total_points = int(await self.bot.db.fetch_points(str(user_id)))

        await channel.send(f"<@&{ADMINS_ROLE_ID}>")

        await message.channel.send(
            f"{message.author.mention} deleted their feedback but didn't have **{points_to_remove}** MF Points to use. You may have submitted a song since giving feedback.\n\n"
            f"You will need to repost the feedback or give feedback again to regain the point. Visit <#{FEEDBACK_ACCESS_CHANNEL_ID}> for more information."
        )

        embed = await self.embeds.MFR_to_delete_embed_with_no_points(
            deleted_content=deleted_content,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
        )
        await thread.send(embed=embed)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(
            name=f"Feedback Deletion - {self.helpers.get_formatted_time()}",
            value=(
                f"<@{user_id}> has **deleted** their feedback containing `<MFR` without enough points. "
                f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
            ),
            inline=False
        )
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await channel.send(embed=embed)
```
