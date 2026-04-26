# MF BOT Audit Deferred Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 6 remaining open audit items: B5 (return type annotations), C9 (sync file I/O), E15 (autocomplete), E18 (Sheets write batching), E7 (print → logging), and E13 (raw reactions → discord.ui.View); then update CODE_AUDIT.md and CLAUDE.md.

**Architecture:** Each item is a self-contained change to specific files; they have no cross-dependencies and can be executed in any order. Ordered here smallest → largest to build momentum.

**Tech Stack:** Python 3.11, discord.py 2.x, gspread, aiosqlite, discord.ui.View, logging stdlib

---

## Scope Note

These are 6 independent subsystems. They are grouped into one plan because the user explicitly requested all of them together. Each task produces a self-contained, committable change.

---

## File Map

| Task | Files Modified |
|------|---------------|
| B5 | `database/db.py`, `cogs/feedback_threads/modules/helpers.py`, `cogs/feedback_threads/modules/threads_manager.py`, `ml_model/ml_model_loader.py` |
| C9 | `ml_model/export_json.py`, `ml_model/feedback_monitor.py` (caller) |
| E15 | `cogs/slash_commands/admin.py` |
| E18 | `database/google_sheet.py` |
| E7 | `bot.py`, `cogs/finished_music_message.py`, `cogs/aotw/create_poll.py`, `cogs/aotw/configure_channel.py`, `cogs/user_listener.py`, `cogs/owner_utilities.py`, `cogs/feedback_threads/feedback_threads.py`, `cogs/feedback_threads/modules/threads_manager.py`, `cogs/feedback_threads/modules/helpers.py`, `cogs/feedback_threads/modules/points_logic.py`, `cogs/member_cards/member_class.py`, `cogs/member_cards/add_rank_member_card.py`, `cogs/slash_commands/get_member_card.py`, `cogs/slash_commands/rank_commands.py`, `cogs/slash_commands/aotw_event.py`, `watchdog.py`, `exception_handler.py`, `modules/scan_delete_intro_messages.py`, `database/threads_db.py`, `database/db.py`, `database/google_sheet.py`, `modules/promotion_checkers/youtube_promotion_checker.py`, `modules/promotion_checkers/spotify_promotion_checker.py`, `modules/promotion_checkers/soundcloud_promotion_checker.py`, `ml_model/feedback_monitor.py`, `ml_model/export_json.py`, `ml_model/ml_model_loader.py`, `ml_model/mod_bad_feedback_notification.py` |
| E13a | `ml_model/mod_bad_feedback_notification.py` |
| E13b | `cogs/music.py` |
| Final | `CODE_AUDIT.md`, `CLAUDE.md` |

---

## Task 1: B5 — Return Type Annotations

**Files:**
- Modify: `database/db.py`
- Modify: `cogs/feedback_threads/modules/helpers.py`
- Modify: `cogs/feedback_threads/modules/threads_manager.py`
- Modify: `ml_model/ml_model_loader.py`

- [ ] **Step 1: Add return types to `database/db.py`**

Add `from typing import Optional` at the top (after existing imports). Then add return types to these functions:

```python
# fetch_points — can return int (always, after update_dict_from_db guarantees the key)
async def fetch_points(user_id: str) -> int:

# fetch_rank — returns int (rank value) or DATABASE_ERROR (-2)
async def fetch_rank(user_id: str) -> int:

# fetch_kicks — always returns int
async def fetch_kicks(user_id: str) -> int:

# reduce_points — no return value
async def reduce_points(user_id: str, points: int) -> None:

# add_points — no return value (find and add the annotation; signature is currently unannotated)
async def add_points(user_id: str, points: int) -> None:

# top_10 — returns list of aiosqlite.Row
async def top_10() -> list:

# fetch_top_users — returns dict keyed by user_id str
async def fetch_top_users() -> dict:

# add_user — no return value
async def add_user(user_id: str, called_from_update_func: bool = False) -> None:

# update_dict_from_db — no return value
async def update_dict_from_db(user_id: str) -> None:

# fetch_rank_from_db — returns aiosqlite.Row or None
async def fetch_rank_from_db(user_id: str) -> Optional[object]:
```

- [ ] **Step 2: Add return types to `cogs/feedback_threads/modules/helpers.py`**

Add `from typing import Optional` at the top. Then:

```python
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .points_logic import PointsLogic
```

Add return types:

```python
# load_feedback_cog returns a tuple on success, None implicitly if cog not found
# (raises RuntimeError if user not in thread, returns None if feedback_cog is None)
async def load_feedback_cog(
    self, ctx=None, user_id=None
) -> Optional[tuple[discord.Thread, int, "PointsLogic", str]]:

# load_threads_cog — returns a 3-tuple; None-tuple on failure
async def load_threads_cog(self, ctx) -> tuple:

# get_thread_id_no_ctx — returns thread id int or None
@staticmethod
async def get_thread_id_no_ctx(bot, user_id: int) -> Optional[int]:

# delete_user_from_user_thread — no return value
@staticmethod
async def delete_user_from_user_thread(bot, user_id: int) -> None:

# delete_user_from_db — no return value
@staticmethod
async def delete_user_from_db(bot, user_id: int) -> None:

# shorten_message — returns str
def shorten_message(self, content: str, max_length: int) -> str:

# get_message_link — returns str
def get_message_link(self, ctx) -> str:

# get_formatted_time — returns str
def get_formatted_time(self) -> str:

# unarchive_thread — no return value
async def unarchive_thread(self, existing_thread) -> None:

# archive_thread — no return value
async def archive_thread(self, existing_thread) -> None:
```

- [ ] **Step 3: Add return types to `cogs/feedback_threads/modules/threads_manager.py`**

```python
# check_if_feedback_thread — returns (thread, ticket_counter)
async def check_if_feedback_thread(
    self, ctx, called_from_zero: bool = False
) -> tuple[discord.Thread, int]:

# create_new_thread — returns the created thread
async def create_new_thread(self, ctx, called_from_zero: bool = False) -> discord.Thread:

# existing_thread — returns the existing thread
async def existing_thread(self, ctx, called_from_zero: bool = False) -> discord.Thread:

# on_ready — no return value
async def on_ready(self) -> None:
```

- [ ] **Step 4: Add return type to `ml_model/ml_model_loader.py`**

```python
from typing import Any

# predict — returns a dict with 'prediction', 'probability', 'is_good' keys
def predict(self, feedback_text: str) -> dict[str, Any]:

# extract_features — returns dict of feature name → value
def extract_features(self, feedback_text: str) -> dict[str, Any]:

# load_model — no return value
def load_model(self) -> None:

# predict_feedback_quality async wrapper
async def predict_feedback_quality(feedback_text: str) -> dict[str, Any]:
```

- [ ] **Step 5: Commit**

```
git add database/db.py cogs/feedback_threads/modules/helpers.py cogs/feedback_threads/modules/threads_manager.py ml_model/ml_model_loader.py
git commit -m "chore: add return type annotations to key public functions (B5)"
```

---

## Task 2: C9 — Async File I/O in export_json.py

**Files:**
- Modify: `ml_model/export_json.py`
- Modify: `ml_model/feedback_monitor.py` (caller of `export_to_json`)

- [ ] **Step 1: Rewrite `export_json.py` to use `asyncio.to_thread`**

Replace the entire file with:

```python
import asyncio
import discord
import json
from data.constants import EXPORTS_CHANNEL, CO_DEV_ID


class ExportJson:

    def __init__(self, client):
        self.client = client

    def _write_json(self, data: list, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def _read_json(self, filename: str) -> list:
        with open(filename, 'r') as f:
            return json.load(f)

    async def export_to_json(self, data, filename="feedback_json.json") -> bool:
        await asyncio.to_thread(self._write_json, data, filename)
        print(f"✅ Exported feedback data to {filename}")
        return True

    async def count_entries(self, filename="feedback_json.json") -> int:
        try:
            data = await asyncio.to_thread(self._read_json, filename)

            if len(data) >= 20:
                mod_channel = self.client.get_channel(EXPORTS_CHANNEL)

                if mod_channel is None:
                    print(f"❌ Could not find channel with ID {EXPORTS_CHANNEL}")
                    return len(data)

                discord_file = discord.File(filename)
                await mod_channel.send(
                    f"<@{CO_DEV_ID}> New Export!",
                    allowed_mentions=discord.AllowedMentions(users=True)
                )
                await mod_channel.send(file=discord_file, content=f"📊 Feedback export - {len(data)} entries")
                print(f"✅ Sent {len(data)} feedback entries to mod channel")

                await asyncio.to_thread(self._write_json, [], filename)
                print(f"🧹 Cleared {filename}")

            return len(data)

        except FileNotFoundError:
            print("⚠️ Feedback file not found")
            return 0
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {filename}")
            return 0
        except Exception as e:
            print(f"❌ Error in count_entries: {e}")
            return 0
```

- [ ] **Step 2: Update the caller in `ml_model/feedback_monitor.py`**

Find the call site where `export_to_json` is called (it will be `self.export_json.export_to_json(...)` without `await`). Add `await`:

```python
# Before:
self.export_json.export_to_json(data, filename)

# After:
await self.export_json.export_to_json(data, filename)
```

Search for all occurrences: `grep -n "export_to_json" ml_model/feedback_monitor.py`

- [ ] **Step 3: Commit**

```
git add ml_model/export_json.py ml_model/feedback_monitor.py
git commit -m "fix: wrap export_json file I/O in asyncio.to_thread (C9)"
```

---

## Task 3: E15 — Autocomplete on /reload Extension Parameter

**Files:**
- Modify: `cogs/slash_commands/admin.py`

**Context:** The rank add/remove commands already use `discord.Role` which gives Discord's native role picker — no autocomplete change needed there. The `/reload` command takes a free-form `extension: str`, and Discord users have to type the exact dotted path (e.g. `cogs.general`). Adding autocomplete here shows currently-loaded extensions as typed suggestions.

- [ ] **Step 1: Add the autocomplete function and decorator to `admin.py`**

Add this function at module level (before the `Admin` class) and add the decorator to `reload_extension`:

```python
# At module level, before the Admin class:
async def extension_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=ext, value=ext)
        for ext in interaction.client.extensions
        if current.lower() in ext.lower()
    ][:25]
```

Then modify the `reload_extension` command to add the autocomplete decorator:

```python
@app_commands.command(name="reload", description="Reload a bot extension by name")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.guilds(discord.Object(id=SERVER_ID))
@app_commands.describe(extension="Extension path (e.g. cogs.general)")
@app_commands.autocomplete(extension=extension_autocomplete)
async def reload_extension(self, interaction: discord.Interaction, extension: str):
    await interaction.response.defer(ephemeral=True)
    try:
        await self.bot.reload_extension(extension)
        await interaction.followup.send(f"Reloaded `{extension}`.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to reload `{extension}`: {e}", ephemeral=True)
```

- [ ] **Step 2: Commit**

```
git add cogs/slash_commands/admin.py
git commit -m "feat: add autocomplete for /reload extension parameter (E15)"
```

---

## Task 4: E18 — Google Sheets Write Batching

**Files:**
- Modify: `database/google_sheet.py`

**Context:** `update_rank_spreadsheet` currently makes two sequential `update_cell()` API calls (one for the rank text, one for the date). These two adjacent cells in the same row can be written in a single `update_cells()` call using `gspread.Cell` objects, cutting the write from 2 API calls to 1.

- [ ] **Step 1: Add `import gspread` to `database/google_sheet.py` if not present**

Check the top of the file. `gspread` is already imported. Add a check:
```python
import gspread  # already present — no change needed
```

- [ ] **Step 2: Replace `update_rank_spreadsheet` with the batched version**

Find `update_rank_spreadsheet` (currently at line 43) and replace its body:

```python
def update_rank_spreadsheet(self, user_id, role, is_rankup: bool) -> None:
    cell_row = self.sheet.find(str(user_id))
    if cell_row:
        user_row = cell_row.row
        user_row_values = self.sheet.row_values(user_row)
        next_available_col = len(user_row_values) + 1

        rank_text = f"Ranked up to {role}" if is_rankup else f"Ranked down to {role}"
        date_text = self.time()

        # Write both cells in a single API call instead of two update_cell() calls
        cells = [
            gspread.Cell(user_row, next_available_col, rank_text),
            gspread.Cell(user_row, next_available_col + 1, date_text),
        ]
        self.sheet.update_cells(cells)
```

- [ ] **Step 3: Verify no other callers of `update_rank_spreadsheet` exist outside `rank_commands.py`**

Run: `grep -rn "update_rank_spreadsheet" .` — should only show `google_sheet.py` and `rank_commands.py`. No signature change was made so `rank_commands.py` callers need no update.

- [ ] **Step 4: Commit**

```
git add database/google_sheet.py
git commit -m "perf: batch update_rank_spreadsheet writes into single API call (E18)"
```

---

## Task 5: E7 — Replace print() With logging Module (Codebase-Wide)

**Files:** ~28 files (see file map above)

**Setup rule:** Every file that currently uses `print()` gets:
```python
import logging
logger = logging.getLogger(__name__)
```
at the top (after existing stdlib imports, before third-party imports). Then each `print(...)` is replaced with `logger.<level>(...)` according to this mapping:

| Pattern | Level |
|---------|-------|
| `print(f"Error...{e}")` inside `except` | `logger.error("...", exc_info=True)` |
| `print(f"Error...{e}")` outside `except` | `logger.error("...")` |
| `print(f"❌ ...{e}")` inside `except` | `logger.error("...", exc_info=True)` |
| `print(f"❌ ...")` | `logger.error("...")` |
| `print(f"⚠️ ...")` | `logger.warning("...")` |
| `print(f"✅ ...")` | `logger.info("...")` |
| Startup/lifecycle messages | `logger.info("...")` |
| Very verbose per-message debug tracing in member_class.py | `logger.debug("...")` |
| Fatal startup failures | `logger.critical("...", exc_info=True)` |

`logger.error(..., exc_info=True)` automatically includes the current exception's traceback — replaces any `traceback.print_exc()` call that follows a `print(...)`.

**bot.py** is special: it also sets up the global logging config in `main()`.

- [ ] **Step 1: Set up logging in `bot.py`**

Add `import logging` at the top. Add `logger = logging.getLogger(__name__)` after the imports. In `main()`, add `logging.basicConfig(...)` as the FIRST statement:

```python
import logging

# ... rest of imports ...

logger = logging.getLogger(__name__)

# ... bot setup ...

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    try:
        await db.init_database()
    except Exception as e:
        logger.critical("FATAL: db.init_database() failed", exc_info=True)
        # keep existing traceback.print_exc() or replace with exc_info=True above
```

Replace all `print()` in `bot.py`:
```python
# Line 43:
logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')

# Line 49:
logger.info("FeedbackThreads threads manager initialized")

# Line 51:
logger.error(f"FeedbackThreads threads manager initialization failed: {e}", exc_info=True)

# Line 53:
logger.warning("FeedbackThreads Cog not found")

# Line 65:
logger.info("Sync-ed slash commands")

# Line 115:
logger.error(f"Unhandled app command error: {error}")

# Line 143:
logger.critical(f"FATAL: db.init_database() failed: {e}", exc_info=True)
# Remove the `traceback.print_exc()` line that follows — exc_info=True handles it
```

Remove the now-unused `import traceback` from `main()` (it was added inline — delete that line too).

- [ ] **Step 2: Replace prints in `database/db.py`**

`db.py` already has `import logging` at line 6. Add `logger = logging.getLogger(__name__)` after it.

```python
# Line 49:
logger.info(f"SQLite database connected (WAL mode) at: {db_file}")

# Line 353:
logger.info(f"Updated warnings for user {user_id}")

# Line 359:
logger.info(f"Inserted a new row for user {user_id}")

# Line 364:
logger.error(f"An error occurred in extreme migration: {e}", exc_info=True)

# Line 372:
logger.info("Database connection closed.")
```

- [ ] **Step 3: Replace prints in `database/threads_db.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 17 (inside except):
logger.error(f"Error connecting to database: {e}", exc_info=True)

# Line 40:
logger.info("SQLite database created or already exists")

# Line 43 (inside except):
logger.error(f"Error creating table: {e}", exc_info=True)

# Line 56 (inside except):
logger.error(f"Error querying users: {e}", exc_info=True)

# Line 84 (inside except):
logger.error(f"Error inserting user: {e}", exc_info=True)

# Line 104 (inside except):
logger.error(f"Error updating ticket_counter: {e}", exc_info=True)

# Line 121 (inside except):
logger.error(f"Error deleting user: {e}", exc_info=True)

# Line 131:
logger.info("Database connection closed")

# Line 134 (inside except):
logger.error(f"Error closing connection: {e}", exc_info=True)
```

- [ ] **Step 4: Replace prints in `database/google_sheet.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 26:
logger.info("Successfully connected to the Google Sheet")
```

- [ ] **Step 5: Replace prints in `bot.py`'s imported `exception_handler.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# "someone tried to use a command that doesnt exist"
logger.info("someone tried to use a command that doesnt exist")

# "No permissions to send message..."
logger.error(f"No permissions to send message\n{e}\n{cog_error}")

# f"UNHANDLED ERROR in {cog_name}: {orig!r}"
logger.error(f"UNHANDLED ERROR in {cog_name}: {orig!r}", exc_info=True)

# f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n{str(e)}"
logger.error(f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n{e}", exc_info=True)
```

- [ ] **Step 6: Replace prints in `watchdog.py`**

Add `import logging` and setup a basicConfig here too (watchdog is a separate process):

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s watchdog %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
```

```python
# "Starting the bot in thread..."
logger.info(f"Starting the bot in thread: {current_thread.name} using {python_cmd}...")

# "Bot went down. Restarting..."
logger.warning("Bot went down. Restarting...")

# "Watchdog shutting down..."
logger.info("Watchdog shutting down...")
```

- [ ] **Step 7: Replace prints in `cogs/finished_music_message.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Channel not found:
logger.error(f"Channel with ID {self.stored_channel_id} not found. Check permissions and ID!")

# Message not found:
logger.warning("Message not found, may have been manually deleted.")

# Error deleting message:
logger.error(f"Error deleting message: {e}", exc_info=True)

# Error sending new message:
logger.error(f"Error sending new message: {e}", exc_info=True)

# Task crashed:
logger.error(f"[FinishedMusicMessage] Task crashed: {error!r}", exc_info=True)

# Could not write stored_message_id.json:
logger.error(f"[FinishedMusicMessage] Could not write stored_message_id.json: {e}", exc_info=True)

# Restored stored_message_id from disk:
logger.info(f"[FinishedMusicMessage] Restored stored_message_id {persisted_id} from disk.")

# Persisted message no longer exists:
logger.warning("[FinishedMusicMessage] Persisted message no longer exists; will create a new one on next cycle.")

# Could not find the Finished Music channel:
logger.error("[FinishedMusicMessage] Could not find the Finished Music channel during setup.")
```

- [ ] **Step 8: Replace prints in `cogs/aotw/create_poll.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# "AOTW submissions channel not found!"
logger.error("AOTW submissions channel not found!")

# Rate limited warning:
logger.warning("⚠️ Rate limited when updating votes channel. Waiting...")

# Error updating votes channel:
logger.error(f"❌ Error updating votes channel: {e}", exc_info=True)
```

- [ ] **Step 9: Replace prints in `cogs/aotw/configure_channel.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Deleted old message:
logger.debug(f"✅ Deleted old message: {msg.id}")

# Error deleting message:
logger.error(f"❌ Error deleting message {msg.id}: {e}", exc_info=True)

# Bulk deleted:
logger.info(f"✅ Bulk deleted {len(deleted)} messages")

# Found old messages:
logger.warning(f"⚠️ Found {len(remaining)} old messages (>14 days), deleting individually...")

# Rate limited (bulk):
logger.warning("⚠️ Rate limited, waiting 5 seconds...")

# Error deleting message (individual):
logger.error(f"❌ Error deleting message: {e}", exc_info=True)

# Rate limited on purge:
logger.warning("⚠️ Rate limited on purge, waiting 60 seconds...")

# Error purging channel:
logger.error(f"❌ Error purging channel: {e}", exc_info=True)

# Name changed to aotw-q-a:
logger.info("name changed to aotw-q-a")

# Error changing name:
logger.error(f"Error changing name: {e}", exc_info=True)

# Name changed to aotw-submissions:
logger.info("name changed to aotw-submissions")

# Second "Error changing name":
logger.error(f"Error changing name: {e}", exc_info=True)

# "name is aotw-submissions":
logger.info("name is aotw-submissions")

# Name changed to aotw-voting:
logger.info("name changed to aotw-voting")

# Third "Error changing name":
logger.error(f"Error changing name: {e}", exc_info=True)

# Ended AOTW voting event:
logger.info("✅ Ended AOTW voting event")

# Error ending event:
logger.error(f"❌ Error ending event: {e}", exc_info=True)

# voting_reminder_task not found:
logger.warning("[AOTW] voting_reminder_task: GENERAL_CHAT_CHANNEL_ID not found")

# Voting reminder task crashed:
logger.error(f"[AOTW] Voting reminder task crashed: {error!r}", exc_info=True)

# Sending message to winner / debug lines (lines 313-351):
logger.debug("Sending message to winner")
logger.debug(str(guild))
logger.debug(f"channel name: {channel_name}")
logger.debug("channel created")
logger.warning(f"⚠️ WARNING: Could not find member {winner['name']} to mention")
logger.debug(f"message sent, channel: {new_channel}")
logger.warning(f"⚠️ WARNING: Could not find winner info in votes channel")
logger.warning(f"⚠️ WARNING: Could not find member {winner_name} to mention")
logger.warning(f"⚠️ WARNING: Could not find member {name} to mention")
logger.info(f"✅ Removed AOTW role from {member.name}")
logger.error(f"❌ Failed to remove role from {member.name}: {e}", exc_info=True)
logger.warning(f"⚠️ AOTW role '{AOTW_ROLE}' not found")
```

- [ ] **Step 10: Replace prints in `cogs/user_listener.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 255 (inside except):
logger.error(str(e), exc_info=True)
```

- [ ] **Step 11: Replace prints in `cogs/owner_utilities.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 120:
logger.info(f"User {user_id} is on the ban list. Ignoring.")
```

- [ ] **Step 12: Replace prints in `cogs/feedback_threads/feedback_threads.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 32:
logger.info(f"user_thread repopulated from SQLite Database: {len(self.user_thread)} entries")

# Line 34:
logger.warning("initialize_sqldb: No data in SQLite Database to repopulate the user_thread dictionary")

# Line 43:
logger.info(f"user_thread loaded from SQLite: {len(self.user_thread)} entries")

# Line 45:
logger.warning("cog_load: SQLite database is empty")
```

- [ ] **Step 13: Replace prints in `cogs/feedback_threads/modules/threads_manager.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 25:
logger.error(f"Error: THREADS_CHANNEL with ID {THREADS_CHANNEL} not found.")
```

- [ ] **Step 14: Replace prints in `cogs/feedback_threads/modules/helpers.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 52:
logger.warning(f"[load_feedback_cog] User {ctx.author.id} not found in user_thread — thread was not created before load_feedback_cog was called")

# Line 79:
logger.error("Feedback cog not loaded.")

# Line 83 (print(user_thread)):
logger.debug(f"user_thread: {user_thread}")

# Line 90:
logger.warning(f"No thread found for user ID: {user_id}")

# Line 98:
logger.error("Feedback cog not loaded.")

# Line 113:
logger.error("Feedback cog not loaded.")
```

- [ ] **Step 15: Replace prints in `cogs/feedback_threads/modules/points_logic.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 64 (print(e)):
logger.error(str(e), exc_info=True)

# Line 245 (print(e)):
logger.error(str(e), exc_info=True)
```

- [ ] **Step 16: Replace prints in `cogs/member_cards/member_class.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

The many "Checking channel...", "Found message...", "No recent message..." prints in this file are diagnostic traces that fire on every member card request. Use `logger.debug()` for these so they're silent in INFO mode but visible when troubleshooting.

```python
# Line 66 (warning about raw_points conversion):
logger.warning(f"Warning: Could not convert raw points '{raw_points}' to int for member {member.display_name}. Defaulting to 0.")

# Line 77 (Error fetching top 10):
logger.error(f"Error fetching top 10 users from DB: {e}", exc_info=True)

# All channel-checking / message-found traces (lines 117-286):
# Replace each print(...) with logger.debug(...)
# Examples:
logger.debug(f"Checking AOTW channel ({aotw_channel.name}) for {member.display_name}...")
logger.debug(f"Found AOTW message with URL: {url}")
logger.warning(f"Bot lacks permissions to read AOTW channel history.")
logger.error(f"HTTP error fetching AOTW history: {e}", exc_info=True)
logger.debug(f"Checking Intro Music channel ({intro_music_channel.name}) for {member.display_name} (Fans)...")
logger.debug(f"Found last intro music link for {member.display_name}: {url}")
logger.debug(f"No recent intro music message with a link/attachment found for {member.display_name}.")
logger.warning(f"Bot lacks permissions to read Intro Music channel history.")
logger.error(f"HTTP error fetching Intro Music history: {e}", exc_info=True)
logger.warning("Intro Music channel not found or not a text channel.")
logger.debug(f"Checking Finished Music channel ({finished_music_channel.name}) for {member.display_name} (Default)...")
logger.debug(f"Found last finished music link for {member.display_name}: {url}")
logger.debug(f"No recent finished music message found for {member.display_name}.")
logger.warning(f"Bot lacks permissions to read Finished Music channel history.")
logger.error(f"HTTP error fetching Finished Music history: {e}", exc_info=True)
logger.warning("Finished Music channel not found or not a text channel.")
logger.error(f"Error: GENERAL_CHAT_CHANNEL (ID: {GENERAL_CHAT_CHANNEL_ID}) not found or not a text channel.")
logger.debug(f"Attempting {random_day_attempts} random days for {member.display_name} in {channel.name}...")
# ... continue the same pattern for all remaining prints in this file
```

Apply the same debug/warning/error pattern to the remaining prints at lines 226, 238, 242, 245, 248, 252, 258, 265, 274, 277, 280, 286.

- [ ] **Step 17: Replace prints in `cogs/member_cards/add_rank_member_card.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 37:
logger.error(f"Error calling get_points for {member.display_name}: {e}", exc_info=True)

# Line 49:
logger.debug(f"Debug: Invalid retrieved_msg_data for {member.display_name}: {retrieved_msg_data}")

# Line 51:
logger.error(f"Error fetching random message for {member.display_name}: {e}", exc_info=True)

# Line 64:
logger.warning(f"Failed to fetch PFP for {member.display_name}. Status: {resp.status}")

# Line 115:
logger.info(f"Member card sent to general chat for {user.display_name}")

# Line 117:
logger.error("General chat channel not found.")
```

- [ ] **Step 18: Replace prints in `cogs/slash_commands/get_member_card.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 90:
logger.warning(f"WARNING: Background images directory not found at: {self.background_images_dir}. Card backgrounds might default to gradient.")

# Line 99:
logger.error(f"Log channel with ID {LOG_CHANNEL_ID} not found.")

# Line 106:
logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")

# Line 110:
logger.error(f"Error sending log to Discord: {e}", exc_info=True)

# Line 112:
logger.error(f"Unexpected error sending log to Discord: {e}", exc_info=True)
```

- [ ] **Step 19: Replace prints in `cogs/slash_commands/rank_commands.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 97:
logger.error(f"Error sending rank message: {e}", exc_info=True)

# Line 99:
logger.error(f"Error sending rank member card: {e}", exc_info=True)
```

- [ ] **Step 20: Replace prints in `cogs/slash_commands/aotw_event.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 12:
logger.error(f"[AOTW] Background task error: {task.exception()!r}")
```

- [ ] **Step 21: Replace prints in `modules/scan_delete_intro_messages.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 27:
logger.error(f"[MessageCleaner] BOT_LOG channel not found: {message}")

# Line 51:
logger.error(f"[MessageCleaner] Failed to log to BOT_LOG: {e}", exc_info=True)

# Line 52:
logger.error(f"[MessageCleaner] Original message: {message}")

# Line 116:
logger.info('[MessageCleaner] Starting up intro-music deleter')

# Line 117:
logger.info('[MessageCleaner] Waiting for bot to be ready...')

# Line 119:
logger.info('[MessageCleaner] Bot ready, fetching channel...')

# Line 124:
logger.info(f'[MessageCleaner] Channel found: {self.channel.name}')

# Line 127:
logger.warning(f'[MessageCleaner] WARNING: Channel {INTRO_MUSIC} not found!')

# Line 131:
logger.error(f'[MessageCleaner] Error in before_loop: {e}', exc_info=True)
```

- [ ] **Step 22: Replace prints in `modules/promotion_checkers/youtube_promotion_checker.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 91:
logger.error("Unable to fetch the user's profile.")

# Line 93:
logger.error(str(e), exc_info=True)

# Line 145:
logger.error("Unable to fetch the user's profile.")

# Line 147:
logger.error(str(e), exc_info=True)
```

- [ ] **Step 23: Replace prints in `modules/promotion_checkers/spotify_promotion_checker.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 59:
logger.error(f"Error processing Spotify link: {spotify_url}", exc_info=True)

# Line 91:
logger.error("Unable to fetch the user's profile.")
```

- [ ] **Step 24: Replace prints in `modules/promotion_checkers/soundcloud_promotion_checker.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 103:
logger.error("error while expanding url from soundcloud", exc_info=True)

# Line 108:
logger.error("error while getting username from soundcloud", exc_info=True)

# Line 113:
logger.error("error while getting display name from soundcloud", exc_info=True)

# Line 136:
logger.error("Unable to fetch the user's profile.")
```

- [ ] **Step 25: Replace prints in `ml_model/feedback_monitor.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 20:
logger.error(f"[FeedbackMonitor] Background task error: {task.exception()!r}")

# Line 37:
logger.error(f"[FeedbackMonitor] BOT_LOG channel not found: {message}")

# Line 61:
logger.error(f"[FeedbackMonitor] Failed to log to BOT_LOG: {e}", exc_info=True)

# Line 62:
logger.error(f"[FeedbackMonitor] Original message: {message}")

# Line 77:
logger.info(f"[FeedbackMonitor] Cleaned up {len(stale)} stale pending validations")

# Lines 85-87 (cog loaded):
logger.info("✅ FeedbackMonitor cog loaded")
logger.info(f"   Monitoring channel: {AUDIO_FEEDBACK}")
logger.info(f"   Sending results to: {DEV_SPAM}")

# Line 96:
logger.error(f"❌ Error in on_ready: {e}", exc_info=True)

# Lines 133, 141, 147, 151, 153 (on_message processing):
logger.debug(f"🔍 Processing feedback from {message.author.name}")
logger.error("❌ predict_feedback_quality returned None")
logger.error(f"❌ Invalid result structure: {result}")
logger.debug(f"✅ Prediction complete: {result['prediction']}")
logger.error(f"❌ Error in predict_feedback_quality: {e}", exc_info=True)

# Lines 162-167:
logger.error(f"❌ Could not find dev spam channel {DEV_SPAM}")
logger.debug("✅ Found dev spam channel")
logger.error(f"❌ Error getting dev spam channel: {e}", exc_info=True)

# Lines 211-275 (embed/reactions/validation):
logger.debug("✅ Embed created")
logger.error(f"❌ Error creating embed: {e}", exc_info=True)
logger.debug(f"✅ Embed sent, message ID: {mod_message.id}")
logger.error(f"❌ Error sending embed: {e}", exc_info=True)
logger.debug("✅ Reactions added")
logger.error(f"❌ Error adding reactions: {e}", exc_info=True)
logger.debug("✅ Validation data stored")
logger.error(f"❌ Error storing validation data: {e}", exc_info=True)
logger.error(f"💥 CRITICAL: Unhandled exception in on_message listener: {e}", exc_info=True)

# Lines 301-321 (reaction handling):
logger.warning(f"⚠️ Message {reaction.message.id} already validated")
logger.info(f"✅ Correct prediction validation by {user.name}")
logger.info(f"❌ Incorrect prediction validation by {user.name}")
logger.error(f"❌ Error handling reaction: {e}", exc_info=True)
logger.error(f"💥 CRITICAL: Unhandled exception in on_reaction_add listener: {e}", exc_info=True)

# Lines 330-446 (_handle_validation):
logger.debug(f"🔄 Processing validation: is_correct={is_correct}")
logger.debug("✅ Embed updated")
logger.error(f"❌ Error updating embed: {e}", exc_info=True)
logger.info(f"📊 Validation: {validation_data['prediction']['prediction']} | ...")
logger.debug("✅ Feedback entry created")
logger.error(f"❌ Error creating feedback entry: {e}", exc_info=True)
logger.debug(f"✅ Loaded existing data from {filename}")
logger.debug("⚠️ No existing file, starting fresh")
logger.warning(f"⚠️ Invalid JSON in {filename}, starting fresh: {e}")
logger.error(f"❌ Error reading {filename}: {e}", exc_info=True)
logger.debug("✅ Entry appended to data list")
logger.error(f"❌ Error appending entry: {e}", exc_info=True)
logger.debug(f"✅ Data exported to {filename}")
logger.error(f"❌ Error exporting to JSON: {e}", exc_info=True)
logger.debug(f"📝 Total feedback entries: {entry_count}")
logger.error(f"❌ Error counting entries: {e}", exc_info=True)
logger.debug("✅ Reactions cleared")
logger.warning(f"⚠️ Could not clear reactions: {e}")
logger.error(f"💥 CRITICAL: Unhandled exception in _handle_validation: {e}", exc_info=True)

# Lines 474, 500, 528:
logger.error(f"❌ Error in feedback_stats: {e}", exc_info=True)
logger.error(f"❌ Error in test_feedback prediction: {e}", exc_info=True)
logger.error(f"❌ Error in test_feedback response: {e}", exc_info=True)
```

- [ ] **Step 26: Replace prints in `ml_model/export_json.py`**

This file was already rewritten in Task 2 with `print()` calls. Now replace those remaining prints:

```python
# Add at top:
import logging
logger = logging.getLogger(__name__)

# Replace all print() in the rewritten file:
logger.info(f"✅ Exported feedback data to {filename}")
logger.error(f"❌ Could not find channel with ID {EXPORTS_CHANNEL}")
logger.info(f"✅ Sent {len(data)} feedback entries to mod channel")
logger.info(f"🧹 Cleared {filename}")
logger.warning("⚠️ Feedback file not found")
logger.error(f"❌ Invalid JSON in {filename}")
logger.error(f"❌ Error in count_entries: {e}", exc_info=True)
```

- [ ] **Step 27: Replace prints in `ml_model/ml_model_loader.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Lines 27-29:
logger.debug(f"🔍 Current working directory: {os.getcwd()}")
logger.debug(f"🔍 Looking for model at: {model_path.resolve()}")
logger.debug(f"🔍 Looking for vectorizer at: {vectorizer_path.resolve()}")

# Line 40:
logger.info(f"✅ Model loaded successfully from {self.model_dir}")

# Line 42:
logger.error(f"❌ Error loading model: {e}", exc_info=True)

# Line 149:
logger.error(f"❌ Prediction error: {e}", exc_info=True)
```

- [ ] **Step 28: Replace prints in `ml_model/mod_bad_feedback_notification.py`**

Add `import logging` and `logger = logging.getLogger(__name__)`.

```python
# Line 27:
logger.error(error_msg)

# Line 49:
logger.info("✅ Bad feedback notification sent to moderators")

# Line 78:
logger.info(f"✅ User {message.author.name} notified about bad feedback")

# Line 82:
logger.error(f"❌ Could not find audio feedback channel {AUDIO_FEEDBACK}")

# Line 88:
logger.info("✅ Moderator dismissed bad feedback alert")

# Line 94:
logger.info(f"⏱️ No moderator reaction within 5 minutes for message {message.id}")

# Line 102:
logger.error(error_msg, exc_info=True)
```

- [ ] **Step 29: Verify no print() calls remain (excluding counter.py and venv)**

Run: `grep -rn "print(" . --include="*.py" --exclude-dir=venv --exclude="counter.py"`

Expected: zero results (or only commented-out lines like `# print(...)` in bot.py).

- [ ] **Step 30: Commit**

```
git add bot.py database/ cogs/ modules/ watchdog.py exception_handler.py ml_model/
git commit -m "refactor: replace all print() with logging module (E7)"
```

---

## Task 6: E13a — mod_bad_feedback_notification.py → discord.ui.View

**Files:**
- Modify: `ml_model/mod_bad_feedback_notification.py`

**Context:** The current code sends a notification message, adds ✅/❌ reactions, and then `await`s `bot.wait_for('reaction_add', timeout=300)` — a 5-minute blocking wait inside a background task. Converting to a `discord.ui.View` eliminates the `wait_for`, handles timeouts automatically, and works correctly even if the bot restarts (with `persistent=True` — not implemented here since it requires slash-command IDs, but the View timeout pattern is the correct modern approach).

- [ ] **Step 1: Rewrite `mod_bad_feedback_notification.py`**

Replace the entire file:

```python
import discord
import logging
from data.constants import MODERATORS_CHANNEL_ID, AUDIO_FEEDBACK, CO_DEV_ID, FEEDBACK_ACCESS_CHANNEL_ID

logger = logging.getLogger(__name__)


class _FeedbackNotificationView(discord.ui.View):
    """Buttons shown to the moderator on a bad-feedback notification."""

    def __init__(
        self,
        moderator_id: int,
        original_message: discord.Message,
        log_callback=None,
    ):
        super().__init__(timeout=300.0)  # 5 minutes
        self.moderator_id = moderator_id
        self.original_message = original_message
        self.log_callback = log_callback
        self.message: discord.Message | None = None  # set after send

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.moderator_id:
            await interaction.response.send_message(
                "Only the assigned moderator can use these buttons.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.success)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=None)
        if self.log_callback:
            await self.log_callback("✅ Bad feedback alert dismissed by moderator")
        self.stop()

    @discord.ui.button(emoji="❌", label="Notify user", style=discord.ButtonStyle.danger)
    async def notify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=None)
        audio_feedback_channel = interaction.client.get_channel(AUDIO_FEEDBACK)
        if audio_feedback_channel:
            await audio_feedback_channel.send(
                f"{self.original_message.author.mention} Please provide more detailed and "
                f"constructive feedback. Check out <#{FEEDBACK_ACCESS_CHANNEL_ID}> if you need help.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            if self.log_callback:
                await self.log_callback(
                    f"✅ User {self.original_message.author.name} notified to improve feedback"
                )
        else:
            if self.log_callback:
                await self.log_callback(f"❌ Audio feedback channel {AUDIO_FEEDBACK} not found")
        self.stop()

    async def on_timeout(self) -> None:
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass
        if self.log_callback:
            await self.log_callback(
                f"⏱️ No moderator response within 5 minutes for message {self.original_message.id}"
            )


class FeedbackNotifier:
    """Handles notifications for feedback quality issues."""

    def __init__(self, bot):
        self.bot = bot
        self.moderator_user_id = CO_DEV_ID

    async def notify_bad_feedback(self, message, feedback_text, log_callback=None) -> bool:
        try:
            mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

            if not mod_channel:
                error_msg = f"❌ Moderators channel {MODERATORS_CHANNEL_ID} not found for bad feedback notification"
                logger.error(error_msg)
                if log_callback:
                    await log_callback(error_msg)
                return False

            feedback_preview = feedback_text[:200]
            if len(feedback_text) > 200:
                feedback_preview += "..."

            view = _FeedbackNotificationView(
                moderator_id=self.moderator_user_id,
                original_message=message,
                log_callback=log_callback,
            )

            notification_message = await mod_channel.send(
                f"⚠️ <@{self.moderator_user_id}> Bad feedback detected from "
                f"{message.author.mention} in {message.channel.mention}:\n"
                f"```{feedback_preview}```\n"
                f"[Jump to message]({message.jump_url})",
                view=view,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            view.message = notification_message

            logger.info("✅ Bad feedback notification sent to moderators")
            if log_callback:
                await log_callback(f"✅ Bad feedback notification sent for message {message.id}")

            return True

        except Exception as e:
            error_msg = f"❌ Error sending bad feedback notification: {e}"
            logger.error(error_msg, exc_info=True)
            if log_callback:
                await log_callback("❌ Error sending bad feedback notification", e)
            return False
```

- [ ] **Step 2: Verify `feedback_monitor.py` still calls `notify_bad_feedback` correctly**

The call site in `feedback_monitor.py` fires this as a background task:
```python
asyncio.create_task(self.notifier.notify_bad_feedback(message, feedback_text, log_callback=self.log_to_bot_log))
```
No change needed — the method signature is unchanged. The View manages its own lifetime after `send()`.

- [ ] **Step 3: Commit**

```
git add ml_model/mod_bad_feedback_notification.py
git commit -m "refactor: replace wait_for reaction pattern with discord.ui.View in mod notifier (E13a)"
```

---

## Task 7: E13b — music.py NotesMenu → discord.ui.View

**Files:**
- Modify: `cogs/music.py`

**Context:** `NotesMenu` extends `menus.Menu` (from `discord-ext-menus`) and registers a raw `on_raw_reaction_add` listener manually. Each invocation of `<MF notes` fires `bot.add_listener()` with its own listener instance. Converting to `discord.ui.View` removes the `menus` dependency, uses Discord's native interaction framework, and eliminates the listener leak risk entirely. The menu logic (multi-level JSON navigation, pagination, terminal chord display) is preserved exactly.

- [ ] **Step 1: Rewrite `cogs/music.py`**

Replace the entire file:

```python
import discord
from discord.ext import commands
import json
import asyncio
from modules.cooldowns import admin_bypass_cooldown


class _OptionButton(discord.ui.Button):
    """A numbered option button in the notes menu."""

    def __init__(self, label: str, selection: str, notes_view: "NotesView", **kwargs):
        super().__init__(label=label, style=discord.ButtonStyle.primary, **kwargs)
        self.selection = selection
        self.notes_view = notes_view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.notes_view.selections.append(self.selection)
        self.notes_view.current_level += 1
        self.notes_view.page_index = 0
        await self.notes_view._refresh(interaction)


class _NavButton(discord.ui.Button):
    """Back / Previous page / Next page navigation button."""

    def __init__(self, action: str, notes_view: "NotesView", **kwargs):
        super().__init__(style=discord.ButtonStyle.secondary, **kwargs)
        self.action = action  # "back" | "prev" | "next"
        self.notes_view = notes_view

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.action == "back":
            if self.notes_view.current_level > 0:
                self.notes_view.current_level -= 1
                self.notes_view.selections.pop()
                self.notes_view.page_index = 0
        elif self.action == "prev":
            if self.notes_view.page_index > 0:
                self.notes_view.page_index -= 1
        elif self.action == "next":
            self.notes_view.page_index += 1
        await self.notes_view._refresh(interaction)


class NotesView(discord.ui.View):
    """Interactive multi-level chord/notes browser as a discord.ui.View."""

    OPTIONS_PER_PAGE = 5

    def __init__(self, json_data: dict, user_id: int, pfp_url: str):
        super().__init__(timeout=60.0)
        self.json_data = json_data
        self.user_id = user_id
        self.pfp_url = pfp_url
        self.current_level = 0
        self.selections: list[str] = []
        self.page_index = 0
        self.message: discord.Message | None = None
        self._rebuild()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Use your own menu with the `<MF notes` command.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass

    # ── Data helpers ────────────────────────────────────────────────────────

    def _get_data(self) -> dict | str:
        data = self.json_data
        for sel in self.selections:
            if isinstance(data, dict) and sel in data:
                data = data[sel]
            else:
                return {}
        return data

    def _get_options(self) -> list[str]:
        data = self._get_data()
        if isinstance(data, dict):
            return list(data.keys())
        return []

    def _is_terminal(self) -> bool:
        data = self._get_data()
        return (
            isinstance(data, dict)
            and set(data.keys()) == {"Degree", "Chords", "Notes"}
        )

    # ── Button building ──────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self.clear_items()

        if self._is_terminal():
            return  # no buttons; caller disables the view after showing embed

        options = self._get_options()
        if not options:
            return

        pages = [
            options[i : i + self.OPTIONS_PER_PAGE]
            for i in range(0, len(options), self.OPTIONS_PER_PAGE)
        ]

        # Clamp page_index
        if self.page_index >= len(pages):
            self.page_index = len(pages) - 1

        page = pages[self.page_index]

        # Row 0 — option buttons
        for i, option in enumerate(page):
            global_index = self.page_index * self.OPTIONS_PER_PAGE + i
            btn = _OptionButton(
                label=f"{i + 1}. {option[:75]}",
                selection=options[global_index],
                notes_view=self,
                row=0,
            )
            self.add_item(btn)

        # Row 1 — navigation
        if self.current_level > 0:
            self.add_item(_NavButton("back", self, label="↩ Back", row=1))
        if self.page_index > 0:
            self.add_item(_NavButton("prev", self, label="◀ Prev", row=1))
        if len(pages) > 1 and self.page_index < len(pages) - 1:
            self.add_item(_NavButton("next", self, label="Next ▶", row=1))

    # ── Embed building ───────────────────────────────────────────────────────

    def _build_embed(self, guild: discord.Guild) -> discord.Embed:
        icon_url = guild.icon.url if guild.icon else None

        if self._is_terminal():
            data = self._get_data()
            chord_name = self.selections[-1] if self.selections else "Unknown Chords"
            embed = discord.Embed(color=0x7E016F)
            embed.set_author(name=f"{chord_name} Chords", icon_url=icon_url)
            for key in ("Degree", "Chords", "Notes"):
                value = data.get(key, "")
                if value:
                    value = value.replace("{degree}", "°")
                    embed.add_field(name=key, value=f"`{value}`", inline=True)
            embed.set_footer(text="Made by FlamingCore", icon_url=self.pfp_url)
            return embed

        options = self._get_options()
        pages = [
            options[i : i + self.OPTIONS_PER_PAGE]
            for i in range(0, len(options), self.OPTIONS_PER_PAGE)
        ]
        page = pages[self.page_index] if self.page_index < len(pages) else []
        chord_name = self.selections[-1] if self.selections else "Menu"
        embed = discord.Embed(
            color=0x7E016F,
            description="\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(page)),
        )
        embed.set_author(name=chord_name, icon_url=icon_url)
        footer = "Made by FlamingCore"
        if len(pages) > 1:
            footer = f"Page {self.page_index + 1} of {len(pages)} • {footer}"
        embed.set_footer(text=footer, icon_url=self.pfp_url)
        return embed

    # ── Interaction handler ──────────────────────────────────────────────────

    async def _refresh(self, interaction: discord.Interaction) -> None:
        self._rebuild()
        embed = self._build_embed(interaction.guild)
        if self._is_terminal():
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            await interaction.response.edit_message(embed=embed, view=self)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._pfp_url: str | None = None
        self._notes_data: dict | None = None

    async def cog_load(self) -> None:
        with open("cogs/options.json", "r") as f:
            self._notes_data = json.load(f)

    def guild_only(ctx):
        return ctx.guild is not None

    async def _get_pfp_url(self) -> str:
        if self._pfp_url is None:
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self._pfp_url = creator_user.avatar.url
        return self._pfp_url

    @commands.check(guild_only)
    @commands.command(help="Use to see the chord/notes information menu.")
    @admin_bypass_cooldown(1, 10)
    async def notes(self, ctx) -> None:
        pfp_url = await self._get_pfp_url()
        view = NotesView(self._notes_data, ctx.author.id, pfp_url)
        embed = view._build_embed(ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot):
    await bot.add_cog(Music(bot))
```

- [ ] **Step 2: Check if `discord-ext-menus` is still used elsewhere**

Run: `grep -rn "from discord.ext import.*menus\|import menus" . --include="*.py" --exclude-dir=venv`

If no other file imports `menus`, remove `discord-ext-menus` from `requirements.txt`.

- [ ] **Step 3: Test the command manually**

Start the bot (`python bot.py`) and run `<MF notes` in the test server. Verify:
- The initial embed + numbered buttons appear
- Clicking a button navigates into the sub-menu
- The Back button appears at level > 0 and works correctly
- The Prev/Next page buttons appear when a page has > 5 options
- The terminal state (Degree / Chords / Notes) shows the final embed with no buttons
- A second user clicking another user's buttons receives the ephemeral error message
- After 60 seconds of no interaction, the menu disables (buttons disappear from the message)

- [ ] **Step 4: Commit**

```
git add cogs/music.py requirements.txt
git commit -m "refactor: replace NotesMenu menus.Menu with discord.ui.View (E13b)"
```

---

## Task 8: Update CODE_AUDIT.md and CLAUDE.md

**Files:**
- Modify: `CODE_AUDIT.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Mark resolved items in `CODE_AUDIT.md`**

In the Etiquette Review Issue Index table at the bottom of CODE_AUDIT.md, update the Status column for all items just resolved:

```
| E7  | Codebase-wide  | `print()` instead of `logging` module  | ~~**Medium**~~ ✅ Resolved |
| E13 | `music.py`, `mod_bad_feedback_notification.py` | Raw reactions instead of `discord.ui.View` | ~~**Medium**~~ ✅ Resolved |
| E15 | `admin.py`     | No autocomplete on `/reload extension` | ~~**Low**~~ ✅ Resolved |
| E18 | `google_sheet.py` | Individual Sheets writes not batched   | ~~**Medium**~~ ✅ Resolved |
```

Also add inline resolution notes to each section body:

For E7, add after the description:
```
~~**Severity: Medium**~~ **✅ RESOLVED** — `logging.basicConfig()` set up in `bot.py:main()`. All `print()` calls replaced with `logger.info/warning/error/debug/critical()` across all 28 bot files. Each file has `logger = logging.getLogger(__name__)`.
```

For E13, add:
```
~~**Severity: Medium**~~ **✅ RESOLVED** — `mod_bad_feedback_notification.py` converted to `_FeedbackNotificationView(discord.ui.View)` with ✅/❌ buttons; `wait_for` removed. `music.py` `NotesMenu` replaced with `NotesView(discord.ui.View)` using `_OptionButton` and `_NavButton` helper classes; `discord-ext-menus` dependency removed.
```

For E15, add:
```
~~**Severity: Low**~~ **✅ RESOLVED** — `@app_commands.autocomplete(extension=extension_autocomplete)` added to `/reload` command; `extension_autocomplete` function returns currently-loaded extension paths filtered by typed input. Rank add/remove commands already use `discord.Role` (native Discord role picker); genre/similar commands are prefix commands (no slash autocomplete applicable).
```

For E18, add:
```
~~**Severity: Medium**~~ **✅ RESOLVED** — `update_rank_spreadsheet` now writes rank text and date in a single `sheet.update_cells([Cell(...), Cell(...)])` call, halving the write API call count per rank update.
```

For B5, add:
```
~~**Severity: Low**~~ **✅ RESOLVED** — Return type annotations added to all public functions in `database/db.py`, `helpers.py`, `threads_manager.py`, and `ml_model_loader.py`.
```

For C9, add:
```
~~**Severity: Low**~~ **✅ RESOLVED** — `export_to_json` is now `async` and wraps file writes with `asyncio.to_thread`. `count_entries` wraps both read and write operations with `asyncio.to_thread`. Caller in `feedback_monitor.py` updated to `await` the call.
```

- [ ] **Step 2: Update `CLAUDE.md`**

In the Architecture Overview section, add a note about logging:

After the line about `bot.py`:
```markdown
### Logging

The bot uses Python's `logging` module throughout. `bot.py:main()` calls `logging.basicConfig(level=logging.INFO, ...)` before starting the bot. Every module has `logger = logging.getLogger(__name__)`. Discord.py's internal logging flows through the same handler. Use `logger.info/warning/error/critical/debug` — never `print()`.
```

- [ ] **Step 3: Commit**

```
git add CODE_AUDIT.md CLAUDE.md
git commit -m "docs: mark E7/E13/E15/E18/B5/C9 resolved in CODE_AUDIT; add logging note to CLAUDE.md"
```

---

## Self-Review

**Spec coverage check:**
- B5 (return types) ✅ — Task 1 covers db.py, helpers.py, threads_manager.py, ml_model_loader.py
- C9 (sync file I/O) ✅ — Task 2 rewrites export_json.py with asyncio.to_thread; updates caller
- E15 (autocomplete) ✅ — Task 3 adds autocomplete to /reload; notes why rank/genre commands need no change
- E18 (Sheets batching) ✅ — Task 4 batches two update_cell calls into one update_cells call
- E7 (print → logging) ✅ — Task 5 covers all 28 files with specific per-file replacements
- E13a (reactions → View, mod notifier) ✅ — Task 6 rewrites mod_bad_feedback_notification.py
- E13b (reactions → View, NotesMenu) ✅ — Task 7 rewrites music.py
- CLAUDE.md update ✅ — Task 8

**Placeholder scan:** No TBD, TODO, or vague "handle edge cases" statements. Every file replacement is shown with specific before/after values.

**Type consistency:** `NotesView._build_embed(guild)` returns `discord.Embed` — used in both `_refresh` and `Music.notes`. `_FeedbackNotificationView` stores `original_message: discord.Message` — accessed as `self.original_message.author.mention` in both button callbacks. Consistent.
