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
_DEFAULT_DAILY_GOAL = 5                  # default threshold; editable via /primetime set_goal
_DAILY_DURATION_MINUTES = 60
_DAILY_COOLDOWN_HOURS = 24

# Bi-weekly: accumulates quality feedbacks across a 14-day window, any day.
# Fires when the goal is reached; window resets on fire or on 14-day expiry.
_DEFAULT_BI_WEEKLY_GOAL = 50             # default threshold; editable via /primetime set_goal
_BI_WEEKLY_DURATION_MINUTES = 240        # 4 hours
_BI_WEEKLY_WINDOW_DAYS = 14

# Sanity cap for admin-editable values to guard against typos.
_GOAL_MAX = 1000
_COUNT_MAX = 1000

# ── Build-up nudges ────────────────────────────────────────────────────────
# As the rolling counter climbs toward the daily goal, post a single message
# each time it crosses a new stage. Pools per stage so it doesn't get stale.
# Goal-hit (count = daily_goal) fires Prime Time itself and skips nudges.
# Stages are sized for the default goal of 5; they don't scale automatically
# if the goal is edited.
_NUDGE_STAGES = (2, 3, 4)

# Bi-weekly nudges fire as bi_weekly_count climbs across the 14-day window.
# Festival theming, day-agnostic. Stages tuned for the default goal of 50.
_BI_WEEKLY_NUDGE_STAGES = (10, 25, 40, 49)

_BI_WEEKLY_NUDGES: dict[int, list[str]] = {
    10: [
        "🎪 **Bi-weekly Headliner Tour** kicking off · **{count}/{goal}** quality MFRs banked.",
        "🎟️ Stage going up for the **bi-weekly headliner** · **{count}/{goal}**.",
        "🚛 Gear's loading in for the **bi-weekly main event** · **{count}/{goal}**.",
        "🎤 Opener's set — **bi-weekly show** forming · **{count}/{goal}**.",
    ],
    25: [
        "🎸 Half-house · **{count}/{goal}**. **Bi-weekly headliner** warming up backstage.",
        "🥁 Main stage filling · **{count}/{goal}**. Halfway to the **bi-weekly show**.",
        "🎶 Mid-festival energy · **{count}/{goal}**. {remaining} away from the bi-weekly headliner.",
        "🎟️ Half the tickets sold · **{count}/{goal}** quality feedbacks for the **bi-weekly set**.",
    ],
    40: [
        "🔊 **Bi-weekly headliner** about to take stage · **{count}/{goal}**. {remaining} more to fire.",
        "🎶 Lights dimming on the main stage · **{count}/{goal}**. {remaining} to go on the **bi-weekly show**.",
        "🎤 Backstage announces the **bi-weekly headliner** · **{count}/{goal}**. {remaining} away.",
        "🎸 Crowd packing in for the **bi-weekly main event** · **{count}/{goal}**.",
    ],
    49: [
        "🎟️ Curtain rising on the **bi-weekly show** · **{count}/{goal}**. One quality `<MFR` away.",
        "🔥 **Bi-weekly headliner** one feedback away · **{count}/{goal}**.",
        "🎤 Spotlight's on · **{count}/{goal}**. One more for the **bi-weekly main event**.",
        "🎶 Final ticket at the door for the **bi-weekly show** · **{count}/{goal}**. One quality `<MFR` and lights go down.",
    ],
}


_NUDGES: dict[int, list[str]] = {
    2: [
        "🎤 Opener's warming up · **{count}/{goal}** quality MFRs in the hour.",
        "🥁 Soundcheck · **{count}/{goal}**. The setlist's forming.",
        "🎶 Doors are open · **{count}/{goal}** quality feedbacks tracking.",
        "🎸 First song landed · **{count}/{goal}**. Crowd's filing in.",
    ],
    3: [
        "🎸 Mid-set vibes · **{count}/{goal}**. Halfway to the encore call.",
        "🎤 Set's in full swing · **{count}/{goal}**. {remaining} songs from encore.",
        "🥁 Past halfway · **{count}/{goal}**. The crowd's locked in.",
        "🎶 Mid-set energy · **{count}/{goal}**. {remaining} more 'til the encore.",
    ],
    4: [
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
        "last_bi_weekly_auto_trigger_ts": None,
        "bi_weekly_window_start_ts": None,
        "bi_weekly_count": 0,
        # Highest bi-weekly nudge stage already posted for the current window —
        # persisted so a restart mid-window doesn't re-post the same nudge.
        "last_bi_weekly_nudge_stage": 0,
        # Persisted daily rolling deque — list of epoch timestamps. Rebuilt
        # into _recent_feedbacks on startup, pruned to the trailing 60 min.
        "daily_rolling_ts": [],
        # Admin-editable goals; default to the module constants.
        "daily_goal": _DEFAULT_DAILY_GOAL,
        "bi_weekly_goal": _DEFAULT_BI_WEEKLY_GOAL,
        # Active-event snapshot — persisted so a restart mid-event can resume
        # the 2x window instead of silently losing it.
        "active_kind": None,           # "manual" | "daily" | "biweekly"
        "active_start_ts": None,       # epoch seconds
        "active_duration_minutes": 0,
        # Live "Bi-weekly progress" message in GENERAL_CHAT_CHANNEL_ID. Updated
        # in place on each quality feedback; cleared when the window resets
        # or bi-weekly Prime Time fires.
        "bi_weekly_progress_message_id": None,
        "bi_weekly_progress_channel_id": None,
        # Cumulative fire/extension counters surfaced via /primetime stats.
        "daily_fire_count": 0,
        "bi_weekly_fire_count": 0,
        "manual_fire_count": 0,
        "extension_count": 0,
    }
    if not _STATE_FILE.exists():
        return default
    try:
        with _STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        logger.error("Could not load prime-time auto-trigger state; starting fresh", exc_info=True)
        return default

    _migrate_saturday_keys(data)
    for k, v in default.items():
        data.setdefault(k, v)
    return data


def _migrate_saturday_keys(data: dict) -> None:
    """One-time rename of legacy saturday_* keys to bi_weekly_*.

    Copies old → new only when the old key exists and the new one is absent.
    Also rewrites active_kind == 'saturday' to 'biweekly' so an in-flight
    Saturday event resumes correctly under the new naming.
    """
    renames = (
        ("saturday_count", "bi_weekly_count"),
        ("saturday_window_start_ts", "bi_weekly_window_start_ts"),
        ("last_saturday_nudge_stage", "last_bi_weekly_nudge_stage"),
        ("saturday_progress_message_id", "bi_weekly_progress_message_id"),
        ("saturday_progress_channel_id", "bi_weekly_progress_channel_id"),
        ("saturday_fire_count", "bi_weekly_fire_count"),
        ("last_saturday_auto_trigger_ts", "last_bi_weekly_auto_trigger_ts"),
    )
    for old, new in renames:
        if old in data and new not in data:
            data[new] = data[old]
    if data.get("active_kind") == "saturday":
        data["active_kind"] = "biweekly"


def _save_auto_state(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, _STATE_FILE)


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
        self._auto_state: dict = _load_auto_state()
        self._recent_feedbacks: deque[float] = deque()
        self._restore_daily_rolling()

        # Highest hype-train stage we've already announced this cycle. Reset
        # to 0 when the rolling window dips below the first stage or after
        # Prime Time fires.
        self._last_nudge_stage: int = self._nudge_stage_for(len(self._recent_feedbacks))
        self._auto_trigger_lock: asyncio.Lock = asyncio.Lock()
        # Tracks whether the *current* active event was auto-triggered (daily
        # or biweekly) — controls which extension branch to apply.
        self._active_kind: str | None = None  # "manual" | "daily" | "biweekly"

    # ── State helpers ─────────────────────────────────────────────────────────

    @property
    def _daily_goal(self) -> int:
        return int(self._auto_state.get("daily_goal", _DEFAULT_DAILY_GOAL))

    @property
    def _bi_weekly_goal(self) -> int:
        return int(self._auto_state.get("bi_weekly_goal", _DEFAULT_BI_WEEKLY_GOAL))

    def _restore_daily_rolling(self) -> None:
        """Rebuild _recent_feedbacks from persisted timestamps, pruning to
        the trailing 60 minutes. Save back if anything was dropped."""
        raw = self._auto_state.get("daily_rolling_ts") or []
        cutoff = time.time() - _DAILY_WINDOW_SECONDS
        survivors = [float(ts) for ts in raw if float(ts) >= cutoff]
        survivors.sort()
        self._recent_feedbacks.clear()
        for ts in survivors:
            self._recent_feedbacks.append(ts)
        if len(survivors) != len(raw):
            self._auto_state["daily_rolling_ts"] = survivors
            _save_auto_state(self._auto_state)

    def _persist_daily_rolling(self) -> None:
        self._auto_state["daily_rolling_ts"] = list(self._recent_feedbacks)
        _save_auto_state(self._auto_state)

    def _nudge_stage_for(self, count: int) -> int:
        return max((s for s in _NUDGE_STAGES if s <= count), default=0)

    def _bi_weekly_nudge_stage_for(self, count: int) -> int:
        return max((s for s in _BI_WEEKLY_NUDGE_STAGES if s <= count), default=0)

    def _maybe_reset_bi_weekly_window(self, now_ts: float) -> bool:
        """Reset the bi-weekly window if it's been open ≥ 14 days without firing.
        Returns True if a reset occurred."""
        start = self._auto_state.get("bi_weekly_window_start_ts")
        if start is None:
            return False
        if now_ts - float(start) < _BI_WEEKLY_WINDOW_DAYS * 86400:
            return False
        self._auto_state["bi_weekly_count"] = 0
        self._auto_state["bi_weekly_window_start_ts"] = now_ts
        self._auto_state["last_bi_weekly_nudge_stage"] = 0
        _save_auto_state(self._auto_state)
        # Live progress message is per-window; tear it down on reset.
        asyncio.create_task(self._clear_bi_weekly_progress_message())
        logger.info("[PrimeTime] Bi-weekly window expired without firing — counter reset")
        return True

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
        """Resume a Prime Time event that was active when the bot went down,
        and reconcile the bi-weekly window in case it expired during downtime."""
        # Bi-weekly window expiration check on every ready (cheap, idempotent).
        self._maybe_reset_bi_weekly_window(time.time())

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

        Maintains a rolling 60-min counter and a 14-day bi-weekly counter, and
        fires (or extends) Prime Time when their thresholds are crossed.
        Errors here must not break the feedback pipeline — every public path
        is wrapped in try/except."""
        try:
            async with self._auto_trigger_lock:
                now_ts = time.time()

                self._record_rolling(now_ts)
                self._record_bi_weekly(now_ts)

                await self._evaluate_daily(now_ts)
                await self._evaluate_bi_weekly(now_ts)
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
        self._persist_daily_rolling()

    def _record_bi_weekly(self, now_ts: float) -> None:
        # First MFR after a fresh state file — stamp the window-start.
        if self._auto_state.get("bi_weekly_window_start_ts") is None:
            self._auto_state["bi_weekly_window_start_ts"] = now_ts
            self._auto_state["bi_weekly_count"] = 0
            self._auto_state["last_bi_weekly_nudge_stage"] = 0
        # Reset on window expiry (≥ 14 days). After this, the upcoming bump
        # starts a fresh window's count at 1.
        self._maybe_reset_bi_weekly_window(now_ts)
        self._auto_state["bi_weekly_count"] = int(self._auto_state.get("bi_weekly_count", 0)) + 1
        _save_auto_state(self._auto_state)

    async def _evaluate_daily(self, now_ts: float) -> None:
        count = len(self._recent_feedbacks)
        goal = self._daily_goal
        if count < goal:
            # Below the goal — maybe post a build-up nudge.
            if self._active:
                # Don't nudge while Prime Time is already running.
                return
            new_stage = self._nudge_stage_for(count)
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
            self._persist_daily_rolling()
            return

        if self._active and self._active_kind in ("daily", "manual"):
            # Same-kind re-trigger or admin-set event — drain the burst, no extension.
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            self._persist_daily_rolling()
            return

        if self._active and self._active_kind == "biweekly":
            # Cross-kind overlap — Daily would have fired during an active
            # Bi-weekly. Stack its duration onto the remaining window.
            await self._extend_active(_DAILY_DURATION_MINUTES, "daily goal hit during the bi-weekly show")
            self._auto_state["last_daily_auto_trigger_ts"] = now_ts
            _save_auto_state(self._auto_state)
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            self._persist_daily_rolling()
            return

        # Nothing active — fire fresh.
        await self._fire_auto("daily", _DAILY_DURATION_MINUTES, count=count)
        self._auto_state["last_daily_auto_trigger_ts"] = now_ts
        _save_auto_state(self._auto_state)
        self._recent_feedbacks.clear()
        self._last_nudge_stage = 0
        self._persist_daily_rolling()

    async def _evaluate_bi_weekly(self, now_ts: float) -> None:
        count = int(self._auto_state.get("bi_weekly_count", 0))
        goal = self._bi_weekly_goal

        if count < goal:
            # Below the goal — refresh the live progress message and maybe
            # post a stage nudge. Skip both while a Prime Time is active so
            # we don't double-up announcements.
            if not self._active:
                await self._sync_bi_weekly_progress_message(count)
                new_stage = self._bi_weekly_nudge_stage_for(count)
                last_stage = int(self._auto_state.get("last_bi_weekly_nudge_stage", 0))
                if new_stage > last_stage:
                    await self._post_bi_weekly_progress(count, new_stage)
                    self._auto_state["last_bi_weekly_nudge_stage"] = new_stage
                    _save_auto_state(self._auto_state)
            return

        if self._active and self._active_kind in ("biweekly", "manual"):
            # Same-kind re-trigger or admin-set event — reset window and counter,
            # no extension. The next 14-day cycle starts fresh.
            self._reset_bi_weekly_after_consumption(now_ts)
            return

        if self._active and self._active_kind == "daily":
            # Cross-kind overlap — Bi-weekly would have fired during an active
            # Daily. Stack its full duration onto the remaining Daily window.
            await self._extend_active(_BI_WEEKLY_DURATION_MINUTES, "bi-weekly goal hit during a daily Prime Time")
            self._auto_state["last_bi_weekly_auto_trigger_ts"] = now_ts
            self._reset_bi_weekly_after_consumption(now_ts)
            return

        # Nothing active — fire fresh.
        await self._fire_auto("biweekly", _BI_WEEKLY_DURATION_MINUTES, count=count)
        self._auto_state["last_bi_weekly_auto_trigger_ts"] = now_ts
        self._reset_bi_weekly_after_consumption(now_ts)

    def _reset_bi_weekly_after_consumption(self, now_ts: float) -> None:
        """Reset the bi-weekly counter and start a fresh 14-day window.
        Called after a fire, an extension, or any other point where the
        accumulated progress has been 'spent'."""
        self._auto_state["bi_weekly_count"] = 0
        self._auto_state["bi_weekly_window_start_ts"] = now_ts
        self._auto_state["last_bi_weekly_nudge_stage"] = 0
        _save_auto_state(self._auto_state)

    async def _post_bi_weekly_progress(self, count: int, stage: int) -> None:
        channel = self.bot.get_channel(AUDIO_FEEDBACK)
        if channel is None:
            return
        pool = _BI_WEEKLY_NUDGES.get(stage)
        if not pool:
            return
        goal = self._bi_weekly_goal
        message = random.choice(pool).format(
            count=count,
            goal=goal,
            remaining=max(0, goal - count),
        )
        try:
            await channel.send(message)
        except Exception:
            logger.error("[PrimeTime] Failed to post bi-weekly nudge", exc_info=True)

    def _build_bi_weekly_progress_text(self, count: int) -> str:
        goal = self._bi_weekly_goal
        remaining = max(0, goal - count)
        bar_total = 20
        filled = min(bar_total, round(bar_total * count / max(1, goal)))
        bar = "█" * filled + "░" * (bar_total - filled)
        window_start = self._auto_state.get("bi_weekly_window_start_ts")
        window_line = ""
        if window_start:
            window_end_ts = int(float(window_start) + _BI_WEEKLY_WINDOW_DAYS * 86400)
            window_line = f"\nWindow resets <t:{window_end_ts}:R> if not fired."
        return (
            f"🎪 **Bi-weekly Headliner — Live Progress**\n"
            f"`{bar}` **{count}/{goal}** quality `<MFR` banked · "
            f"{remaining} to fire the {_BI_WEEKLY_DURATION_MINUTES // 60}-hour Prime Time."
            f"{window_line}"
        )

    async def _sync_bi_weekly_progress_message(self, count: int) -> None:
        """Post or edit the running 'X/goal' display in GENERAL_CHAT_CHANNEL_ID."""
        channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)
        if channel is None:
            return

        text = self._build_bi_weekly_progress_text(count)
        msg_id = self._auto_state.get("bi_weekly_progress_message_id")
        msg_channel_id = self._auto_state.get("bi_weekly_progress_channel_id")

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
                logger.warning("[PrimeTime] Bi-weekly progress message missing; posting a fresh one")
            except discord.HTTPException:
                logger.error("[PrimeTime] Failed to edit bi-weekly progress message", exc_info=True)
                return

        try:
            msg = await channel.send(text)
        except discord.HTTPException:
            logger.error("[PrimeTime] Failed to post bi-weekly progress message", exc_info=True)
            return
        self._auto_state["bi_weekly_progress_message_id"] = msg.id
        self._auto_state["bi_weekly_progress_channel_id"] = GENERAL_CHAT_CHANNEL_ID
        _save_auto_state(self._auto_state)

    async def _clear_bi_weekly_progress_message(self) -> None:
        """Delete the live progress message (if any) and clear the stored id.
        Called on window reset and on bi-weekly Prime Time fire."""
        msg_id = self._auto_state.get("bi_weekly_progress_message_id")
        channel_id = self._auto_state.get("bi_weekly_progress_channel_id")
        self._auto_state["bi_weekly_progress_message_id"] = None
        self._auto_state["bi_weekly_progress_channel_id"] = None
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
            logger.warning("[PrimeTime] Bi-weekly progress message already deleted")
        except discord.HTTPException:
            logger.warning("[PrimeTime] Could not delete stale bi-weekly progress message", exc_info=True)

    async def _fire_auto(self, kind: str, minutes: int, *, count: int) -> None:
        self._active = True
        self._active_kind = kind
        self._start_time = datetime.now(timezone.utc)
        self._duration = minutes
        self._timer_task = asyncio.create_task(self._run_timer(minutes * 60))
        self._timer_task.add_done_callback(_log_task_error)
        self._persist_active()

        # Bump cumulative fire counter for /primetime stats.
        counter_key = "bi_weekly_fire_count" if kind == "biweekly" else "daily_fire_count"
        self._auto_state[counter_key] = int(self._auto_state.get(counter_key, 0)) + 1
        _save_auto_state(self._auto_state)

        # Bi-weekly Prime Time replaces the live progress message — pull it
        # down so chat doesn't show the running "X/goal" alongside the fire.
        if kind == "biweekly":
            await self._clear_bi_weekly_progress_message()

        start_ts = int(self._start_time.timestamp())
        end_ts = start_ts + minutes * 60

        if kind == "daily":
            prefix = "🎟️ **THE SHOW'S ON**"
            why = (
                f"_Encore unlocked by **{count} quality feedbacks** in the last hour. "
                f"Lights go down for {minutes} minutes — give quality critical feedback now to earn 2x._"
            )
        elif kind == "biweekly":
            prefix = "🎟️ **BI-WEEKLY HEADLINER**"
            hours = minutes // 60
            why = (
                f"_The bi-weekly headliner takes the stage — unlocked by **{count} quality feedbacks** "
                f"banked across the window. Lights stay down for {minutes} minutes ({hours}-hour set). "
                f"Next window starts fresh now._"
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
        event (Daily↔Bi-weekly overlap)."""
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
        goal = self._daily_goal
        message = random.choice(pool).format(
            count=count,
            goal=goal,
            remaining=max(0, goal - count),
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
        daily_goal = self._daily_goal
        lines.append("")
        lines.append(f"**Daily auto-trigger** ({daily_goal}/hr rolling, 24h cooldown):")
        lines.append(f"• Rolling counter: **{len(self._recent_feedbacks)}/{daily_goal}** in last 60 min")
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

        # Bi-weekly auto block
        bw_goal = self._bi_weekly_goal
        bw_count = int(self._auto_state.get("bi_weekly_count", 0))
        bw_start = self._auto_state.get("bi_weekly_window_start_ts")
        last_b = self._auto_state.get("last_bi_weekly_auto_trigger_ts")

        lines.append("")
        lines.append(f"**Bi-weekly auto-trigger** ({bw_goal} quality MFRs across {_BI_WEEKLY_WINDOW_DAYS} days, any day):")
        lines.append(f"• Counter: **{bw_count}/{bw_goal}**")
        if bw_start:
            bw_start_ts = int(float(bw_start))
            bw_end_ts = bw_start_ts + _BI_WEEKLY_WINDOW_DAYS * 86400
            lines.append(f"• Window opened: <t:{bw_start_ts}:F>")
            lines.append(f"• Window resets: <t:{bw_end_ts}:F> (<t:{bw_end_ts}:R>)")
        else:
            lines.append("• Window: _not started yet — next quality MFR opens it_")
        if last_b:
            lines.append(f"• Last fire: <t:{int(last_b)}:F>")
        else:
            lines.append("• Last fire: _never_")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @primetime_group.command(name="reset_cooldown", description="Clear the daily auto-trigger cooldown (admin testing)")
    async def primetime_reset_cooldown(self, interaction: discord.Interaction) -> None:
        self._auto_state["last_daily_auto_trigger_ts"] = None
        _save_auto_state(self._auto_state)
        await interaction.response.send_message(
            "✅ Cleared daily cooldown.", ephemeral=True
        )
        logger.info("[PrimeTime] Daily cooldown cleared by %s", interaction.user)

    @primetime_group.command(name="reset_counter", description="Clear an auto-trigger counter (admin testing)")
    @app_commands.describe(kind="Which counter to clear")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (rolling 60-min deque)", value="daily"),
        app_commands.Choice(name="Bi-weekly (14-day window count)", value="biweekly"),
        app_commands.Choice(name="Both", value="both"),
    ])
    async def primetime_reset_counter(self, interaction: discord.Interaction,
                                      kind: app_commands.Choice[str]) -> None:
        cleared: list[str] = []
        if kind.value in ("daily", "both"):
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            self._persist_daily_rolling()
            cleared.append("daily")
        if kind.value in ("biweekly", "both"):
            self._reset_bi_weekly_after_consumption(time.time())
            await self._clear_bi_weekly_progress_message()
            cleared.append("biweekly")
        await interaction.response.send_message(
            f"✅ Cleared counter(s): {', '.join(cleared)}.", ephemeral=True
        )
        logger.info("[PrimeTime] Counter(s) cleared by %s: %s", interaction.user, cleared)

    @primetime_group.command(name="set_goal", description="Set a goal (cap) for a Prime Time auto-trigger")
    @app_commands.describe(kind="Which goal to set", value="New goal value (1-1000)")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (per-hour rolling)", value="daily"),
        app_commands.Choice(name="Bi-weekly (14-day window)", value="biweekly"),
    ])
    async def primetime_set_goal(self, interaction: discord.Interaction,
                                 kind: app_commands.Choice[str], value: int) -> None:
        if value <= 0 or value > _GOAL_MAX:
            await interaction.response.send_message(
                f"❌ Goal must be between 1 and {_GOAL_MAX}.", ephemeral=True
            )
            return
        if kind.value == "daily":
            self._auto_state["daily_goal"] = value
            label = "Daily"
        else:
            self._auto_state["bi_weekly_goal"] = value
            label = "Bi-weekly"
        _save_auto_state(self._auto_state)
        await interaction.response.send_message(
            f"✅ {label} goal set to **{value}**. "
            f"(Note: nudge stages are tuned for the default goals and don't auto-scale.)",
            ephemeral=True,
        )
        logger.info("[PrimeTime] %s goal set to %d by %s", label, value, interaction.user)

    @primetime_group.command(name="set_count", description="Set the current counter for a Prime Time auto-trigger")
    @app_commands.describe(kind="Which counter to set", value="New counter value (0-1000)")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (rolling 60-min deque)", value="daily"),
        app_commands.Choice(name="Bi-weekly (14-day window count)", value="biweekly"),
    ])
    async def primetime_set_count(self, interaction: discord.Interaction,
                                  kind: app_commands.Choice[str], value: int) -> None:
        if value < 0 or value > _COUNT_MAX:
            await interaction.response.send_message(
                f"❌ Count must be between 0 and {_COUNT_MAX}.", ephemeral=True
            )
            return

        now_ts = time.time()
        if kind.value == "daily":
            self._recent_feedbacks.clear()
            for _ in range(value):
                self._recent_feedbacks.append(now_ts)
            self._last_nudge_stage = self._nudge_stage_for(value)
            self._persist_daily_rolling()
            extra = (
                "\n⚠️ All injected entries share the same timestamp, so they'll "
                "all expire from the 60-min window together."
                if value > 0 else ""
            )
            await interaction.response.send_message(
                f"✅ Daily counter set to **{value}/{self._daily_goal}**.{extra}",
                ephemeral=True,
            )
        else:
            if value == 0:
                self._reset_bi_weekly_after_consumption(now_ts)
                await self._clear_bi_weekly_progress_message()
                window_note = " Window reset; fresh 14-day cycle starts now."
            else:
                # Preserve current window; just rewrite the count and recompute
                # the nudge marker.
                if self._auto_state.get("bi_weekly_window_start_ts") is None:
                    self._auto_state["bi_weekly_window_start_ts"] = now_ts
                self._auto_state["bi_weekly_count"] = value
                self._auto_state["last_bi_weekly_nudge_stage"] = self._bi_weekly_nudge_stage_for(value)
                _save_auto_state(self._auto_state)
                window_start = self._auto_state.get("bi_weekly_window_start_ts")
                window_end_ts = int(float(window_start) + _BI_WEEKLY_WINDOW_DAYS * 86400)
                window_note = f" Window unchanged; resets <t:{window_end_ts}:R>."
            await interaction.response.send_message(
                f"✅ Bi-weekly counter set to **{value}/{self._bi_weekly_goal}**.{window_note}",
                ephemeral=True,
            )
        logger.info("[PrimeTime] %s counter set to %d by %s", kind.value, value, interaction.user)

    @primetime_group.command(name="stats", description="Cumulative Prime Time fire counts and last-fire times")
    async def primetime_stats(self, interaction: discord.Interaction) -> None:
        daily = int(self._auto_state.get("daily_fire_count", 0))
        bi_weekly = int(self._auto_state.get("bi_weekly_fire_count", 0))
        manual = int(self._auto_state.get("manual_fire_count", 0))
        extensions = int(self._auto_state.get("extension_count", 0))
        total = daily + bi_weekly + manual

        lines: list[str] = ["📊 **Prime Time Stats** _(since counters were introduced)_", ""]
        lines.append(f"• Total fires: **{total}**")
        lines.append(f"  - Daily (auto): {daily}")
        lines.append(f"  - Bi-weekly (auto): {bi_weekly}")
        lines.append(f"  - Manual (slash command): {manual}")
        lines.append(f"• Cross-kind extensions: **{extensions}**")
        lines.append("")

        last_d = self._auto_state.get("last_daily_auto_trigger_ts")
        last_b = self._auto_state.get("last_bi_weekly_auto_trigger_ts")
        if last_d:
            lines.append(f"• Last daily fire: <t:{int(last_d)}:F> (<t:{int(last_d)}:R>)")
        else:
            lines.append("• Last daily fire: _never_")
        if last_b:
            lines.append(f"• Last bi-weekly fire: <t:{int(last_b)}:F> (<t:{int(last_b)}:R>)")
        else:
            lines.append("• Last bi-weekly fire: _never_")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @primetime_group.command(name="force_fire", description="Force-fire an auto Prime Time (admin testing)")
    @app_commands.describe(kind="Which auto-trigger to fire as if its goal had been hit")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Daily (60 min)", value="daily"),
        app_commands.Choice(name="Bi-weekly (4h)", value="biweekly"),
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
        now_ts = time.time()
        if kind.value == "daily":
            count = max(self._daily_goal, len(self._recent_feedbacks))
            await self._fire_auto("daily", _DAILY_DURATION_MINUTES, count=count)
            self._auto_state["last_daily_auto_trigger_ts"] = now_ts
            self._recent_feedbacks.clear()
            self._last_nudge_stage = 0
            self._persist_daily_rolling()
        else:  # biweekly
            count = max(self._bi_weekly_goal, int(self._auto_state.get("bi_weekly_count", 0)))
            await self._fire_auto("biweekly", _BI_WEEKLY_DURATION_MINUTES, count=count)
            self._auto_state["last_bi_weekly_auto_trigger_ts"] = now_ts
            self._reset_bi_weekly_after_consumption(now_ts)
        await interaction.followup.send(
            f"✅ Force-fired `{kind.value}` Prime Time.", ephemeral=True
        )
        logger.info("[PrimeTime] Force-fired %s by %s", kind.value, interaction.user)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrimeTime(bot))
