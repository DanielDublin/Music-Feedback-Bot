# Modularisation Design — MF BOT
**Date:** 2026-04-25
**Items:** M1–M8

---

## Constraints (from user)

1. **No god-object.** Only true global services attach to `bot`: the database (`bot.db`) and the owner pfp helper (`bot.get_owner_pfp_url()`). Logic used by only one cog stays in that cog.
2. **No circular imports.** `data/` files import nothing from our own codebase. `database/db.py` imports from `data/` only. `utils/` may import from `data/` but not from `cogs/`. Cogs sit at the top of the chain.

### Dependency chain (bottom → top)
```
data/constants.py   data/config.py
        ↓                 ↓
    database/db.py    utils/bot_logger.py
              ↓          ↓
           bot.py  (attaches bot.db, DiscordChannelHandler, get_owner_pfp_url)
                    ↓
               cogs/**
```

---

## M1 — Centralise `pfp_url` fetching

**Problem:** Every cog that sends embeds carries `self.pfp_url = ""` and an identical lazy-fetch block — currently in 9 places.

**Solution:** Add a method to the bot subclass in `bot.py`:

```python
class MFBot(commands.Bot):
    _owner_pfp_url: str = ""

    async def get_owner_pfp_url(self) -> str:
        if not self._owner_pfp_url:
            user = await self.fetch_user(self.owner_id)
            self._owner_pfp_url = user.avatar.url
        return self._owner_pfp_url
```

All affected files remove their `self.pfp_url` field and replace all fetch + reference code with `await self.bot.get_owner_pfp_url()`.

**Affected files (9):**
- `cogs/general.py`
- `cogs/guild_events.py`
- `cogs/user_listener.py`
- `cogs/music.py` — passes pfp_url to `NotesView(...)` constructor; constructor updated to call `bot.get_owner_pfp_url()` itself
- `cogs/help_command.py` — passes pfp_url to `HelpMenu(...)` constructor; same pattern
- `cogs/slash_commands/admin.py`
- `cogs/slash_commands/rank_commands.py`
- `cogs/slash_commands/threads.py`
- `cogs/feedback_threads/modules/points_logic.py` — receives `bot` already; use `self.bot.get_owner_pfp_url()`

**Not changed:** `cogs/member_cards/` pfp_url references — those are the *member's* avatar URL, not the owner's.

---

## M2 — Database as a class (`bot.db`)

**Problem:** `database/db.py` exposes module-level functions and a module-level `users_dict` — a hidden global.

**Solution:** Convert `db.py` from module-level functions into a `Database` class. `users_dict` becomes `self.users_dict`. All function signatures gain `self`. No separate wrapper — the class IS the service.

```python
# database/db.py
class Database:
    def __init__(self):
        self.users_dict: dict[str, dict] = {}

    async def init_database(self) -> None: ...
    async def fetch_points(self, user_id: str) -> int: ...
    async def add_points(self, user_id: str, amount: int) -> None: ...
    # ... all existing functions become methods
```

In `bot.py`, before cogs load:
```python
bot.db = Database()
await bot.db.init_database()
```

All callers change `db.fetch_points(...)` → `self.bot.db.fetch_points(...)`.

**Affected files (11):**
- `bot.py`
- `cogs/general.py`
- `cogs/user_listener.py`
- `cogs/owner_utilities.py`
- `cogs/slash_commands/admin.py`
- `cogs/aotw/create_poll.py`
- `cogs/member_cards/member_class.py` (will be split by M5, but db calls updated either way)
- `cogs/feedback_threads/feedback_threads.py`
- `cogs/feedback_threads/modules/embeds.py`
- `cogs/feedback_threads/modules/helpers.py`
- `cogs/feedback_threads/modules/points_logic.py`

**Note:** `threads_db.py` (SQLite for thread mappings) stays as-is.

---

## M3 — Clean public API for `feedback_threads`

**Problem:** External cogs reach into `FeedbackThreads` internals: `feedback_cog.threads_manager.check_if_feedback_thread(ctx)`, `self.helpers.load_feedback_cog(ctx)`, etc.

**Solution:** Add three public methods to the `FeedbackThreads` cog. All external callers use only these; internal modules stay internal.

```python
class FeedbackThreads(commands.Cog):

    async def record_feedback(self, ctx: commands.Context) -> None:
        """Called by general.py after a successful <MFR command."""

    async def record_spend(self, ctx: commands.Context) -> None:
        """Called by general.py after a successful <MFS command."""

    async def record_admin_adjustment(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        points: int,
        is_add: bool,
    ) -> discord.Thread:
        """Called by admin.py /mfpoints add|remove|clear.
        Returns the target user's thread so the caller can send the mod embed."""
```

`general.py` and `admin.py` call `feedback_cog = self.bot.get_cog("FeedbackThreads")` then call only these methods. The internal `threads_manager`, `points_logic`, `helpers` chain is invisible to external callers.

---

## M4 — Rank config in `data/config.py`

**Problem:** Rank names, orderings, and role IDs are magic strings/numbers scattered across `rank_commands.py`, `points_logic.py`, and `helpers.py`.

**Solution:** New file `data/config.py`. `data/constants.py` is not touched.

```python
# data/config.py — no imports from our own codebase

RANK_ORDER: list[str] = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]

RANK_ROLE_IDS: dict[str, int] = {
    "Bronze":   <id>,
    "Silver":   <id>,
    "Gold":     <id>,
    "Platinum": <id>,
    "Diamond":  <id>,
}
```

The actual IDs are extracted from the existing hardcoded values in `rank_commands.py` / `helpers.py` during implementation. All rank-comparison logic imports `from data.config import RANK_ORDER, RANK_ROLE_IDS`.

---

## M5 — Split `member_class.py`

**Problem:** `member_class.py` mixes async Discord data-fetching with CPU-bound Pillow image generation.

**Solution:** Split into two files:

**`cogs/member_cards/member_data.py`**
- `MemberData` dataclass: all fetched Discord data (display name, avatar URL, points, rank, join date, roles, etc.)
- `async def fetch_member_data(bot, member: discord.Member) -> MemberData` — all Discord API calls

**`cogs/member_cards/member_card_renderer.py`**
- `async def render_member_card(data: MemberData) -> discord.File`
- All Pillow drawing calls, wrapped in `asyncio.to_thread()`

`member_class.py` is deleted. Callers (`get_member_card.py`, `add_rank_member_card.py`) import from the two new files.

---

## M6 — Complete `feedback_monitor.py` split

**Problem:** `feedback_monitor.py` still builds the embed and sends to `dev_spam` — logic that belongs in the notifier layer.

**Solution:**

`feedback_monitor.py` keeps:
- `on_message`: calls ML prediction, decides pass/fail, calls `await self.notifier.send_prediction_result(...)`, stores returned `mod_message.id` in `pending_validations`
- `on_reaction_add` → `_handle_validation`: exports JSON, pops from dict

`mod_bad_feedback_notification.py` gains:
- `async def send_prediction_result(self, message, result, feedback_text) -> discord.Message` — builds embed, sends to `dev_spam`, adds reactions, returns `mod_message`

The `_BadFeedbackView` already lives in `mod_bad_feedback_notification.py` from E13.

---

## M7 — `ConfigureChannel` as cog-level dependency

**Problem:** `cogs/slash_commands/aotw_event.py` instantiates `ConfigureChannel(self.bot)` at the top of 5 separate command handlers.

**Solution:**

```python
# aotw_event.py
class AotwEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_config = ConfigureChannel(bot)
```

Each of the 5 handlers replaces `config = ConfigureChannel(self.bot)` with `self.channel_config`. No other files change.

---

## M8 — Shared Discord logging handler

**Problem:** `log_to_bot_log` is a ~30-line async method copy-pasted in `feedback_monitor.py`, `modules/scan_delete_intro_messages.py`, and `cogs/finished_music_message.py`.

**Important nuance:** `feedback_monitor.py` calls `log_to_bot_log` ~40 times, including many INFO-level operational messages ("Processing feedback from...", "Feedback processed successfully"). These must NOT all route to Discord — that would spam BOT_LOG. The right migration:
- Operational trace calls → `logger.info(...)` (console only)
- Error/warning calls → `logger.warning(...)` / `logger.error(...)` (Discord via handler)

**Solution:** `utils/bot_logger.py`:

```python
import asyncio, logging, discord
from data.constants import BOT_LOG

class DiscordChannelHandler(logging.Handler):
    def __init__(self, bot: discord.Client, level: int = logging.WARNING):
        super().__init__(level)
        self.bot = bot

    def emit(self, record: logging.LogRecord):
        if not self.bot.is_ready():
            return
        msg = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(msg))
        except RuntimeError:
            pass  # called outside event loop — swallow

    async def _send(self, msg: str):
        channel = self.bot.get_channel(BOT_LOG)
        if not channel:
            return
        for chunk in [msg[i:i+1990] for i in range(0, len(msg), 1990)]:
            await channel.send(f"```\n{chunk}\n```")
```

In `bot.py` after the bot is instantiated:
```python
discord_handler = DiscordChannelHandler(bot, level=logging.WARNING)
logging.getLogger().addHandler(discord_handler)
```

The three `log_to_bot_log` methods are deleted. Each call site is migrated:
- `log_to_bot_log("🔍 Processing...")` → `logger.info("Processing...")`
- `log_to_bot_log("❌ Error...")` → `logger.error("...", exc_info=True)`
- `log_to_bot_log("⚠️ Warning...")` → `logger.warning("...")`

BOT_LOG receives only WARNING+ — actual problems, not per-message operational trace.

---

## Files created
| File | Purpose |
|------|---------|
| `data/config.py` | Rank hierarchy constants |
| `utils/bot_logger.py` | DiscordChannelHandler |
| `cogs/member_cards/member_data.py` | MemberData dataclass + fetch function |
| `cogs/member_cards/member_card_renderer.py` | Pillow rendering off event loop |

## Files deleted
| File | Replaced by |
|------|-------------|
| `cogs/member_cards/member_class.py` | `member_data.py` + `member_card_renderer.py` |

## Files modified (complete list)
| File | Change |
|------|--------|
| `bot.py` | MFBot subclass; `bot.db`; `get_owner_pfp_url`; add DiscordChannelHandler |
| `database/db.py` | Module-level functions → `Database` class |
| `cogs/general.py` | pfp_url → bot method; db → bot.db |
| `cogs/user_listener.py` | pfp_url → bot method; db → bot.db |
| `cogs/guild_events.py` | pfp_url → bot method |
| `cogs/music.py` | pfp_url → bot method (pass through to NotesView) |
| `cogs/help_command.py` | pfp_url → bot method (pass through to HelpMenu) |
| `cogs/owner_utilities.py` | db → bot.db |
| `cogs/slash_commands/admin.py` | pfp_url → bot method; db → bot.db |
| `cogs/slash_commands/rank_commands.py` | pfp_url → bot method; rank constants → config.py |
| `cogs/slash_commands/threads.py` | pfp_url → bot method |
| `cogs/slash_commands/aotw_event.py` | ConfigureChannel → self.channel_config |
| `cogs/aotw/create_poll.py` | db → bot.db |
| `cogs/feedback_threads/feedback_threads.py` | Add public API (M3); db → bot.db |
| `cogs/feedback_threads/modules/embeds.py` | db → bot.db |
| `cogs/feedback_threads/modules/helpers.py` | db → bot.db; rank constants → config.py |
| `cogs/feedback_threads/modules/points_logic.py` | pfp_url → bot method; db → bot.db; rank constants → config.py |
| `ml_model/feedback_monitor.py` | Remove log_to_bot_log; migrate calls to logger.*; delegate embed/send to notifier (M6) |
| `ml_model/mod_bad_feedback_notification.py` | Add send_prediction_result (M6) |
| `modules/scan_delete_intro_messages.py` | Remove log_to_bot_log; migrate calls to logger.* |
| `cogs/finished_music_message.py` | Remove log_to_bot_log; migrate calls to logger.* |
