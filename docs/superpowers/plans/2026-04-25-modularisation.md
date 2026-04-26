# Modularisation (M1–M8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor MF BOT into clearly bounded modules — shared DB service, centralised pfp helper, rank config, logging handler, clean FeedbackThreads API, split member card system, and completed feedback monitor split.

**Architecture:** `data/` sits at the bottom of the import chain (no internal imports). `database/db.py` becomes a `Database` class attached to `bot.db`. `utils/bot_logger.py` adds a `DiscordChannelHandler` to the root logger. Cogs reference `self.bot.db` and `self.bot.get_owner_pfp_url()` instead of module-level globals.

**Tech Stack:** Python 3.11, discord.py 2.x, aiosqlite, Pillow, logging stdlib

---

## Spec reference
`docs/superpowers/specs/2026-04-25-modularisation-design.md`

## Implementation notes
- **No automated tests** exist in this project. Verification steps run the bot and confirm startup + key commands work.
- **M3 edge case:** `record_admin_adjustment` returns `None` when the target has left or thread creation fails. Callers must check before using the thread.
- **M8 shutdown risk:** `DiscordChannelHandler.emit` must guard `bot.is_ready()` and wrap `create_task` in try/except `RuntimeError` to survive the shutdown window.

---

## Task 1: M4 — Create `data/config.py`

**Files:**
- Create: `data/config.py`
- Modify: `cogs/slash_commands/rank_commands.py` (lines ~75, ~123)
- Modify: `cogs/member_cards/member_class.py` (lines ~46–47)

- [ ] **Step 1: Create `data/config.py`**

```python
# data/config.py
# No imports from our own codebase — safe to import from anywhere.

# Ordered from lowest to highest (used for rank-up/rank-down comparisons)
RANK_ORDER: list[str] = [
    "Groupies",
    "Stagehands",
    "Supporting Acts",
    "Headliners",
    "MF Gilded",
    "The Real MFrs",
]

# Roles removed when a user ranks up past them
LOWER_RANKS: frozenset[str] = frozenset({"Groupies", "Stagehands", "Supporting Acts"})

# Role names used for special-case logic across the codebase
AOTW_ROLE_NAME: str = "Artist of the Week"
FANS_ROLE_NAME: str = "Fans"

# Roles skipped when determining a member's display rank
ROLES_TO_IGNORE: frozenset[str] = frozenset({"POO CAFE", "kangaroo", "emo nemo", "Event Host"})
```

- [ ] **Step 2: Update `rank_commands.py` to import from config**

In `cogs/slash_commands/rank_commands.py`, add at the top:
```python
from data.config import RANK_ORDER, LOWER_RANKS
```

Replace line ~75:
```python
# BEFORE
lower_rank_names = {"Groupies", "Stagehands", "Supporting Acts"}
# AFTER
lower_rank_names = LOWER_RANKS
```

Replace line ~123:
```python
# BEFORE
higher_rank_names = ["Groupies", "Stagehands", "Supporting Acts", "Headliners", "MF Gilded", "The Real MFrs"]
# AFTER
higher_rank_names = RANK_ORDER
```

- [ ] **Step 3: Update `member_class.py` to import from config**

In `cogs/member_cards/member_class.py`, add:
```python
from data.config import AOTW_ROLE_NAME, FANS_ROLE_NAME, ROLES_TO_IGNORE
```

In `get_rank` (~line 44–60), replace:
```python
# BEFORE
aotw = "Artist of the Week"
fans_role_name = "Fans"
roles_to_ignore = ["POO CAFE", "kangaroo", "emo nemo", "Event Host"]
# AFTER
aotw = AOTW_ROLE_NAME
fans_role_name = FANS_ROLE_NAME
roles_to_ignore = ROLES_TO_IGNORE
```

In `get_last_finished_music` (~line 101–102), replace:
```python
# BEFORE
aotw_role_name = "Artist of the Week"
fans_role_name = "Fans"
# AFTER
aotw_role_name = AOTW_ROLE_NAME
fans_role_name = FANS_ROLE_NAME
```

- [ ] **Step 4: Verify**

Start the bot: `python bot.py`
Expected: bot starts, no `ImportError` or `NameError`. Test `/ranks add` to confirm rank logic still works.

- [ ] **Step 5: Commit**

```bash
git add data/config.py cogs/slash_commands/rank_commands.py cogs/member_cards/member_class.py
git commit -m "feat(M4): extract rank names into data/config.py"
```

---

## Task 2: M8 — Discord logging handler

**Files:**
- Create: `utils/__init__.py` (empty)
- Create: `utils/bot_logger.py`
- Modify: `bot.py`
- Modify: `ml_model/feedback_monitor.py`
- Modify: `modules/scan_delete_intro_messages.py`
- Modify: `cogs/finished_music_message.py`

- [ ] **Step 1: Create `utils/__init__.py`**

Create an empty file at `utils/__init__.py`.

- [ ] **Step 2: Create `utils/bot_logger.py`**

```python
# utils/bot_logger.py
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
```

- [ ] **Step 3: Add the handler to the root logger in `bot.py`**

In `bot.py`, after the `bot = commands.Bot(...)` line (around line 31), add:
```python
from utils.bot_logger import DiscordChannelHandler
```

At the end of the `main()` function, after the logging setup and **after** `bot` is available, add:
```python
discord_handler = DiscordChannelHandler(bot, level=logging.WARNING)
discord_handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s %(name)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logging.getLogger().addHandler(discord_handler)
```

Place this block immediately after `logging.basicConfig(...)` inside `main()`.

- [ ] **Step 4: Migrate `ml_model/feedback_monitor.py`**

Delete the entire `log_to_bot_log` method (lines 36–67).

Replace every `await self.log_to_bot_log(...)` call with the appropriate `logger.*` level:

Migration rule:
- `"🔍 Processing..."`, `"✅ Feedback processed..."`, `"✅ Validation..."`, `"💾 Feedback saved..."`, `"📊 Stats..."`, `"🧪 Test feedback..."`, `"🔄 Listener check..."`, `"🚀 FeedbackMonitor started"` → `logger.info(...)`
- `"⚠️ on_message called but listener inactive"`, `"⚠️ Empty feedback text..."`, `"⚠️ Error adding reactions..."`, `"⚠️ Error counting entries..."` → `logger.warning(...)`
- All `"❌ Error..."`, `"💥 CRITICAL..."` calls → `logger.error("...", exc_info=True)` (remove the separate `error` parameter — `exc_info=True` captures the current exception automatically inside `except` blocks)

Also update the `notifier.notify_bad_feedback(...)` call — remove `log_callback=self.log_to_bot_log` argument (the notifier will use its own logger after M6).

- [ ] **Step 5: Migrate `modules/scan_delete_intro_messages.py`**

Delete the `log_to_bot_log` method. Replace calls:
- Startup, success messages (`"🚀 MessageCleaner started"`, `"✅ Cleaned..."`, `"ℹ️ No old messages"`) → `logger.info(...)`
- `"⚠️ Channel is None..."` → `logger.warning(...)`
- All `"❌ ..."` and `"💥 CRITICAL..."` calls → `logger.error("...", exc_info=True)`

- [ ] **Step 6: Migrate `cogs/finished_music_message.py`**

Read the file to confirm it has a `log_to_bot_log` method. Delete it. Replace calls following the same rule as Step 4–5.

- [ ] **Step 7: Verify**

Start `python bot.py`. Trigger a `logger.warning(...)` by sending a bad command. Confirm the warning appears in BOT_LOG channel.

- [ ] **Step 8: Commit**

```bash
git add utils/__init__.py utils/bot_logger.py bot.py ml_model/feedback_monitor.py modules/scan_delete_intro_messages.py cogs/finished_music_message.py
git commit -m "feat(M8): add DiscordChannelHandler; remove log_to_bot_log from 3 cogs"
```

---

## Task 3: M2 — Convert `database/db.py` to a `Database` class

**Files:**
- Modify: `database/db.py`

This task converts the file only. Callers are updated in Task 4.

- [ ] **Step 1: Rewrite `database/db.py`**

Replace the entire file content with the class-based version below. All logic is identical — only `global` keywords are removed, module-level variables become `self.*`, and module-level functions become methods.

```python
# database/db.py
import aiosqlite
import os
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

DATABASE_ERROR = -2
_WEEK = 60 * 60 * 24 * 7


class Database:
    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None
        self.users_dict: dict[str, dict] = {}

    # ── connection ──────────────────────────────────────────────────────────

    async def init_database(self) -> None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        db_filename = os.environ.get("DB_NAME", "MF_DB.db")
        db_file = os.path.join(data_dir, db_filename)

        self._conn = await aiosqlite.connect(db_file)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA busy_timeout=5000;")
        await self._conn.commit()

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                kicks INTEGER DEFAULT 0
            )
        """)
        await self._conn.commit()
        logger.info("SQLite database connected (WAL mode) at: %s", db_file)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed.")

    def _ensure_connected(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.init_database() has not been called.")
        return self._conn

    # ── weekly cache reset ───────────────────────────────────────────────────

    async def schedule_weekly_task(self) -> None:
        while True:
            await asyncio.sleep(_WEEK)
            self.users_dict.clear()

    # ── internal ─────────────────────────────────────────────────────────────

    async def _update_dict_from_db(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        self.users_dict[user_id] = {}
        async with conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()

        if result:
            self.users_dict[user_id]["Points"] = int(result["points"])
            self.users_dict[user_id]["Warnings"] = int(result["warnings"])
            self.users_dict[user_id]["Kicks"] = int(result["kicks"])
        else:
            del self.users_dict[user_id]
            await self.add_user(user_id, called_from_update_func=True)
            self.users_dict[user_id] = {"Points": 0, "Warnings": 0, "Kicks": 0}

    async def _fetch_rank_from_db(self, user_id: str) -> aiosqlite.Row | None:
        conn = self._ensure_connected()
        query = """
            SELECT (SELECT COUNT(*) + 1
                    FROM users AS u
                    WHERE u.points > (SELECT points FROM users WHERE user_id = ?)) AS Rank_value
        """
        async with conn.execute(query, (str(user_id),)) as cursor:
            return await cursor.fetchone()

    # ── read ──────────────────────────────────────────────────────────────────

    async def fetch_points(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Points" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Points"]
        if user_id in self.users_dict:
            del self.users_dict[user_id]
        await self._update_dict_from_db(user_id)
        return self.users_dict[user_id]["Points"]

    async def fetch_rank(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Rank" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Rank"]
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        result = await self._fetch_rank_from_db(user_id)
        if result and result["Rank_value"] is not None:
            self.users_dict[user_id]["Rank"] = result["Rank_value"]
            return result["Rank_value"]
        return DATABASE_ERROR

    async def fetch_kicks(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Kicks" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Kicks"]
        await self._update_dict_from_db(user_id)
        return self.users_dict[user_id]["Kicks"]

    async def top_10(self) -> list:
        conn = self._ensure_connected()
        async with conn.execute(
            "SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10"
        ) as cursor:
            return await cursor.fetchall()

    async def fetch_top_users(self) -> dict:
        conn = self._ensure_connected()
        async with conn.execute(
            "SELECT user_id, points FROM users ORDER BY points DESC LIMIT 5"
        ) as cursor:
            top_users = await cursor.fetchall()
        return {
            user["user_id"]: {"points": user["points"], "rank": i}
            for i, user in enumerate(top_users, start=1)
        }

    # ── write ─────────────────────────────────────────────────────────────────

    async def add_points(self, user_id: str, points: int) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] += points
        await conn.execute(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points, user_id)
        )
        await conn.commit()

    async def reduce_points(self, user_id: str, points: int) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] -= points
        await conn.execute(
            "UPDATE users SET points = points - ? WHERE user_id = ?",
            (points, user_id)
        )
        await conn.commit()

    async def reset_points(self, user_id: str, is_kicked: bool = False) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if is_kicked and user_id in self.users_dict:
            del self.users_dict[user_id]
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] = 0
        await conn.execute(
            "UPDATE users SET points = 0 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_user(self, user_id: str, called_from_update_func: bool = False) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            self.users_dict[user_id] = {}
        await conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await conn.commit()
        if not called_from_update_func:
            await self._update_dict_from_db(user_id)

    async def remove_user(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        self.users_dict.pop(user_id, None)
        await conn.execute(
            "DELETE FROM users WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_kick(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        self.users_dict[user_id]["Kicks"] = self.users_dict[user_id].get("Kicks", 0) + 1
        await conn.execute(
            "UPDATE users SET kicks = kicks + 1 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_warning_to_user(self, user_id: str) -> int:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        self.users_dict[user_id]["Warnings"] = self.users_dict[user_id].get("Warnings", 0) + 1
        await conn.execute(
            "UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()
        return self.users_dict[user_id]["Warnings"]

    # ── migrations (unchanged logic) ─────────────────────────────────────────

    async def json_migration(self, users: dict) -> None:
        conn = self._ensure_connected()
        batch = [(str(uid), data["points"]) for uid, data in users.items()]
        await conn.executemany(
            "INSERT OR REPLACE INTO users (user_id, points, warnings) VALUES (?, ?, 0)",
            batch
        )
        await conn.commit()

    async def migrate_warnings(self) -> None:
        conn = self._ensure_connected()
        try:
            with open('user_ids.json', 'r') as file:
                user_ids_json = json.load(file)
            for user_id, warnings in user_ids_json.items():
                async with conn.execute(
                    "UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id))
                ) as cursor:
                    if cursor.rowcount > 0:
                        logger.info("Updated user %s with %d warnings", user_id, warnings)
                    else:
                        logger.warning("User %s not found in the database", user_id)
            await conn.commit()
        except Exception:
            logger.error("migrate_warnings failed", exc_info=True)

    async def migrate_warnings_extreme(self, user_warnings: dict) -> None:
        conn = self._ensure_connected()
        try:
            for user_id, warnings in user_warnings.items():
                async with conn.execute(
                    "SELECT * FROM users WHERE user_id = ?;", (str(user_id),)
                ) as cur:
                    existing_user = await cur.fetchone()
                if existing_user is not None:
                    await conn.execute(
                        "UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id))
                    )
                    logger.info("Updated warnings for user %s", user_id)
                else:
                    await conn.execute(
                        "INSERT INTO users (user_id, points, warnings, kicks) VALUES (?, ?, ?, ?);",
                        (str(user_id), 0, warnings, 0)
                    )
                    logger.info("Inserted new row for user %s", user_id)
            await conn.commit()
        except Exception:
            logger.error("migrate_warnings_extreme failed", exc_info=True)
```

- [ ] **Step 2: Commit the db.py change alone before touching callers**

```bash
git add database/db.py
git commit -m "refactor(M2): convert db.py module functions to Database class"
```

---

## Task 4: M2 — Wire `bot.db` and update all callers

**Files:**
- Modify: `bot.py`
- Modify: `cogs/general.py`
- Modify: `cogs/user_listener.py`
- Modify: `cogs/owner_utilities.py`
- Modify: `cogs/slash_commands/admin.py`
- Modify: `cogs/aotw/create_poll.py`
- Modify: `cogs/member_cards/member_class.py`
- Modify: `cogs/feedback_threads/feedback_threads.py`
- Modify: `cogs/feedback_threads/modules/embeds.py`
- Modify: `cogs/feedback_threads/modules/helpers.py`
- Modify: `cogs/feedback_threads/modules/points_logic.py`

- [ ] **Step 1: Update `bot.py`**

Replace:
```python
import database.db as db
```
with:
```python
from database.db import Database
```

Replace the `bot = commands.Bot(...)` block with an `MFBot` subclass (this also sets up M1's `get_owner_pfp_url`):
```python
class MFBot(commands.Bot):
    _owner_pfp_url: str = ""

    async def get_owner_pfp_url(self) -> str:
        if not self._owner_pfp_url:
            user = await self.fetch_user(self.owner_id)
            self._owner_pfp_url = user.avatar.url
        return self._owner_pfp_url


bot = MFBot(
    command_prefix=["<MF", "<Mf", "<mF", "<mf"],
    intents=intents,
    case_insensitive=True,
    strip_after_prefix=True,
    owner_id=BOT_DEV_ID,
)
bot.remove_command('help')
```

In `main()`, replace:
```python
await db.init_database()
```
with:
```python
bot.db = Database()
await bot.db.init_database()
```

Replace:
```python
task = asyncio.create_task(db.schedule_weekly_task())
```
with:
```python
task = asyncio.create_task(bot.db.schedule_weekly_task())
```

- [ ] **Step 2: Pattern for updating every caller**

The change is mechanical in all 10 remaining files. For each file:

1. Remove: `import database.db as db`
2. All callsites: `db.METHOD(args)` → `self.bot.db.METHOD(args)` (or `bot.db.METHOD(args)` in `bot.py`)

**Exception — `feedback_threads/modules/` helpers:** These classes receive `bot` in `__init__` as `self.bot`. Use `self.bot.db.METHOD(args)`.

File-by-file changes:

**`cogs/general.py`**
- Remove `import database.db as db`
- `db.add_points(...)` → `await self.bot.db.add_points(...)`
- `db.fetch_points(...)` → `await self.bot.db.fetch_points(...)`
- `db.reduce_points(...)` → `await self.bot.db.reduce_points(...)`

**`cogs/user_listener.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/owner_utilities.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/slash_commands/admin.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/aotw/create_poll.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/member_cards/member_class.py`**
- Remove `import database.db as db`
- `db.fetch_points(...)` → `await self.bot.db.fetch_points(...)`
- `db.top_10()` → `await self.bot.db.top_10()`

**`cogs/feedback_threads/feedback_threads.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/feedback_threads/modules/embeds.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/feedback_threads/modules/helpers.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

**`cogs/feedback_threads/modules/points_logic.py`**
- Remove `import database.db as db`
- All `db.*` → `self.bot.db.*`

- [ ] **Step 3: Verify**

```
python bot.py
```
Expected: bot starts, no `AttributeError: module 'database.db' has no attribute 'fetch_points'` or similar. Run `<MFpoints` to confirm DB reads work.

- [ ] **Step 4: Commit**

```bash
git add bot.py cogs/general.py cogs/user_listener.py cogs/owner_utilities.py cogs/slash_commands/admin.py cogs/aotw/create_poll.py cogs/member_cards/member_class.py cogs/feedback_threads/feedback_threads.py cogs/feedback_threads/modules/embeds.py cogs/feedback_threads/modules/helpers.py cogs/feedback_threads/modules/points_logic.py
git commit -m "refactor(M2): wire bot.db and update all callers"
```

---

## Task 5: M1 — Centralise `pfp_url` fetching

**Files (9):**
- Modify: `cogs/general.py`
- Modify: `cogs/guild_events.py`
- Modify: `cogs/user_listener.py`
- Modify: `cogs/music.py`
- Modify: `cogs/help_command.py`
- Modify: `cogs/slash_commands/admin.py`
- Modify: `cogs/slash_commands/rank_commands.py`
- Modify: `cogs/slash_commands/threads.py`
- Modify: `cogs/feedback_threads/modules/points_logic.py`

Note: `MFBot.get_owner_pfp_url()` was added to `bot.py` in Task 4 Step 1.

- [ ] **Step 1: Pattern for each cog**

For every file listed:

1. Remove `self.pfp_url = ""` from `__init__`
2. Remove every `if self.pfp_url == "":` / `if not self.pfp_url:` lazy-fetch block (the 3–4 lines that call `fetch_user` and assign `self.pfp_url`)
3. Replace every remaining `self.pfp_url` reference with `await self.bot.get_owner_pfp_url()`

**Special cases:**

**`cogs/music.py`** — the `Music` cog uses `self._pfp_url = None` / `_get_pfp_url()` helper, and passes the result to `NotesView(...)`:
```python
# BEFORE
pfp_url = await self._get_pfp_url()
view = NotesView(ctx.author.id, self._notes_data, pfp_url, ctx.guild.icon.url)

# AFTER — delete _get_pfp_url method entirely
pfp_url = await self.bot.get_owner_pfp_url()
view = NotesView(ctx.author.id, self._notes_data, pfp_url, ctx.guild.icon.url)
```
Also remove `self._pfp_url = None` from `__init__`.

**`cogs/help_command.py`** — same pattern, the `HelpCommand` cog has `_get_pfp_url()`:
```python
# BEFORE
pfp_url = await self._get_pfp_url()
self.menu = HelpMenu(self.bot, pfp_url)

# AFTER — delete _get_pfp_url method entirely
pfp_url = await self.bot.get_owner_pfp_url()
self.menu = HelpMenu(self.bot, pfp_url)
```

**`cogs/feedback_threads/modules/points_logic.py`** — receives `bot` in `__init__` as `self.bot`, same pattern as cogs.

- [ ] **Step 2: Verify**

Start `python bot.py`. Run `<MFpoints` and `<MFR` — confirm embeds still show the footer icon. No `AttributeError`.

- [ ] **Step 3: Commit**

```bash
git add cogs/general.py cogs/guild_events.py cogs/user_listener.py cogs/music.py cogs/help_command.py cogs/slash_commands/admin.py cogs/slash_commands/rank_commands.py cogs/slash_commands/threads.py cogs/feedback_threads/modules/points_logic.py
git commit -m "refactor(M1): centralise pfp_url via bot.get_owner_pfp_url()"
```

---

## Task 6: M7 — `ConfigureChannel` as cog-level dependency

**Files:**
- Modify: `cogs/slash_commands/aotw_event.py`

- [ ] **Step 1: Update `AOTWEvent.__init__`**

```python
# BEFORE
class AOTWEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# AFTER
class AOTWEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_config = ConfigureChannel(bot)
```

- [ ] **Step 2: Replace the 5 inline instantiations**

Search for `config = ConfigureChannel(self.bot)` — there are 5 occurrences in `aotw_event.py`. Replace each one with nothing (delete the line). Then replace every subsequent `config.` reference on that handler with `self.channel_config.`.

For example:
```python
# BEFORE
config = ConfigureChannel(self.bot)
await config.initialize_channels()

# AFTER
await self.channel_config.initialize_channels()
```

Repeat for all 5 handlers.

- [ ] **Step 3: Verify**

Start the bot. Confirm `/aotw` commands still load without `AttributeError`.

- [ ] **Step 4: Commit**

```bash
git add cogs/slash_commands/aotw_event.py
git commit -m "refactor(M7): ConfigureChannel as cog-level dependency in AOTWEvent"
```

---

## Task 7: M5 — Split `member_class.py`

**Files:**
- Create: `cogs/member_cards/member_data.py`
- Create: `cogs/member_cards/member_card_renderer.py`
- Modify: `cogs/slash_commands/get_member_card.py`
- Modify: `cogs/member_cards/add_rank_member_card.py`
- Modify: `bot.py` (remove member_class from extensions)
- Delete: `cogs/member_cards/member_class.py`

- [ ] **Step 1: Create `cogs/member_cards/member_data.py`**

This file takes everything from `MemberCards` in `member_class.py` and makes it a plain (non-cog) class:

```python
# cogs/member_cards/member_data.py
import discord
import logging
import re
import random
from datetime import datetime, timedelta, timezone
from typing import Union
from data.constants import FINISHED_MUSIC, AOTW_CHANNEL, GENERAL_CHAT_CHANNEL_ID, INTRO_MUSIC
from data.config import AOTW_ROLE_NAME, FANS_ROLE_NAME, ROLES_TO_IGNORE

logger = logging.getLogger(__name__)


class MemberData:
    """Fetches and holds Discord data for a guild member. Not a cog."""

    TARGET_MAIN_GENRES = tuple(int(x, 16) for x in ("8d", "8c", "8c"))
    TARGET_DAW = tuple(int(x, 16) for x in ("61", "55", "a6"))
    TARGET_INSTRUMENTS = tuple(int(x, 16) for x in ("e3", "ab", "ff"))

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
```

Then copy over all methods from `member_class.py` (`get_username`, `get_pfp`, `get_join_date`, `get_rank`, `get_points`, `get_message_count`, `get_last_finished_music`, `generate_random_date_range`, `get_random_message`, `get_roles`, `get_roles_by_colors`), replacing `db.*` with `self.bot.db.*`.

Key change in `get_rank` — use imported constants:
```python
async def get_rank(self, member: discord.Member) -> str:
    for role in reversed(member.roles):
        if role.name in ROLES_TO_IGNORE:
            continue
        if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
            if role.name == AOTW_ROLE_NAME:
                return AOTW_ROLE_NAME
            elif role.name == FANS_ROLE_NAME:
                return FANS_ROLE_NAME
            else:
                return role.name
    return "No specific rank"
```

No `setup()` function — this is not a cog.

- [ ] **Step 2: Create `cogs/member_cards/member_card_renderer.py`**

Read `cogs/slash_commands/get_member_card.py` to identify all Pillow drawing code (the `generate_card`, `render_animated_frames`, and related helper functions). Extract them into a standalone async function:

```python
# cogs/member_cards/member_card_renderer.py
import asyncio
import discord
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter, ImageOps
# ... (all other Pillow imports from get_member_card.py)

logger = logging.getLogger(__name__)


async def render_member_card(bot, member: discord.Member, **kwargs) -> discord.File:
    """Runs all Pillow work off the event loop. Returns a discord.File."""
    return await asyncio.to_thread(_render_sync, bot, member, **kwargs)


def _render_sync(bot, member: discord.Member, **kwargs) -> discord.File:
    # Move the synchronous Pillow drawing logic here from get_member_card.py
    ...
```

The exact function signatures and Pillow code come directly from `get_member_card.py`. Do not change logic — only move it.

- [ ] **Step 3: Update `get_member_card.py`**

Replace the inline Pillow drawing code with an import and call to `render_member_card`:
```python
from cogs.member_cards.member_card_renderer import render_member_card
from cogs.member_cards.member_data import MemberData
```

In `__init__`:
```python
def __init__(self, bot):
    self.bot = bot
    self.member_data = MemberData(bot)
    # keep font_path, background_images_dir etc. here or move to renderer
```

Replace calls like `await cog.get_rank(member)` → `await self.member_data.get_rank(member)`.

- [ ] **Step 4: Update `add_rank_member_card.py`**

```python
from cogs.member_cards.member_data import MemberData
```

Replace `cog = self.bot.get_cog('MemberCards')` → `member_data = MemberData(self.bot)`.
Replace `await cog.get_pfp(member)` → `await member_data.get_pfp(member)`.

- [ ] **Step 5: Remove `member_class.py` from bot extensions**

In `bot.py`, remove `'cogs.member_cards.member_class'` from `initial_extensions`.

- [ ] **Step 6: Delete `member_class.py`**

```bash
del "cogs\member_cards\member_class.py"
```

- [ ] **Step 7: Verify**

Start `python bot.py`. Run `/membercard` — confirm the card generates. No `ModuleNotFoundError`.

- [ ] **Step 8: Commit**

```bash
git add cogs/member_cards/member_data.py cogs/member_cards/member_card_renderer.py cogs/slash_commands/get_member_card.py cogs/member_cards/add_rank_member_card.py bot.py
git commit -m "refactor(M5): split member_class into member_data + member_card_renderer"
```

---

## Task 8: M3 — Clean public API for `FeedbackThreads`

**Files:**
- Modify: `cogs/feedback_threads/feedback_threads.py`
- Modify: `cogs/general.py`
- Modify: `cogs/slash_commands/admin.py`

- [ ] **Step 1: Add public methods to `FeedbackThreads`**

In `cogs/feedback_threads/feedback_threads.py`, add three public methods after `cog_load`:

```python
async def record_feedback(self, ctx: commands.Context) -> tuple[discord.Thread, int] | None:
    """
    Called by general.py after a successful <MFR command.
    Creates/updates the user's private thread and returns (thread, ticket_counter)
    for the caller to use in the feedback-log embed.
    Returns None if the thread is unavailable.
    """
    try:
        await self.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
    except Exception:
        logger.error("record_feedback: thread operation failed for %s", ctx.author.id, exc_info=True)
        return None
    thread_info = self.user_thread.get(ctx.author.id)
    if thread_info is None:
        return None
    thread_id, ticket_counter = thread_info
    thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
    return thread, ticket_counter

async def record_spend(self, ctx: commands.Context) -> tuple[discord.Thread, int] | None:
    """
    Called by general.py after a successful <MFS command.
    Identical flow to record_feedback — separate method for clarity.
    """
    try:
        await self.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
    except Exception:
        logger.error("record_spend: thread operation failed for %s", ctx.author.id, exc_info=True)
        return None
    thread_info = self.user_thread.get(ctx.author.id)
    if thread_info is None:
        return None
    thread_id, ticket_counter = thread_info
    thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
    return thread, ticket_counter

async def record_admin_adjustment(
    self,
    interaction: discord.Interaction,
    target: discord.Member,
) -> discord.Thread | None:
    """
    Called by admin.py for /mfpoints add|remove|clear.
    Creates/updates the target user's private thread.
    Returns the thread so the caller can send the mod embed, or None on failure.
    """
    from cogs.feedback_threads.modules.ctx_class import ContextLike
    target_ctx = ContextLike(interaction=interaction, command=None, custom_author=target)
    try:
        await self.threads_manager.check_if_feedback_thread(target_ctx, called_from_zero=False)
    except Exception:
        logger.error("record_admin_adjustment: thread operation failed for %s", target.id, exc_info=True)
        return None
    thread_info = self.user_thread.get(target.id)
    if thread_info is None:
        return None
    thread_id, _ = thread_info
    thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
    return thread
```

- [ ] **Step 2: Update `general.py` MFR command**

Replace the internals-reaching block in `MFR_command`:
```python
# BEFORE
feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx)
await feedback_cog.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)

# AFTER
feedback_cog = self.bot.get_cog("FeedbackThreads")
result = await feedback_cog.record_feedback(ctx)
if result is None:
    return
thread, ticket_counter = result
```

- [ ] **Step 3: Update `general.py` MFS command (points > 0 branch)**

```python
# BEFORE
feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx)
...
await feedback_cog.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)

# AFTER
feedback_cog = self.bot.get_cog("FeedbackThreads")
result = await feedback_cog.record_spend(ctx)
if result is None:
    return
thread, ticket_counter = result
```

- [ ] **Step 4: Update `admin.py` (add, remove, clear commands)**

For each of the three slash commands, replace:
```python
# BEFORE
admin_ctx_like = ContextLike(interaction=interaction, command=self.add)
feedback_cog, user_thread, sqldatabase = await self.helpers.load_threads_cog(admin_ctx_like)
target_user_ctx_like = ContextLike(interaction=interaction, command=self.add, custom_author=user)
thread_for_target_user, ticket_counter = await feedback_cog.threads_manager.check_if_feedback_thread(target_user_ctx_like, called_from_zero=False)

# AFTER
feedback_cog = self.bot.get_cog("FeedbackThreads")
thread_for_target_user = await feedback_cog.record_admin_adjustment(interaction, user)
if thread_for_target_user is None:
    await interaction.followup.send("Could not create or retrieve feedback thread for this user.", ephemeral=True)
    return
```

Note: `ticket_counter` is no longer returned from `record_admin_adjustment`. Check whether the `mod_embed` in admin.py uses `ticket_counter`. If it does, retrieve it after:
```python
thread_info = feedback_cog.user_thread.get(user.id)
ticket_counter = thread_info[1] if thread_info else 0
```

- [ ] **Step 5: Verify**

Start `python bot.py`. Run `<MFR` and `<MFS` — confirm point updates and thread logs work. Run `/mfpoints add @user` — confirm mod embed appears in the user's thread, or graceful error if user has left.

- [ ] **Step 6: Commit**

```bash
git add cogs/feedback_threads/feedback_threads.py cogs/general.py cogs/slash_commands/admin.py
git commit -m "refactor(M3): add record_feedback/record_spend/record_admin_adjustment public API to FeedbackThreads"
```

---

## Task 9: M6 — Complete `feedback_monitor.py` split

**Files:**
- Modify: `ml_model/mod_bad_feedback_notification.py`
- Modify: `ml_model/feedback_monitor.py`

- [ ] **Step 1: Read `mod_bad_feedback_notification.py`**

Read the full file to understand the current `FeedbackNotifier` class and the existing `_BadFeedbackView`.

- [ ] **Step 2: Add `send_prediction_result` to `FeedbackNotifier`**

In `mod_bad_feedback_notification.py`, add a new method to `FeedbackNotifier`:

```python
async def send_prediction_result(
    self,
    message: discord.Message,
    result: dict,
    feedback_text: str,
) -> discord.Message | None:
    """
    Builds the prediction embed, sends it to DEV_SPAM, adds reactions.
    Returns the sent mod_message (used by FeedbackMonitor to track pending validation),
    or None if the send fails.
    """
    from data.constants import DEV_SPAM, CO_DEV_ID

    dev_spam = self.bot.get_channel(DEV_SPAM)
    if not dev_spam:
        logger.error("send_prediction_result: DEV_SPAM channel %s not found", DEV_SPAM)
        return None

    feedback_preview = feedback_text[:500] + ("..." if len(feedback_text) > 500 else "")
    embed = discord.Embed(
        title="🤖 Feedback Quality Check",
        description=f"**Prediction:** {result['prediction']}",
        color=discord.Color.green() if result['is_good'] else discord.Color.red()
    )
    embed.add_field(name="Feedback Content", value=f"```{feedback_preview}```", inline=False)
    embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Confidence", value=f"{result['probability']:.1%}", inline=True)
    embed.add_field(name="Original Message", value=f"[Jump to message]({message.jump_url})", inline=False)
    embed.set_footer(text=f"Message ID: {message.id}")
    embed.timestamp = message.created_at

    try:
        mod_message = await dev_spam.send(
            content=f"<@{CO_DEV_ID}> New feedback!",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True)
        )
    except Exception:
        logger.error("send_prediction_result: failed to send embed to DEV_SPAM", exc_info=True)
        return None

    try:
        await mod_message.add_reaction("✅")
        await mod_message.add_reaction("❌")
    except Exception:
        logger.warning("send_prediction_result: failed to add reactions (non-critical)")

    return mod_message
```

- [ ] **Step 3: Update `feedback_monitor.py` to delegate to notifier**

In `on_message`, replace the embed-building and dev_spam-sending block with:
```python
# BEFORE — large try block that builds embed and sends to dev_spam
try:
    dev_spam = self.bot.get_channel(DEV_SPAM)
    ...
    embed = discord.Embed(...)
    ...
    mod_message = await dev_spam.send(...)
    ...
    await mod_message.add_reaction("✅")
    await mod_message.add_reaction("❌")
except Exception:
    ...

# AFTER
mod_message = await self.notifier.send_prediction_result(message, result, feedback_text)
if mod_message is None:
    return
```

Remove `DEV_SPAM` from `feedback_monitor.py` imports if it's no longer used directly.

- [ ] **Step 4: Verify**

Start `python bot.py`. Submit an `<MFR` message in the audio feedback channel. Confirm the embed appears in DEV_SPAM with reactions. React with ✅ or ❌ — confirm validation flow still works.

- [ ] **Step 5: Update `CODE_AUDIT.md` entries for M1–M8**

In the "Part 3 — Modularisation Recommendations" section of `CODE_AUDIT.md`, update each M1–M8 heading to mark resolved:

Pattern for each:
```markdown
### M1 — Centralise `pfp_url` fetching

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`get_owner_pfp_url()` added to `MFBot`; all 9 cogs updated.
```

- [ ] **Step 6: Commit**

```bash
git add ml_model/mod_bad_feedback_notification.py ml_model/feedback_monitor.py CODE_AUDIT.md
git commit -m "refactor(M6): move embed build + DEV_SPAM send into FeedbackNotifier.send_prediction_result"
```

---

## Self-review checklist

**Spec coverage:**
- M1 ✅ Task 4 (MFBot class) + Task 5 (all callers)
- M2 ✅ Task 3 (db.py class) + Task 4 (callers + bot.db)
- M3 ✅ Task 8
- M4 ✅ Task 1
- M5 ✅ Task 7
- M6 ✅ Task 9
- M7 ✅ Task 6
- M8 ✅ Task 2

**M3 edge case (user left server / thread fails):** Handled — `record_admin_adjustment` returns `None`, callers check and send ephemeral error.

**M8 shutdown risk:** `DiscordChannelHandler.emit` guards `bot.is_ready()` and wraps `create_task` in try/except `RuntimeError` — survives the shutdown window.

**Type consistency:**
- `record_feedback` / `record_spend` return `tuple[discord.Thread, int] | None` — used consistently in Task 8 Steps 2–3.
- `record_admin_adjustment` returns `discord.Thread | None` — used consistently in Task 8 Step 4.
- `send_prediction_result` returns `discord.Message | None` — used consistently in Task 9 Step 3.
- `Database` class methods match callers — all `db.METHOD(args)` become `bot.db.METHOD(args)`.
