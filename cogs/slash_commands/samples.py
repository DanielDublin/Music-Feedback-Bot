"""Admin lookup of ML training samples by author.

Samples carry only a message ID, so to honor a deletion request we resolve each
sample's message in the audio-feedback channel and compare its author. Samples whose
original message was deleted can't be attributed (reported as "unresolved").
The lookup logic lives in ml_model/sample_store.py (shared with <mf deletedata).
"""

import io
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from ml_model.sample_store import collect_samples, find_user_messages

logger = logging.getLogger(__name__)

_PREVIEW_CHARS = 160


def _parse_user_id(raw: str) -> int | None:
    """Accepts a bare ID, a <@id> mention, or text containing one."""
    match = re.search(r"\d{15,20}", raw)
    return int(match.group()) if match else None


class Samples(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(
        name="samples",
        description="ML training-sample tools.",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

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

        samples = await collect_samples(self.bot)
        try:
            found, unresolved = await find_user_messages(self.bot, user_id, samples)
        except RuntimeError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        matches = [sample for sample, _ in found]

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
