"""Admin lookup of ML training samples by author.

Samples carry only a message ID, so to honor a deletion request we resolve each
sample's message in the audio-feedback channel and compare its author. Samples whose
original message was deleted can't be attributed (reported as "unresolved").
"""

import asyncio
import io
import json
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from data.constants import AUDIO_FEEDBACK, EXPORTS_CHANNEL

logger = logging.getLogger(__name__)

LOCAL_SAMPLE_FILE = "feedback_json.json"
_PREVIEW_CHARS = 160


def _parse_user_id(raw: str) -> int | None:
    """Accepts a bare ID, a <@id> mention, or text containing one."""
    match = re.search(r"\d{15,20}", raw)
    return int(match.group()) if match else None


def _read_local() -> list[dict]:
    try:
        with open(LOCAL_SAMPLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


class Samples(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(
        name="samples",
        description="ML training-sample tools.",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

    async def _collect_samples(self) -> list[dict]:
        """Local file + every JSON batch the bot posted to the exports channel, de-duplicated."""
        samples = await asyncio.to_thread(_read_local)

        channel = self.bot.get_channel(EXPORTS_CHANNEL)
        if channel is not None:
            async for msg in channel.history(limit=None):
                if msg.author.id != self.bot.user.id:
                    continue
                for att in msg.attachments:
                    if not att.filename.endswith(".json"):
                        continue
                    try:
                        samples.extend(json.loads(await att.read()))
                    except (json.JSONDecodeError, discord.HTTPException):
                        logger.warning("Could not read export attachment %s", att.url, exc_info=True)
        else:
            logger.warning("Exports channel %s not found; only local samples scanned", EXPORTS_CHANNEL)

        seen, unique = set(), []
        for sample in samples:
            mid = sample.get("message_id")
            if mid is not None and mid not in seen:
                seen.add(mid)
                unique.append(sample)
        return unique

    @group.command(name="find", description="List a user's ML training samples (by message ID).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="User ID or @mention (works for people who already left the server)")
    async def find(self, interaction: discord.Interaction, user: str):
        user_id = _parse_user_id(user)
        if user_id is None:
            await interaction.response.send_message("Give me a user ID or an @mention.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        logger.info("Sample lookup for user %s by admin %s", user_id, interaction.user.id)

        samples = await self._collect_samples()
        source = self.bot.get_channel(AUDIO_FEEDBACK)
        if source is None:
            await interaction.followup.send("Audio feedback channel not found.", ephemeral=True)
            return

        gate = asyncio.Semaphore(5)
        unresolved = 0
        matches: list[dict] = []

        async def check(sample: dict):
            nonlocal unresolved
            async with gate:
                try:
                    message = await source.fetch_message(int(sample["message_id"]))
                except discord.NotFound:
                    unresolved += 1
                    return
                except discord.HTTPException:
                    logger.warning("Could not fetch sample message %s", sample["message_id"], exc_info=True)
                    unresolved += 1
                    return
            if message.author.id == user_id:
                matches.append(sample)

        await asyncio.gather(*(check(s) for s in samples))

        header = (
            f"**Sample lookup for `{user_id}`**\n"
            f"Scanned {len(samples)} sample(s): **{len(matches)} match(es)**, "
            f"{unresolved} unresolved (original message deleted or unreachable — can't be attributed)."
        )
        if not matches:
            await interaction.followup.send(header, ephemeral=True)
            return

        matches.sort(key=lambda s: s.get("timestamp", ""))
        lines = []
        for s in matches:
            text = (s.get("feedback") or "").replace("\n", " ")
            if len(text) > _PREVIEW_CHARS:
                text = text[:_PREVIEW_CHARS - 1] + "…"
            label = "good" if s.get("rating") == 1 else "bad"
            lines.append(f"`{s['message_id']}` · {label} · {s.get('timestamp', '?')[:10]}\n> {text}")
        body = "\n".join(lines)

        if len(header) + len(body) < 1900:
            await interaction.followup.send(f"{header}\n{body}", ephemeral=True)
        else:
            file = discord.File(io.BytesIO(body.encode("utf-8")), filename=f"samples_{user_id}.txt")
            await interaction.followup.send(header, file=file, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Samples(bot))
