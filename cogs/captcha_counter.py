import json
import logging
import os
import random
import time
from pathlib import Path

import discord
from discord.ext import commands

from data.constants import CAPTCHA_BOT_ID, CAPTCHA_COUNTER_CHANNEL_ID

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "captcha_counter.json"

# Rank tiers: (threshold, name, embed color, flavor description).
# Walked bottom-up; the last tier whose threshold <= count wins.
_TIERS: list[tuple[int, str, discord.Color, str]] = [
    (0,     "Awaiting First Contact", discord.Color.from_rgb(170, 170, 170),
     "The defense grid is online. No threats yet."),
    (1,     "Rookie Defender",        discord.Color.gold(),
     "First catch. The captcha gate held."),
    (10,    "Sentinel",               discord.Color.orange(),
     "The bots are testing the gate. The gate doesn't blink."),
    (25,    "Gatekeeper",             discord.Color.from_rgb(230, 130, 0),
     "A quarter-hundred sent home crying. The pattern is forming."),
    (50,    "Captcha Master",         discord.Color.red(),
     "Half a hundred attempts denied. Word travels fast in botnet circles."),
    (100,   "Bot Reaper",             discord.Color.dark_red(),
     "Triple digits. Somewhere a botnet operator is updating their spreadsheet."),
    (250,   "Warden of the Wall",     discord.Color.from_rgb(140, 0, 0),
     "The wall has a name now. The bots whisper it before they vanish."),
    (500,   "MF DEMIGOD",             discord.Color.purple(),
     "Five hundred souls turned away. Folk songs are being written about this server."),
    (1000,  "FORTRESS ETERNAL",       discord.Color.from_rgb(60, 0, 90),
     "Four digits. The walls are made of bones now. The bots know fear."),
    (2500,  "EVENT HORIZON",          discord.Color.from_rgb(30, 0, 60),
     "Bots don't escape. Light barely does."),
    (5000,  "MYTHIC GUARDIAN",        discord.Color.from_rgb(10, 0, 40),
     "Five thousand. Botnet operators tell their grandkids about this place."),
]

_FOOTERS = [
    "Each number is a bot that thought it had a chance.",
    "Captcha.bot, silently doing the lord's work.",
    "Welcome to the wall. The bots are not.",
    "Tonight on MF: another bot eats dirt.",
    "This channel pays rent in deflated egos.",
    "Sleep tight. The grid is watching.",
    "Captchas: the great filter.",
    "Behind every catch: one very confused script.",
    "Brought to you by the people who said 'verify this'.",
    "Bots checked in. Bots did not check out.",
    "The captcha doesn't care about your feelings.",
    "Some doors are open. This one has a moat.",
    "Statistically, the next bot is already on its way.",
    "We do not negotiate with botnets.",
    "Another day, another digit.",
    "If you can read this, you passed.",
    "Powered by tiny puzzles and big grudges.",
    "The grid never sleeps. It just blinks slower.",
    "Today's forecast: scattered captchas, heavy losses for bots.",
    "Bot graveyard. No headstones. No mercy.",
    "Captcha.bot: undefeated. Untouched. Unbothered.",
    "Filed under: things that did not get past.",
    "The wall hears them coming.",
    "Bot in. Bot out. Bot upset.",
    "Yes, we count. We count everything.",
    "Spam folder, but cooler.",
    "The bouncer doesn't blink. Neither does this counter.",
    "Three captchas walked into a bar. None passed.",
    "The grid keeps a list. It is a long list.",
    "Some servers have lore. We have receipts.",
    "Behold: a number that goes up.",
    "Engagement metric of choice for sicko admins.",
    "Botnet QA team is in tears.",
    "Captchas before vibes. Always.",
    "Each tick is a tiny victory parade.",
    "Bots fear the gate. The gate fears nothing.",
    "Filed under W. All of them.",
    "Captcha.bot has been promoted. Again.",
    "Quietly, surgically, dismissively: rejected.",
    "The math is simple. The bots are not.",
    "Anti-spam, pro-vibes.",
    "Every catch funds a tiny celebration in dev's head.",
]

# One-time celebration thresholds posted as their own message in the channel
# when crossed. Comparing by equality to current count guarantees once-only.
_MILESTONES: dict[int, str] = {
    1:     "🎉 **First catch!** The Defense Grid has tasted bot.",
    5:     "✋ **Five down.** Captcha.bot is warming up.",
    10:    "🔟 **Ten bots down.** Captcha.bot stretches its claws.",
    25:    "🦾 **Twenty-five.** They keep coming. We keep winning.",
    50:    "💀 **Fifty bots denied.** Halfway to triple digits.",
    75:    "🧱 **Seventy-five.** The wall just keeps getting taller.",
    100:   "🏆 **TRIPLE DIGITS.** The grid bows to no bot.",
    150:   "🛡️ **150 catches.** Botnet operators have started a support group.",
    200:   "⚔️ **200 down.** This counter has its own gravitational pull.",
    250:   "🔥 **250 souls collected.** Captcha.bot is unstoppable.",
    333:   "🃏 **333.** Half-evil, fully effective.",
    500:   "⚡ **500 BOTS.** Welcome to MF DEMIGOD status.",
    666:   "😈 **666.** Even the bots are crossing themselves.",
    750:   "🏰 **750.** The keep stands.",
    1000:  "👑 **FOUR. ZEROS.** This isn't a server anymore — it's a fortress.",
    1337:  "🕹️ **1337.** Elite. Just like the wall.",
    2000:  "🚀 **2,000.** We have left the atmosphere.",
    2500:  "🌌 **2,500 catches.** Bot insurance companies hate this server.",
    5000:  "🛸 **5,000.** At this point we should be writing papers.",
    7500:  "📜 **7,500.** Future historians will struggle to explain this channel.",
    10000: "🌠 **TEN THOUSAND.** Captcha.bot accepts no further questions.",
}

# Sent and immediately deleted after each kick to nudge unread indicators in
# the sidebar — a quiet "hey, something happened" without leaving spam behind.
_CHAT_WARMERS = [
    "gotcha, bot",
    "another one",
    "denied",
    "nice try",
    "swing and a miss",
    "next",
    "rejected",
    "bot down",
    "see ya",
    "and stay out",
    "no.",
    "filtered",
    "nope",
    "byeeee",
    "captcha says no",
    "another tally",
    "blocked",
    "shoo",
    "thanks for playing",
    "click. denied.",
    "logged.",
    "boop. gone.",
]


def _tier_for(count: int) -> tuple[int, str, discord.Color, str]:
    chosen = _TIERS[0]
    for tier in _TIERS:
        if count >= tier[0]:
            chosen = tier
        else:
            break
    return chosen


def _button_style(count: int) -> discord.ButtonStyle:
    if count >= 50:
        return discord.ButtonStyle.danger
    if count >= 1:
        return discord.ButtonStyle.success
    return discord.ButtonStyle.secondary


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"count": 0, "message_id": None, "last_catch_ts": None, "last_milestone": 0}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "count": int(data.get("count", 0)),
            "message_id": data.get("message_id"),
            "last_catch_ts": data.get("last_catch_ts"),
            "last_milestone": int(data.get("last_milestone", 0)),
        }
    except Exception:
        logger.error("Could not load captcha counter state; starting fresh", exc_info=True)
        return {"count": 0, "message_id": None, "last_catch_ts": None, "last_milestone": 0}


def _latest_milestone(count: int) -> tuple[int, str] | None:
    """Highest milestone whose threshold <= count, or None if nothing crossed yet."""
    crossed = [(thr, text) for thr, text in _MILESTONES.items() if thr <= count]
    if not crossed:
        return None
    return max(crossed, key=lambda x: x[0])


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


class CounterDisplay(discord.ui.LayoutView):
    """Components V2 layout: a single Container holding the title, flavor,
    rank/last-catch line, the disabled count button, and a small footer line.
    Rendering puts the button visually inside the container's bordered card."""

    def __init__(self, state: dict):
        super().__init__(timeout=None)
        count = int(state.get("count", 0))
        _, tier_name, color, flavor = _tier_for(count)

        last_ts = state.get("last_catch_ts")
        last_catch = f"<t:{int(last_ts)}:R>" if last_ts else "never"
        footer = random.choice(_FOOTERS)

        milestone = _latest_milestone(count)
        rank_block = f"**Rank:** {tier_name}\n**Last Catch:** {last_catch}"
        if milestone is not None:
            rank_block = (
                f"**Rank:** {tier_name}\n"
                f"**Milestone:** {milestone[1]}\n"
                f"**Last Catch:** {last_catch}"
            )

        container = discord.ui.Container(
            discord.ui.TextDisplay("## 🛡️  MF CAPTCHA DEFENSE GRID  🛡️"),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(flavor),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(rank_block),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            discord.ui.ActionRow(
                discord.ui.Button(
                    label=f"Bots Caught: {count}",
                    emoji="🤖",
                    style=_button_style(count),
                    disabled=True,
                    custom_id="captcha_counter:display",
                )
            ),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(f"-# {footer}"),
            accent_color=color,
        )
        self.add_item(container)


class CaptchaCounter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = _load_state()

    async def _get_counter_channel(self):
        if not CAPTCHA_COUNTER_CHANNEL_ID:
            return None
        ch = self.bot.get_channel(CAPTCHA_COUNTER_CHANNEL_ID)
        if ch is not None:
            return ch
        try:
            return await self.bot.fetch_channel(CAPTCHA_COUNTER_CHANNEL_ID)
        except discord.HTTPException:
            logger.error("Could not fetch captcha counter channel", exc_info=True)
            return None

    async def _sync_counter_message(self):
        channel = await self._get_counter_channel()
        if channel is None:
            return

        view = CounterDisplay(self.state)
        msg_id = self.state.get("message_id")
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                try:
                    # Components V2 messages can't carry content/embeds, so
                    # explicitly clear those when editing in case the existing
                    # message was the older embed-based render.
                    await msg.edit(view=view, embed=None, content=None)
                    return
                except discord.HTTPException as e:
                    # Likely an embed -> V2 layout switch which Discord rejects
                    # via edit; fall through to delete + repost.
                    logger.info("Counter edit failed, recreating message: %s", e)
                    try:
                        await msg.delete()
                    except discord.HTTPException:
                        pass
            except discord.NotFound:
                logger.info("Stored captcha counter message missing; recreating")
            except discord.HTTPException:
                logger.error("Failed to fetch captcha counter message", exc_info=True)
                return

        try:
            msg = await channel.send(view=view)
        except discord.HTTPException:
            logger.error("Failed to send captcha counter message", exc_info=True)
            return
        self.state["message_id"] = msg.id
        _save_state(self.state)

    async def _chat_warmer_ping(self):
        """Send + immediately delete a tiny message so the channel surfaces
        as unread in the sidebar without leaving visible spam behind."""
        channel = await self._get_counter_channel()
        if channel is None:
            return
        try:
            msg = await channel.send(random.choice(_CHAT_WARMERS))
        except discord.HTTPException:
            logger.error("Chat warmer send failed", exc_info=True)
            return
        try:
            await msg.delete()
        except discord.HTTPException:
            logger.warning("Chat warmer delete failed; leaving message", exc_info=True)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._sync_counter_message()

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.action != discord.AuditLogAction.kick:
            return
        if entry.user is None or entry.user.id != CAPTCHA_BOT_ID:
            return

        new_count = int(self.state.get("count", 0)) + 1
        self.state["count"] = new_count
        self.state["last_catch_ts"] = int(time.time())

        latest = _latest_milestone(new_count)
        if latest is not None and latest[0] > int(self.state.get("last_milestone", 0)):
            self.state["last_milestone"] = latest[0]

        _save_state(self.state)
        logger.info(
            "Captcha counter bumped to %d (kick entry %s, target %s)",
            new_count, entry.id, entry.target.id if entry.target else "?",
        )

        await self._sync_counter_message()
        await self._chat_warmer_ping()


async def setup(bot: commands.Bot):
    await bot.add_cog(CaptchaCounter(bot))
