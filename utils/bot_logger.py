import asyncio
import logging
import discord
from data.constants import BOT_LOG


class DiscordChannelHandler(logging.Handler):
    """Routes WARNING+ log records to the BOT_LOG Discord channel."""

    def __init__(self, bot: discord.Client, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self.bot = bot

    def emit(self, record: logging.LogRecord) -> None:
        if not self.bot.is_ready():
            return
        msg = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(msg))
        except RuntimeError:
            pass  # called outside the event loop (e.g. shutdown) — swallow silently

    async def _send(self, msg: str) -> None:
        channel = self.bot.get_channel(BOT_LOG)
        if not channel:
            return
        for chunk in [msg[i:i + 1990] for i in range(0, len(msg), 1990)]:
            try:
                await channel.send(f"```\n{chunk}\n```")
            except Exception:
                pass  # don't let a failed Discord send crash anything
