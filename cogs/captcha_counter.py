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
    (0,    "Awaiting First Contact", discord.Color.from_rgb(170, 170, 170),
     "The defense grid is online. No threats yet."),
    (1,    "Rookie Defender",        discord.Color.gold(),
     "First catch. The captcha gate held."),
    (10,   "Sentinel",               discord.Color.orange(),
     "The bots are testing the gate. The gate doesn't blink."),
    (50,   "Captcha Master",         discord.Color.red(),
     "Half a hundred attempts denied. Word travels fast in botnet circles."),
    (100,  "Bot Reaper",             discord.Color.dark_red(),
     "Triple digits. Somewhere a botnet operator is updating their spreadsheet."),
    (500,  "MF DEMIGOD",             discord.Color.purple(),
     "Five hundred souls turned away. Folk songs are being written about this server."),
    (1000, "FORTRESS ETERNAL",       discord.Color.from_rgb(60, 0, 90),
     "Four digits. The walls are made of bones now. The bots know fear."),
]

_FOOTERS = [
    "Each number is a bot that thought it had a chance.",
    "Captcha.bot, silently doing the lord's work.",
    "Welcome to the wall. The bots are not.",
    "Tonight on MF: another bot eats dirt.",
    "This channel pays rent in deflated egos.",
    "Sleep tight. The grid is watching.",
    "Captchas: the great filter.",
]

# One-time celebration thresholds posted as their own message in the channel
# when crossed. Comparing by equality to current count guarantees once-only.
_MILESTONES: dict[int, str] = {
    1:    "🎉 **First catch!** The Defense Grid has tasted bot.",
    10:   "🔟 **Ten bots down.** Captcha.bot stretches its claws.",
    25:   "🦾 **Twenty-five.** They keep coming. We keep winning.",
    50:   "💀 **Fifty bots denied.** Halfway to triple digits.",
    100:  "🏆 **TRIPLE DIGITS.** The grid bows to no bot.",
    250:  "🔥 **250 souls collected.** Captcha.bot is unstoppable.",
    500:  "⚡ **500 BOTS.** Welcome to MF DEMIGOD status.",
    1000: "👑 **FOUR. ZEROS.** This isn't a server anymore — it's a fortress.",
    2500: "🌌 **2,500 catches.** Bot insurance companies hate this server.",
    5000: "🛸 **5,000.** At this point we should be writing papers.",
}


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
        return {"count": 0, "message_id": None, "last_catch_ts": None}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "count": int(data.get("count", 0)),
            "message_id": data.get("message_id"),
            "last_catch_ts": data.get("last_catch_ts"),
        }
    except Exception:
        logger.error("Could not load captcha counter state; starting fresh", exc_info=True)
        return {"count": 0, "message_id": None, "last_catch_ts": None}


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

        container = discord.ui.Container(
            discord.ui.TextDisplay("## 🛡️  MF CAPTCHA DEFENSE GRID  🛡️"),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(flavor),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            discord.ui.TextDisplay(
                f"**Rank:** {tier_name}\n**Last Catch:** {last_catch}"
            ),
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

    async def _announce_milestone(self, count: int):
        text = _MILESTONES.get(count)
        if text is None:
            return
        channel = await self._get_counter_channel()
        if channel is None:
            return
        try:
            await channel.send(text)
        except discord.HTTPException:
            logger.error("Failed to send milestone message", exc_info=True)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._sync_counter_message()

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.action != discord.AuditLogAction.kick:
            return
        if entry.user is None or entry.user.id != CAPTCHA_BOT_ID:
            return

        self.state["count"] = int(self.state.get("count", 0)) + 1
        self.state["last_catch_ts"] = int(time.time())
        _save_state(self.state)
        logger.info(
            "Captcha counter bumped to %d (kick entry %s, target %s)",
            self.state["count"], entry.id, entry.target.id if entry.target else "?",
        )

        await self._sync_counter_message()
        await self._announce_milestone(self.state["count"])


async def setup(bot: commands.Bot):
    await bot.add_cog(CaptchaCounter(bot))
