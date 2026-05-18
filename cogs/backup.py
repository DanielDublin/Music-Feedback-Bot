"""Nightly backup of bot-local state files to DEV_SPAM.

Uploads a zip of feedback_threads.sqlite and data/*.json so the Discord-side
log channel doubles as crude offsite storage. The hosted MySQL has its own
snapshot story and is not included.
"""

import asyncio
import io
import logging
import zipfile
from datetime import datetime, time as dtime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from data.constants import DEV_SPAM

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files included in every snapshot. Anything missing on disk is skipped and
# noted in the upload summary — losing one file shouldn't block the rest.
_BACKUP_PATHS: list[Path] = [
    _PROJECT_ROOT / "feedback_threads.sqlite",
    _PROJECT_ROOT / "data" / "captcha_counter.json",
    _PROJECT_ROOT / "data" / "prime_time_state.json",
]

# 04:00 UTC chosen so the nightly fires comfortably outside US/EU prime-time
# server activity. Adjust if Discord uploads start failing during this window.
_BACKUP_TIME = dtime(hour=4, minute=0, tzinfo=timezone.utc)


class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nightly_backup.start()

    def cog_unload(self):
        self.nightly_backup.cancel()

    @tasks.loop(time=_BACKUP_TIME)
    async def nightly_backup(self):
        await self._run_backup(reason="nightly")

    @nightly_backup.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()

    async def _run_backup(self, *, reason: str) -> tuple[bool, str]:
        try:
            zip_bytes, included, skipped = await asyncio.to_thread(self._build_archive)
        except Exception:
            logger.error("Backup: archive build failed (%s)", reason, exc_info=True)
            return False, "archive build failed"

        if not included:
            logger.warning("Backup: no source files present on disk (%s)", reason)
            return False, "no source files present on disk"

        channel = self.bot.get_channel(DEV_SPAM)
        if channel is None:
            logger.error("Backup: DEV_SPAM channel %s not cached", DEV_SPAM)
            return False, f"DEV_SPAM channel {DEV_SPAM} not found"

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"mfbot-backup-{stamp}.zip"
        files_line = ", ".join(included)
        skip_line = f" · _skipped (missing): {', '.join(skipped)}_" if skipped else ""
        summary = (
            f"📦 **{reason.capitalize()} backup** — {len(included)} file(s): "
            f"`{files_line}`{skip_line}"
        )
        try:
            await channel.send(
                summary,
                file=discord.File(io.BytesIO(zip_bytes), filename=filename),
            )
            logger.info("Backup uploaded (%s): %s", reason, filename)
            return True, filename
        except discord.HTTPException as e:
            logger.error("Backup: upload to DEV_SPAM failed (%s): %r", reason, e, exc_info=True)
            return False, f"upload failed: {e}"

    def _build_archive(self) -> tuple[bytes, list[str], list[str]]:
        included: list[str] = []
        skipped: list[str] = []
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for path in _BACKUP_PATHS:
                if not path.exists():
                    skipped.append(path.name)
                    continue
                # SQLite WAL means a plain file read gets a consistent
                # snapshot in the vast majority of cases. If we ever hit
                # corruption from this, switch to sqlite3.Connection.backup().
                z.write(path, arcname=path.name)
                included.append(path.name)
        return buf.getvalue(), included, skipped

    @app_commands.command(
        name="backup_now",
        description="Trigger an immediate state-file backup to DEV_SPAM (admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def backup_now(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok, summary = await self._run_backup(reason="manual")
        if ok:
            await interaction.followup.send(f"✅ Uploaded: `{summary}`", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {summary}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
