import asyncio
import logging
import sys
import threading
import time
import discord
from data.constants import BOT_LOG

_DEDUP_WINDOW_SECONDS = 60.0
_DEDUP_CACHE_MAX = 256


class DiscordChannelHandler(logging.Handler):
    """Routes WARNING+ log records to the BOT_LOG Discord channel.

    Identical records repeating within a 60s sliding window are collapsed:
    the first is sent immediately, repeats are counted silently, and the
    next send after the window carries a '(+N duplicates suppressed)' note.
    """

    def __init__(self, bot: discord.Client, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self.bot = bot
        # key (name, levelno, message) -> [last_seen_monotonic, suppressed_count]
        self._dedup: dict[tuple[str, int, str], list] = {}
        self._dedup_lock = threading.Lock()

    def _dedup_check(self, record: logging.LogRecord) -> tuple[bool, int]:
        """Decide whether to send `record`.

        Returns (should_send, suppressed_count). suppressed_count is the
        number of duplicates collapsed since this key was last sent, and is
        only non-zero when should_send is True.
        """
        key = (record.name, record.levelno, record.getMessage())
        now = time.monotonic()
        with self._dedup_lock:
            entry = self._dedup.get(key)
            if entry is None or now - entry[0] > _DEDUP_WINDOW_SECONDS:
                suppressed = entry[1] if entry is not None else 0
                self._dedup[key] = [now, 0]
                self._prune_locked()
                return True, suppressed
            # within the window — collapse this occurrence
            entry[0] = now
            entry[1] += 1
            return False, 0

    def _prune_locked(self) -> None:
        """Drop the oldest entries when the cache exceeds its cap.

        Caller must hold self._dedup_lock.
        """
        if len(self._dedup) <= _DEDUP_CACHE_MAX:
            return
        oldest = sorted(self._dedup.items(), key=lambda kv: kv[1][0])
        for key, _ in oldest[:len(self._dedup) - _DEDUP_CACHE_MAX]:
            del self._dedup[key]

    def emit(self, record: logging.LogRecord) -> None:
        if not self.bot.is_ready():
            return
        should_send, suppressed = self._dedup_check(record)
        if not should_send:
            return
        msg = self.format(record)
        if suppressed > 0:
            msg += (f"\n(+{suppressed} duplicate(s) suppressed "
                    f"in the last {int(_DEDUP_WINDOW_SECONDS)}s)")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(msg))
        except RuntimeError:
            # called outside the event loop (e.g. shutdown) — surface to stderr
            # so failures during teardown don't vanish completely
            print(f"[DiscordChannelHandler] no running loop, dropping: {msg[:200]}",
                  file=sys.stderr)

    async def _send(self, msg: str) -> None:
        channel = self.bot.get_channel(BOT_LOG)
        if not channel:
            return
        for chunk in [msg[i:i + 1990] for i in range(0, len(msg), 1990)]:
            try:
                await channel.send(f"```\n{chunk}\n```")
            except Exception as e:
                # Don't let a failed Discord send crash anything, but at least
                # leave a breadcrumb on stderr (can't log from the log handler
                # itself without risking recursion).
                print(f"[DiscordChannelHandler] send failed: {e!r}", file=sys.stderr)
