import asyncio
import io
import json
import logging
import os
import random
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from data.constants import (
    AUDIO_FEEDBACK,
    FEEDBACK_DISCUSSION_CHANNEL_ID,
    GENERAL_CHAT_CHANNEL_ID,
    LYRIC_FEEDBACK,
)
from ml_model.ml_model_loader import BONUS_QUALITY_THRESHOLD

logger = logging.getLogger(__name__)

_ANNOUNCEMENT_CHANNELS = (GENERAL_CHAT_CHANNEL_ID, AUDIO_FEEDBACK, LYRIC_FEEDBACK)
_ASSETS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'assets')
_START_GIF = os.path.join(_ASSETS, 'prime_time_start.gif')
_END_IMG = os.path.join(_ASSETS, 'prime_time_end.png')

_MAX_MINUTES = 480

# ── Auto-trigger config ────────────────────────────────────────────────────
# Daily: rolling-window goal that fires Prime Time once a real burst happens.
_DAILY_WINDOW_SECONDS = 60 * 60          # count quality feedbacks in the last hour
_DAILY_GOAL = 10                          # feedbacks to fire
_DAILY_DURATION_MINUTES = 60
_DAILY_COOLDOWN_HOURS = 24

# Saturday: rare big payoff. Counts quality feedbacks over a full UTC Saturday;
# fires once when the goal is hit. 14-day cooldown so it's bi-weekly at best.
_SATURDAY_GOAL = 50
_SATURDAY_DURATION_MINUTES = 240          # 4 hours
_SATURDAY_COOLDOWN_DAYS = 14

# ── Build-up nudges ────────────────────────────────────────────────────────
# As the rolling counter climbs toward the daily goal, post a single message
# each time it crosses a new stage. Pools per stage so it doesn't get stale.
# Goal-hit (count = _DAILY_GOAL) fires Prime Time itself and skips nudges.
_NUDGE_STAGES = (3, 5, 7, 9)

# Saturday nudges fire as the saturday_count climbs across the Saturday-UTC
# window. Festival theming to set the bi-weekly headliner apart from the
# nightly daily show.
_SATURDAY_NUDGE_STAGES = (10, 25, 40, 49)

_SATURDAY_NUDGES: dict[int, list[str]] = {
    10: [
        "🎪 **Bi-weekly Saturday show** selling tickets · **{count}/{goal}** quality MFRs today.",
        "🎟️ Stage going up for the **bi-weekly headliner** · **{count}/{goal}** today.",
        "🚛 Gear's loading in for **today's bi-weekly Saturday set** · **{count}/{goal}**.",
        "🎤 Opener's set — **today's bi-weekly show** forming · **{count}/{goal}**.",
    ],
    25: [
        "🎸 Half-house · **{count}/{goal}**. **Bi-weekly Saturday headliner** warming up backstage.",
        "🥁 Main stage filling · **{count}/{goal}**. Halfway to **today's bi-weekly Saturday show**.",
        "🎶 Mid-festival energy · **{count}/{goal}**. {remaining} away from the bi-weekly headliner.",
        "🎟️ Half the tickets sold · **{count}/{goal}** quality feedbacks for **today's bi-weekly set**.",
    ],
    40: [
        "🔊 **Bi-weekly headliner** about to take stage · **{count}/{goal}**. {remaining} more to fire.",
        "🎶 Lights dimming on the main stage · **{count}/{goal}**. {remaining} to go on **today's bi-weekly Saturday**.",
        "🎤 Backstage announces the **bi-weekly headliner** · **{count}/{goal}**. {remaining} away.",
        "🎸 Crowd packing in for **today's bi-weekly main event** · **{count}/{goal}**.",
    ],
    49: [
        "🎟️ Curtain rising on **today's bi-weekly Saturday show** · **{count}/{goal}**. One quality `<MFR` away.",
        "🔥 **Bi-weekly Saturday headliner** one feedback away · **{count}/{goal}**.",
        "🎤 Spotlight's on · **{count}/{goal}**. One more for **today's bi-weekly main event**.",
        "🎶 Final ticket at the door for **today's bi-weekly show** · **{count}/{goal}**. One quality `<MFR` and lights go down.",
    ],
}


_NUDGES: dict[int, list[str]] = {
    3: [
        "🎤 Opener's warming up · **{count}/{goal}** quality MFRs in the hour.",
        "🥁 Soundcheck · **{count}/{goal}**. The setlist's forming.",
        "🎶 Doors are open · **{count}/{goal}** quality feedbacks tracking.",
        "🎸 First song landed · **{count}/{goal}**. Crowd's filing in.",
    ],
    5: [
        "🎸 Mid-set vibes · **{count}/{goal}**. Halfway to the encore call.",
        "🎤 Set's in full swing · **{count}/{goal}**. {remaining} songs from encore.",
        "🥁 Halfway through · **{count}/{goal}**. The crowd's locked in.",
        "🎶 Mid-set energy · **{count}/{goal}**. {remaining} more 'til the encore.",
    ],
    7: [
        "🎶 Headliner's on deck · **{count}/{goal}**. {remaining} songs to go.",
        "🔊 Building to the headliner · **{count}/{goal}**. {remaining} more quality MFRs.",
        "🎸 Stage lights warming · **{count}/{goal}**. {remaining} before the closer.",
        "🎤 Closer's getting ready · **{count}/{goal}**. {remaining} away.",
    ],
    9: [
        "🔥 Encore loaded · **{count}/{goal}**. One more and the lights go down.",
        "🎤 Crowd's chanting · **{count}/{goal}**. One quality `<MFR` to bring it home.",
        "🎶 Last song queued · **{count}/{goal}**. One more.",
        "🎸 Final number on deck · **{count}/{goal}**. One quality feedback and Prime Time fires.",
    ],
}

_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "prime_time_state.json"


def _load_auto_state() -> dict:
    default = {
        "last_daily_auto_trigger_ts": None,
        "last_saturday_auto_trigger_ts": None,
        "saturday_window_start_ts": None,
        "saturday_count": 0,
        # Highest Saturday nudge stage already posted for the current window —
        # persisted so a restart mid-Saturday doesn't re-post the same nudge.
        "last_saturday_nudge_stage": 0,
        # Active-event snapshot — persisted so a restart mid-event can resume
        # the 2x window instead of silently losing it.
        "active_kind": None,           # "manual" | "daily" | "saturday"
        "active_start_ts": None,       # epoch seconds
        "active_duration_minutes": 0,
        # Live "Saturday progress" message in GENERAL_CHAT_CHANNEL_ID. Updated
        # in place on each quality feedback during a Saturday window; cleared
        # when the window ends or Saturday Prime Time fires.
        "saturday_progress_message_id": None,
        "saturday_progress_channel_id": None,
        # Cumulative fire/extension counters surfaced via /primetime stats.
        "daily_fire_count": 0,
        "saturday_fire_count": 0,
        "manual_fire_count": 0,
        "extension_count": 0,
    }
    if not _STATE_FILE.exists():
        return default
    try:
        with _STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in default.items():
            data.setdefault(k, v)
        return data
    except Exception:
        logger.error("Could not load prime-time auto-trigger state; starting fresh", exc_info=True)
        return default


def _save_auto_state(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, _STATE_FILE)


def _saturday_window_start(now: datetime) -> datetime | None:
    """Return midnight UTC of the current Saturday if `now` is on a Saturday,
    else None. weekday(): Monday=0 .. Saturday=5."""
    if now.weekday() != 5:
        return None
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _next_saturday_window_start(now: datetime) -> datetime:
    """Return midnight UTC of the next upcoming Saturday — today if it's
    Saturday, otherwise the closest future one."""
    days_until_sat = (5 - now.weekday()) % 7
    target = (now + timedelta(days=days_until_sat)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    return target


def _build_start_text(minutes: int) -> str:
    duration_str = "the next hour" if minutes == 60 else f"the next {minutes} minutes"
    confidence_pct = int(BONUS_QUALITY_THRESHOLD * 100)
    return (
        f"# PRIME TIME\n"
        f"2x the MF points for {duration_str} .... *STARTING NOW!!!*\n\n"
        f"During Prime Time, every quality `<MFR` you submit earns **2 points** instead of 1. "
        f"`<MFS` submissions still cost 1 point.\n\n"
        f"## Qualifying for the 2x bonus\n\n"
        f"**In <#{AUDIO_FEEDBACK}>**, an automated quality model scores your feedback. "
        f"To earn 2x, the model must be at least **{confidence_pct}% confident** your feedback is good.\n"
        f"- ✅ **Rewards:** specific timestamps, technical terms (EQ, compression, mix, levels, etc.), "
        f"concrete suggestions, problem identification, comparisons.\n"
        f"- ❌ **Penalizes:** excessive praise (\"amazing\", \"perfect\"), generic phrases "
        f"(\"sounds good\", \"great job\"), too-short replies, vague \"could/should/might\" without specifics.\n\n"
        f"**In <#{LYRIC_FEEDBACK}>**, the model isn't trained on lyric feedback yet, so we use a simple rule: "
        f"feedback must be **over 300 characters** to earn the bonus.\n\n"
        f"Feedback that doesn't qualify still earns the base **1 point**. "
        f"If you delete an `<MFR` that got the bonus, you'll lose **2 points**.\n\n"
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

        # Auto-trigger state
        self._recent_feedbacks: deque[float] = deque()
        # Highest hype-train stage we've already announced this cycle. Reset
        # to 0 when the rolling window dips below the first stage or after
        # Prime Time fires.
        self._last_nudge_stage: int = 0
        self._auto_state: dict = _load_auto_state()
        self._auto_trigger_lock: asyncio.Lock = asyncio.Lock()
        # Tracks whether the *current* active event was auto-triggered (daily
        # or saturday) — controls which extension cap to apply.
        self._active_kind: str | None = None  # "manual" | "daily" | "saturday"

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

    async def _end_prime_time(self, *, post_end_image: bool = True) -> None:
        self._active = False
        self._active_kind = None
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = None

        # Clear persisted active-state snapshot.
        self._auto_state["active_kind"] = None
        self._auto_state["active_start_ts"] = None
        self._auto_state["active_duration_minutes"] = 0
        _save_auto_state(self._auto_state)

        logger.info("[PrimeTime] Event ended")
        if post_end_image:
            await self._post_to_channels(_END_IMG)

    def _persist_active(self) -> None:
        """Snapshot the currently-active event so we can resume after restart."""
        if not self._active or self._start_time is None:
            return
        self._auto_state["active_kind"] = self._active_kind
        self._auto_state["active_start_ts"] = self._start_time.timestamp()
        self._auto_state["active_duration_minutes"] = self._duration
        _save_auto_state(self._auto_state)

    # ── Restart resume ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Resume a Prime Time event that was active when the bot went down."""
        if self._active:
            # Already resumed — guard against on_ready firing twice.
            return
        kind = self._auto_state.get("active_kind")
        start_ts = self._auto_state.get("active_start_ts")
        duration = int(self._auto_state.get("active_duration_minutes") or 0)
        if not kind or start_ts is None or duration <= 0:
            return

        end_ts = float(start_ts) + duration * 60
        now_ts = time.time()
        if now_ts >= end_ts:
            # Event expired during downtime — quietly clean up and post the
            # end image so the chat sees a clean close.
            logger.info("[PrimeTime] Found expired %s event on restart, ending", kind)
            self._auto_state["active_kind"] = None
            self._auto_state["active_start_ts"] = None
            self._auto_state["active_duration_minutes"] = 0
            _save_auto_state(self._auto_state)
            try:
                await self._post_to_channels(_END_IMG)
            except Exception:
                logger.error("[PrimeTime] Failed to post end image on restart cleanup", exc_info=True)
            return

        remaining_seconds = int(end_ts - now_ts)
        self._active = True
        self._active_kind = kind
        self._start_time = datetime.fromtimestamp(float(start_ts), tz=timezone.utc)
        self._duration = duration
        self._timer_task = asyncio.create_task(self._run_timer(remaining_seconds))
        self._timer_task.add_done_callback(_log_task_error)
        logger.info(
            "[PrimeTime] Resumed %s event after restart (%d min remaining of %d)",
            kind, remaining_seconds // 60, duration,
        )

    # ── Auto-trigger hook (called by feedback_monitor) ────────────────────────

    async def record_quality_feedback(self) -> None:
        """Called by FeedbackMonitor for every ML-pass `<MFR` submission.

        Maintains a rolling 60-min counter and a Saturday-day counter, and
        fires (or extends) Prime Time when their thresholds are crossed.
        Errors here must not break the feedback pipeline — every public path
        is wrapped in try/except."""
        try:
            async with self._auto_trigger_lock:
                now_ts = time.time()
                now_dt = datetime.now(timezone.utc)

                self._record_rolling(now_ts)
                self._record_saturday(now_dt)

                await self._evaluate_daily(now_ts)
                await self._evaluate_saturday(now_ts, now_dt)
        except Exception:
            logger.error("[PrimeTime] record_quality_feedback failed", exc_info=True)

    def _record_rolling(self, now_ts: float) -> None:
        self._recent_feedbacks.append(now_ts)
        cutoff = now_ts - _DAILY_WINDOW_SECONDS
        while self._recent_feedbacks and self._recent_feedbacks[0] < cutoff:
            self._recent_feedbacks.popleft()
        if len(self._recent_feedbacks) < _NUDGE_STAGES[0]:
            # Burst fizzled below the first hype stage — reset so a fresh
            # burst can hype-train again from the start.
            self._last_nudge_stage = 0

    def _record_saturday(self, now_dt: datetime) -> None:
        marker = _saturday_window_start(now_dt)
        if marker is None:
            return
        marker_ts = marker.timestamp()
        stored = self._auto_state.get("saturday_window_start_ts")
        if stored != marker_ts:
            # New Saturday window — reset counter, nudge stage, and drop any
            # progress message from a previous Saturday so this Saturday's
            # display starts fresh.
            asyncio.create_task(self._clear_saturday_progress_message())
            self._auto_state["saturday_window_start_ts"] = marker_ts
            self._auto_state["saturday_count"] = 0
            self._auto_state["last_saturday_nudge_stage"] = 0
        self._auto_state["saturday_count"] = int(self._auto_state.get("saturday_count", 0)) + 1
        _save_auto_state(self._auto_state)

    async def _evaluate_daily(self, now_ts: float) -> None:
        count = len(self._recent_feedbacks)
        if count < _DAILY_GOAL:
            # Below the goal — maybe post a build-up nudge.
            if self._active:
                # Don't nudge while Prime Time is already running.
                return
            new_stage = max((s for s in _NUDGE_STAGES if s <= count), default=0)
            if new_stage > self._last_nudge_stage:
                await self._post_daily_progress(count, new_stage)
                self._last_nudge_stage = new_stage
            return

        # Goal hit. Cooldown gates both fresh fires AND cross-kind extensions.
        last = self._auto_state.get("last_daily_auto_trigger_ts")
        if last is not None and now_ts - last < _DAILY_COOLDOWN_HOURS * 3600:
            # On cooldown — just drain the burst so we don't re-check on every tick.
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            return

        if self._active and self._active_kind in ("daily", "manual"):
            # Same-kind re-trigger or admin-set event — drain the burst, no extension.
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            return

        if self._active and self._active_kind == "saturday":
            # Cross-kind overlap — Daily would have fired during an active
            # Saturday. Stack its duration onto the remaining Saturday window.
            await self._extend_active(_DAILY_DURATION_MINUTES, "daily goal hit during the bi-weekly Saturday show")
            self._auto_state["last_daily_auto_trigger_ts"] = now_ts
            _save_auto_state(self._auto_state)
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            return

        # Nothing active — fire fresh.
        await self._fire_auto("daily", _DAILY_DURATION_MINUTES, count=count)
        self._auto_state["last_daily_auto_trigger_ts"] = now_ts
        _save_auto_state(self._auto_state)
        self._recent_feedbacks.clear()
        self._last_nudge_stage = 0

    async def _evaluate_saturday(self, now_ts: float, now_dt: datetime) -> None:
        if _saturday_window_start(now_dt) is None:
            return
        count = int(self._auto_state.get("saturday_count", 0))

        if count < _SATURDAY_GOAL:
            # Below the goal — refresh the live progress message (skipped if
            # already fired today or on cooldown) and maybe post a stage nudge.
            if not self._active:
                await self._sync_saturday_progress_message(count, now_ts)
                new_stage = max((s for s in _SATURDAY_NUDGE_STAGES if s <= count), default=0)
                last_sat_stage = int(self._auto_state.get("last_saturday_nudge_stage", 0))
                if new_stage > last_sat_stage:
                    await self._post_saturday_progress(count, new_stage)
                    self._auto_state["last_saturday_nudge_stage"] = new_stage
                    _save_auto_state(self._auto_state)
            return

        last = self._auto_state.get("last_saturday_auto_trigger_ts")
        if last is not None and now_ts - last < _SATURDAY_COOLDOWN_DAYS * 86400:
            # On cooldown — leave saturday_count alone; the next Saturday
            # window will reset it on its own via _record_saturday.
            return

        if self._active and self._active_kind in ("saturday", "manual"):
            # Same-kind re-trigger or admin-set event — drain the counter.
            self._auto_state["saturday_count"] = 0
            self._auto_state["last_saturday_nudge_stage"] = 0
            _save_auto_state(self._auto_state)
            return

        if self._active and self._active_kind == "daily":
            # Cross-kind overlap — Saturday would have fired during an active
            # Daily. Stack its full duration onto the remaining Daily window.
            await self._extend_active(_SATURDAY_DURATION_MINUTES, "bi-weekly Saturday goal hit during a daily Prime Time")
            self._auto_state["last_saturday_auto_trigger_ts"] = now_ts
            self._auto_state["saturday_count"] = 0
            self._auto_state["last_saturday_nudge_stage"] = 0
            _save_auto_state(self._auto_state)
            return

        # Nothing active — fire fresh.
        await self._fire_auto("saturday", _SATURDAY_DURATION_MINUTES, count=count)
        self._auto_state["last_saturday_auto_trigger_ts"] = now_ts
        self._auto_state["saturday_count"] = 0
        self._auto_state["last_saturday_nudge_stage"] = 0
        _save_auto_state(self._auto_state)

    async def _post_saturday_progress(self, count: int, stage: int) -> None:
        channel = self.bot.get_channel(AUDIO_FEEDBACK)
        if channel is None:
            return
        pool = _SATURDAY_NUDGES.get(stage)
        if not pool:
            return
        message = random.choice(pool).format(
            count=count,
            goal=_SATURDAY_GOAL,
            remaining=_SATURDAY_GOAL - count,
        )
        try:
            await channel.send(message)
        except Exception:
            logger.error("[PrimeTime] Failed to post Saturday nudge", exc_info=True)

    def _build_saturday_progress_text(self, count: int) -> str:
        remaining = max(0, _SATURDAY_GOAL - count)
        bar_total = 20
        filled = min(bar_total, round(bar_total * count / _SATURDAY_GOAL))
        bar = "█" * filled + "░" * (bar_total - filled)
        return (
            f"🎪 **Bi-weekly Saturday Headliner — Live Progress**\n"
            f"`{bar}` **{count}/{_SATURDAY_GOAL}** quality `<MFR` today · "
            f"{remaining} to fire the 4-hour Prime Time."
        )

    async def _sync_saturday_progress_message(self, count: int, now_ts: float) -> None:
        """Post or edit the running 'X/50' display in GENERAL_CHAT_CHANNEL_ID.
        Skipped silently if it would be redundant: cooldown active, already
        fired this Saturday window, or no channel resolvable."""
        last_s = self._auto_state.get("last_saturday_auto_trigger_ts")
        sat_window_ts = self._auto_state.get("saturday_window_start_ts")
        # Skip if we already fired during the current Saturday window. The
        # cooldown check below covers that, but only roughly — anchor on the
        # window start so a back-to-back Saturday after a 14-day gap behaves
        # correctly.
        if last_s and sat_window_ts and float(last_s) >= float(sat_window_ts):
            return
        if last_s and now_ts - float(last_s) < _SATURDAY_COOLDOWN_DAYS * 86400:
            return

        channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)
        if channel is None:
            return

        text = self._build_saturday_progress_text(count)
        msg_id = self._auto_state.get("saturday_progress_message_id")
        msg_channel_id = self._auto_state.get("saturday_progress_channel_id")

        # If we have a stored message but it lives in a different channel
        # (e.g. constant changed), drop the reference and post fresh.
        if msg_id and msg_channel_id and msg_channel_id != GENERAL_CHAT_CHANNEL_ID:
            msg_id = None

        if msg_id:
            try:
                existing = await channel.fetch_message(msg_id)
                await existing.edit(content=text)
                return
            except discord.NotFound:
                # the stored message is gone — fall through and post a fresh one
                logger.warning("[PrimeTime] Saturday progress message missing; posting a fresh one")
            except discord.HTTPException:
                logger.error("[PrimeTime] Failed to edit Saturday progress message", exc_info=True)
                return

        try:
            msg = await channel.send(text)
        except discord.HTTPException:
            logger.error("[PrimeTime] Failed to post Saturday progress message", exc_info=True)
            return
        self._auto_state["saturday_progress_message_id"] = msg.id
        self._auto_state["saturday_progress_channel_id"] = GENERAL_CHAT_CHANNEL_ID
        _save_auto_state(self._auto_state)

    async def _clear_saturday_progress_message(self) -> None:
        """Delete the live progress message (if any) and clear the stored id.
        Called on Saturday-window change and on Saturday Prime Time fire."""
        msg_id = self._auto_state.get("saturday_progress_message_id")
        channel_id = self._auto_state.get("saturday_progress_channel_id")
        self._auto_state["saturday_progress_message_id"] = None
        self._auto_state["saturday_progress_channel_id"] = None
        _save_auto_state(self._auto_state)
        if not msg_id or not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.delete()
        except discord.NotFound:
            # already gone — the desired end state anyway, but surface it for visibility
            logger.warning("[PrimeTime] Saturday progress message already deleted")
        except discord.HTTPException:
            logger.warning("[PrimeTime] Could not delete stale Saturday progress message", exc_info=True)

    async def _fire_auto(self, kind: str, minutes: int, *, count: int) -> None:
        self._active = True
        self._active_kind = kind
        self._start_time = datetime.now(timezone.utc)
        self._duration = minutes
        self._timer_task = asyncio.create_task(self._run_timer(minutes * 60))
        self._timer_task.add_done_callback(_log_task_error)
        self._persist_active()

        # Bump cumulative fire counter for /primetime stats.
        counter_key = "saturday_fire_count" if kind == "saturday" else "daily_fire_count"
        self._auto_state[counter_key] = int(self._auto_state.get(counter_key, 0)) + 1
        _save_auto_state(self._auto_state)

        # Saturday Prime Time replaces the live progress message — pull it
        # down so chat doesn't show the running "X/50" alongside the fire.
        if kind == "saturday":
            await self._clear_saturday_progress_message()

        start_ts = int(self._start_time.timestamp())
        end_ts = start_ts + minutes * 60

        if kind == "daily":
            prefix = "🎟️ **THE SHOW'S ON**"
            why = (
                f"_Encore unlocked by **{count} quality feedbacks** in the last hour. "
                f"Lights go down for {minutes} minutes — give quality critical feedback now to earn 2x._"
            )
        elif kind == "saturday":
            prefix = "🎟️ **BI-WEEKLY SATURDAY HEADLINER**"
            sat_start_dt = _saturday_window_start(self._start_time) or self._start_time
            sat_start_ts = int(sat_start_dt.timestamp())
            why = (
                f"_The bi-weekly Saturday show is on — **<t:{sat_start_ts}:D>'s** Saturday window, "
                f"unlocked by **{count} quality feedbacks** today. "
                f"Lights stay down for {minutes} minutes (4-hour set). "
                f"Next eligible bi-weekly window: <t:{sat_start_ts + _SATURDAY_COOLDOWN_DAYS * 86400}:D>._"
            )
        else:
            prefix = "🎟️ **PRIME TIME**"
            why = ""

        intro = f"{prefix} — Prime Time fires for {minutes} minutes!\n"
        if why:
            intro += f"{why}\n"
        intro += f"🕒 **Started:** <t:{start_ts}:F> · **Ends:** <t:{end_ts}:t> (<t:{end_ts}:R>)\n\n"

        try:
            await self._post_to_channels(_START_GIF, intro + _build_start_text(minutes))
        except Exception:
            logger.error("[PrimeTime] Failed to announce auto-trigger", exc_info=True)
        logger.info("[PrimeTime] Auto-triggered (%s) for %d minutes (count=%d)", kind, minutes, count)

    async def _extend_active(self, fresh_duration_minutes: int, reason: str) -> None:
        """Append the full fresh duration to whatever's left of the active event.
        Used only when a *different-kind* auto-trigger fires during an active
        event (Daily↔Saturday overlap). Naturally rate-limited by the per-kind
        cooldowns, so no extra cap needed."""
        if not self._active or self._start_time is None:
            return
        now = datetime.now(timezone.utc)
        end_time = self._start_time + timedelta(minutes=self._duration)
        remaining_seconds = max(0, (end_time - now).total_seconds())
        elapsed_seconds = (now - self._start_time).total_seconds()

        new_remaining_seconds = remaining_seconds + fresh_duration_minutes * 60
        self._duration = int((elapsed_seconds + new_remaining_seconds) / 60)

        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = asyncio.create_task(self._run_timer(int(new_remaining_seconds)))
        self._timer_task.add_done_callback(_log_task_error)
        self._persist_active()

        self._auto_state["extension_count"] = int(self._auto_state.get("extension_count", 0)) + 1
        _save_auto_state(self._auto_state)

        new_remaining_minutes = max(1, int(round(new_remaining_seconds / 60)))
        new_end_ts = int((now + timedelta(seconds=new_remaining_seconds)).timestamp())

        try:
            channel = self.bot.get_channel(AUDIO_FEEDBACK)
            if channel is not None:
                await channel.send(
                    f"🎟️ **The set just got longer.** A second Prime Time stacked on — "
                    f"added **+{fresh_duration_minutes} min** ({reason}).\n"
                    f"🕒 **Now ends:** <t:{new_end_ts}:F> (<t:{new_end_ts}:R>) · "
                    f"~{new_remaining_minutes} min remaining."
                )
        except Exception:
            logger.error("[PrimeTime] Failed to announce extension", exc_info=True)
        logger.info("[PrimeTime] Extended (%s) by %d min, new remaining %d min, total event length %d",
                    reason, fresh_duration_minutes, new_remaining_minutes, self._duration)

    async def _post_daily_progress(self, count: int, stage: int) -> None:
        channel = self.bot.get_channel(AUDIO_FEEDBACK)
        if channel is None:
            return
        pool = _NUDGES.get(stage)
        if not pool:
            return
        message = random.choice(pool).format(
            count=count,
            goal=_DAILY_GOAL,
            remaining=_DAILY_GOAL - count,
        )
        try:
            await channel.send(message)
        except Exception:
            logger.error("[PrimeTime] Failed to post hype nudge", exc_info=True)

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
        self._active_kind = "manual"
        self._start_time = datetime.now(timezone.utc)
        self._duration = minutes

        self._timer_task = asyncio.create_task(self._run_timer(minutes * 60))
        self._timer_task.add_done_callback(_log_task_error)
        self._persist_active()

        self._auto_state["manual_fire_count"] = int(self._auto_state.get("manual_fire_count", 0)) + 1
        _save_auto_state(self._auto_state)

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

    @primetime_group.command(name="status", description="Full Prime Time status: active event + auto-trigger state")
    async def primetime_status(self, interaction: discord.Interaction) -> None:
        now_ts = int(time.time())
        lines: list[str] = ["🎟️ **Prime Time Status**"]

        # Active event block
        lines.append("")
        lines.append("**Active event:**")
        if self._active and self._start_time is not None:
            start_ts = int(self._start_time.timestamp())
            end_ts = start_ts + self._duration * 60
            remaining = max(0, end_ts - now_ts)
            mins, secs = divmod(remaining, 60)
            lines.append(f"• Kind: `{self._active_kind}`")
            lines.append(f"• Started: <t:{start_ts}:F>")
            lines.append(f"• Ends: <t:{end_ts}:F> (<t:{end_ts}:R>)")
            lines.append(f"• Remaining: **{mins}m {secs}s** of {self._duration} min total")
        else:
            lines.append("• _None_")

        # Daily auto block
        lines.append("")
        lines.append("**Daily auto-trigger** (10/hr rolling, 24h cooldown):")
        lines.append(f"• Rolling counter: **{len(self._recent_feedbacks)}/{_DAILY_GOAL}** in last 60 min")
        last_d = self._auto_state.get("last_daily_auto_trigger_ts")
        if last_d:
            next_d = int(last_d) + _DAILY_COOLDOWN_HOURS * 3600
            lines.append(f"• Last fire: <t:{int(last_d)}:F>")
            if now_ts < next_d:
                lines.append(f"• Next eligible: <t:{next_d}:F> (<t:{next_d}:R>)")
            else:
                lines.append("• Cooldown elapsed — eligible now")
        else:
            lines.append("• Last fire: _never_ — eligible now")

        # Saturday auto block
        lines.append("")
        lines.append("**Bi-weekly Saturday auto-trigger** (50 quality MFRs across one Saturday UTC, 14-day cooldown):")
        now_dt = datetime.now(timezone.utc)
        sat_start = _saturday_window_start(now_dt)
        sat_count = int(self._auto_state.get("saturday_count", 0))
        last_s = self._auto_state.get("last_saturday_auto_trigger_ts")

        if sat_start is not None:
            sat_start_ts = int(sat_start.timestamp())
            lines.append(
                f"• **Today is the Saturday window** (<t:{sat_start_ts}:D>) — counter: **{sat_count}/{_SATURDAY_GOAL}**"
            )
        else:
            next_window = _next_saturday_window_start(now_dt)
            next_window_ts = int(next_window.timestamp())
            lines.append(
                f"• Today is not Saturday — counter (last saved): **{sat_count}/{_SATURDAY_GOAL}**"
            )
            lines.append(
                f"• Next Saturday window opens: <t:{next_window_ts}:F> (<t:{next_window_ts}:R>)"
            )

        # The "next eligible Saturday" is the next Saturday whose window is
        # entered after the 14-day cooldown elapses. If we've never fired,
        # the next upcoming Saturday qualifies.
        if last_s:
            cooldown_end_ts = int(last_s) + _SATURDAY_COOLDOWN_DAYS * 86400
            anchor_ts = max(now_ts, cooldown_end_ts)
            anchor_dt = datetime.fromtimestamp(anchor_ts, tz=timezone.utc)
            # If the anchor lands on a Saturday already, that Saturday is eligible.
            eligible_dt = (
                _saturday_window_start(anchor_dt) or _next_saturday_window_start(anchor_dt)
            )
            eligible_ts = int(eligible_dt.timestamp())
            lines.append(f"• Last fire: <t:{int(last_s)}:F>")
            lines.append(
                f"• Next eligible: **<t:{eligible_ts}:D>** "
                f"(window opens <t:{eligible_ts}:R>)"
            )
        else:
            eligible_dt = sat_start or _next_saturday_window_start(now_dt)
            eligible_ts = int(eligible_dt.timestamp())
            lines.append("• Last fire: _never_")
            lines.append(
                f"• Next eligible: **<t:{eligible_ts}:D>** "
                f"(window opens <t:{eligible_ts}:R>) — no cooldown to wait on"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @primetime_group.command(name="reset_cooldown", description="Clear an auto-trigger cooldown (admin testing)")
    @app_commands.describe(kind="Which cooldown to clear")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily", value="daily"),
        app_commands.Choice(name="Saturday (bi-weekly)", value="saturday"),
        app_commands.Choice(name="Both", value="both"),
    ])
    async def primetime_reset_cooldown(self, interaction: discord.Interaction,
                                       kind: app_commands.Choice[str]) -> None:
        cleared: list[str] = []
        if kind.value in ("daily", "both"):
            self._auto_state["last_daily_auto_trigger_ts"] = None
            cleared.append("daily")
        if kind.value in ("saturday", "both"):
            self._auto_state["last_saturday_auto_trigger_ts"] = None
            cleared.append("saturday")
        _save_auto_state(self._auto_state)
        await interaction.response.send_message(
            f"✅ Cleared cooldown(s): {', '.join(cleared)}.", ephemeral=True
        )
        logger.info("[PrimeTime] Cooldown(s) cleared by %s: %s", interaction.user, cleared)

    @primetime_group.command(name="reset_counter", description="Clear an auto-trigger counter (admin testing)")
    @app_commands.describe(kind="Which counter to clear")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (rolling 60-min deque)", value="daily"),
        app_commands.Choice(name="Saturday — bi-weekly (today's count)", value="saturday"),
        app_commands.Choice(name="Both", value="both"),
    ])
    async def primetime_reset_counter(self, interaction: discord.Interaction,
                                      kind: app_commands.Choice[str]) -> None:
        cleared: list[str] = []
        if kind.value in ("daily", "both"):
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            cleared.append("daily")
        if kind.value in ("saturday", "both"):
            self._auto_state["saturday_count"] = 0
            self._auto_state["last_saturday_nudge_stage"] = 0
            cleared.append("saturday")
        _save_auto_state(self._auto_state)
        await interaction.response.send_message(
            f"✅ Cleared counter(s): {', '.join(cleared)}.", ephemeral=True
        )
        logger.info("[PrimeTime] Counter(s) cleared by %s: %s", interaction.user, cleared)

    @primetime_group.command(name="stats", description="Cumulative Prime Time fire counts and last-fire times")
    async def primetime_stats(self, interaction: discord.Interaction) -> None:
        daily = int(self._auto_state.get("daily_fire_count", 0))
        saturday = int(self._auto_state.get("saturday_fire_count", 0))
        manual = int(self._auto_state.get("manual_fire_count", 0))
        extensions = int(self._auto_state.get("extension_count", 0))
        total = daily + saturday + manual

        lines: list[str] = ["📊 **Prime Time Stats** _(since counters were introduced)_", ""]
        lines.append(f"• Total fires: **{total}**")
        lines.append(f"  - Daily (auto): {daily}")
        lines.append(f"  - Saturday (bi-weekly auto): {saturday}")
        lines.append(f"  - Manual (slash command): {manual}")
        lines.append(f"• Cross-kind extensions: **{extensions}**")
        lines.append("")

        last_d = self._auto_state.get("last_daily_auto_trigger_ts")
        last_s = self._auto_state.get("last_saturday_auto_trigger_ts")
        if last_d:
            lines.append(f"• Last daily fire: <t:{int(last_d)}:F> (<t:{int(last_d)}:R>)")
        else:
            lines.append("• Last daily fire: _never_")
        if last_s:
            lines.append(f"• Last Saturday fire: <t:{int(last_s)}:F> (<t:{int(last_s)}:R>)")
        else:
            lines.append("• Last Saturday fire: _never_")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @primetime_group.command(name="force_fire", description="Force-fire an auto Prime Time (admin testing)")
    @app_commands.describe(kind="Which auto-trigger to fire as if its goal had been hit")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (60 min)", value="daily"),
        app_commands.Choice(name="Saturday — bi-weekly (4h)", value="saturday"),
    ])
    async def primetime_force_fire(self, interaction: discord.Interaction,
                                   kind: app_commands.Choice[str]) -> None:
        if self._active:
            await interaction.response.send_message(
                f"❌ A `{self._active_kind}` Prime Time is already active. "
                "Stop it with `/primetime stop` first.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        if kind.value == "daily":
            count = max(_DAILY_GOAL, len(self._recent_feedbacks))
            await self._fire_auto("daily", _DAILY_DURATION_MINUTES, count=count)
            self._auto_state["last_daily_auto_trigger_ts"] = time.time()
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
        else:  # saturday
            count = max(_SATURDAY_GOAL, int(self._auto_state.get("saturday_count", 0)))
            await self._fire_auto("saturday", _SATURDAY_DURATION_MINUTES, count=count)
            self._auto_state["last_saturday_auto_trigger_ts"] = time.time()
            self._auto_state["saturday_count"] = 0
            self._auto_state["last_saturday_nudge_stage"] = 0
        _save_auto_state(self._auto_state)
        await interaction.followup.send(
            f"✅ Force-fired `{kind.value}` Prime Time. Cooldown is now active.", ephemeral=True
        )
        logger.info("[PrimeTime] Force-fired %s by %s", kind.value, interaction.user)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrimeTime(bot))
