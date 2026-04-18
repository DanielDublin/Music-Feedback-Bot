# Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all open issues from CODE_AUDIT.md, ordered by severity — critical correctness bugs first, then reliability, then code quality.

**Architecture:** Fixes are applied in-place to existing files with no new abstractions introduced. Each task is scoped to one or two closely related files so changes are easy to review and roll back independently.

**Tech Stack:** Python 3.11, discord.py 2.x, aiosqlite, asyncio

> **Note:** This project has no automated test suite. Each task ends with a manual verification step and a commit.

---

## Task 1: Fix `db.py` — `add_user` leaves `users_dict` empty (N11)

**Files:**
- Modify: `database/db.py` — `update_dict_from_db` else branch

**Problem:** When a user isn't in the DB, `update_dict_from_db` calls `add_user(called_from_update_func=True)` which sets `users_dict[user_id] = {}` but never populates the keys. The very next line in `fetch_points` does `return users_dict[user_id]["Points"]` → `KeyError`.

- [ ] **Step 1: Open `database/db.py` and locate the else branch in `update_dict_from_db` (around line 87)**

```python
    else:
        del users_dict[user_id]
        await add_user(user_id, called_from_update_func=True)
```

- [ ] **Step 2: Add default population after `add_user`**

Replace the else branch with:

```python
    else:
        del users_dict[user_id]
        await add_user(user_id, called_from_update_func=True)
        users_dict[user_id] = {"Points": 0, "Warnings": 0, "Kicks": 0}
```

- [ ] **Step 3: Verify manually**

Run the bot and trigger `<mf points` as a user who has never been seen before. Confirm no `KeyError` in console and the response shows 0 points.

- [ ] **Step 4: Commit**

```bash
git add database/db.py
git commit -m "fix: populate users_dict after add_user to prevent KeyError on first fetch"
```

---

## Task 2: Fix `helpers.py` — `load_feedback_cog` implicit None return (A1)

**Files:**
- Modify: `cogs/feedback_threads/modules/helpers.py` — `load_feedback_cog`

**Problem:** If `ctx.author.id` is not in `feedback_cog.user_thread`, the `else: pass` branch runs and the function returns `None`. Every caller unpacks the return as `thread, ticket_counter, points_logic, user_id = ...` which crashes with `TypeError: cannot unpack non-iterable NoneType object`.

This shouldn't happen in normal flow (because `check_if_feedback_thread` is always called before `load_feedback_cog` and creates the thread entry), but it can happen if the thread cog is in a bad state.

- [ ] **Step 1: Open `cogs/feedback_threads/modules/helpers.py`, find `load_feedback_cog` (around line 33)**

Current code:
```python
    if ctx.author.id in feedback_cog.user_thread:
        user_thread = feedback_cog.user_thread
        points_logic = PointsLogic(self.bot, user_thread)
        user_id = str(ctx.author.id)
        ticket_counter = user_thread[ctx.author.id][1]
        thread_id = user_thread[ctx.author.id][0]
        thread = await self.bot.fetch_channel(thread_id)
    else:
        pass

    return thread, ticket_counter, points_logic, user_id
```

- [ ] **Step 2: Replace `else: pass` with an explicit error log and raise**

```python
    if ctx.author.id in feedback_cog.user_thread:
        user_thread = feedback_cog.user_thread
        points_logic = PointsLogic(self.bot, user_thread)
        user_id = str(ctx.author.id)
        ticket_counter = user_thread[ctx.author.id][1]
        thread_id = user_thread[ctx.author.id][0]
        thread = await self.bot.fetch_channel(thread_id)
    else:
        print(f"[load_feedback_cog] User {ctx.author.id} not found in user_thread — thread was not created before load_feedback_cog was called")
        raise RuntimeError(f"No feedback thread found for user {ctx.author.id}")

    return thread, ticket_counter, points_logic, user_id
```

- [ ] **Step 3: Verify manually**

Run the bot and use `<mfr` normally. The happy path should work. If a thread is somehow missing the error is now explicit in the console rather than a confusing unpack crash.

- [ ] **Step 4: Commit**

```bash
git add cogs/feedback_threads/modules/helpers.py
git commit -m "fix: raise RuntimeError instead of implicit None return in load_feedback_cog"
```

---

## Task 3: Fix `user_listener.py` — `asyncio.sleep(86400)` coroutine leak (A2)

**Files:**
- Modify: `cogs/user_listener.py` — `on_message` handler

**Problem:** Every message in `INTRO_MUSIC` spawns a coroutine that sleeps for 24 hours. With any traffic these stack up indefinitely. `scan_delete_intro_messages.py` already handles this with a proper task loop — this code is fully redundant.

- [ ] **Step 1: Open `cogs/user_listener.py`, find the elif block around line 67**

```python
        elif ctx.channel.id == INTRO_MUSIC and not ctx.author.guild_permissions.administrator: # Music intro delete 24h
           try:
               await asyncio.sleep(60*60*24) # 24 hours
               await ctx.delete()
           except Exception as e:
               print(str(e))
```

- [ ] **Step 2: Delete the entire elif block**

Remove it completely. The surrounding structure should now flow from the `'primus'` check to `on_member_join`. The import `import asyncio` at the top of the file is still needed for other uses so leave it.

- [ ] **Step 3: Verify manually**

Restart the bot. Send a message to the intro-music channel. Confirm the bot no longer tries to delete it inline (the task loop in `scan_delete_intro_messages.py` handles deletion on its own schedule).

- [ ] **Step 4: Commit**

```bash
git add cogs/user_listener.py
git commit -m "fix: remove 24h asyncio.sleep in on_message — scan_delete_intro_messages already handles this"
```

---

## Task 4: Fix `scan_delete_intro_messages.py` — `self.channel` not initialised in `__init__` (T4)

**Files:**
- Modify: `modules/scan_delete_intro_messages.py`

**Problem:** `self.channel` is only assigned inside the `before_loop` hook. If that hook raises before the assignment, the loop body's `if self.channel is None` guard throws `AttributeError: 'MessageCleaner' object has no attribute 'channel'`, permanently killing the task.

- [ ] **Step 1: Open `modules/scan_delete_intro_messages.py`, find `__init__`**

- [ ] **Step 2: Add `self.channel = None` to `__init__`**

```python
def __init__(self, bot):
    self.bot = bot
    self.channel = None
    self.clean_old_messages.start()
```

- [ ] **Step 3: Commit**

```bash
git add modules/scan_delete_intro_messages.py
git commit -m "fix: initialise self.channel = None in MessageCleaner __init__ to prevent AttributeError"
```

---

## Task 5: Fix `finished_music_message.py` — task loop has no error handler (T2)

**Files:**
- Modify: `cogs/finished_music_message.py`

**Problem:** `delete_and_repost_cycle` has no `reconnect=True` and no `.error` handler. Any exception or network blip silently kills the loop permanently.

- [ ] **Step 1: Open `cogs/finished_music_message.py`, find the `@tasks.loop` decorator on `delete_and_repost_cycle`**

- [ ] **Step 2: Add `reconnect=True` to the decorator**

```python
@tasks.loop(hours=6, reconnect=True)
async def delete_and_repost_cycle(self):
```

- [ ] **Step 3: Add an error handler immediately after the loop method**

Place this directly after the `delete_and_repost_cycle` method body:

```python
@delete_and_repost_cycle.error
async def delete_and_repost_cycle_error(self, error):
    print(f"[FinishedMusicMessage] Task crashed: {error!r}")
    if not self.delete_and_repost_cycle.is_running():
        self.delete_and_repost_cycle.restart()
```

- [ ] **Step 4: Commit**

```bash
git add cogs/finished_music_message.py
git commit -m "fix: add reconnect=True and error handler to delete_and_repost_cycle task loop"
```

---

## Task 6: Fix `aotw_event.py` — unretieved task exceptions (T6) and duplicate call (N3)

**Files:**
- Modify: `cogs/slash_commands/aotw_event.py`

**Problem (T6):** `asyncio.create_task(self.check_aotw_channel_announcement())` — if the task raises, the exception is attached to the Task object but never retrieved, so failures are invisible.

**Problem (N3):** `check_aotw_channel_announcement` is called twice in succession at line 387; the second call is missing its required argument and will raise `TypeError`.

- [ ] **Step 1: Open `cogs/slash_commands/aotw_event.py`, add a module-level error-logging callback near the top of the file (after imports)**

```python
def _log_task_error(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        print(f"[AOTW] Background task error: {task.exception()!r}")
```

- [ ] **Step 2: Find every `asyncio.create_task(self.check_aotw_channel_announcement(...))` call and attach the callback**

```python
task = asyncio.create_task(self.check_aotw_channel_announcement(...))
task.add_done_callback(_log_task_error)
```

- [ ] **Step 3: Find the duplicate call at line ~387 and remove the second (argumentless) call**

Keep only the call that passes the required argument. Delete the bare `self.check_aotw_channel_announcement()` line directly below it.

- [ ] **Step 4: Commit**

```bash
git add cogs/slash_commands/aotw_event.py
git commit -m "fix: log aotw background task exceptions; remove duplicate check_aotw_channel_announcement call"
```

---

## Task 7: Fix `music.py` — `NotesMenu` listener never removed (T5)

**Files:**
- Modify: `cogs/music.py`

**Problem:** `NotesMenu.__init__` calls `self.bot.add_listener(self.on_raw_reaction_add)` but there is no matching `remove_listener`. Every `<MF notes` invocation adds another permanent listener. After N calls, N copies fire for every reaction event.

- [ ] **Step 1: Open `cogs/music.py`, find `NotesMenu` class and locate where the menu session ends or times out**

- [ ] **Step 2: Add `remove_listener` in the cleanup/timeout path**

Find the method that handles timeout or menu close (typically a `try/except asyncio.TimeoutError` or a `stop` method) and add:

```python
self.bot.remove_listener(self.on_raw_reaction_add)
```

Also add it in any early-exit code path (e.g. if the user picks a final option).

- [ ] **Step 3: Commit**

```bash
git add cogs/music.py
git commit -m "fix: remove NotesMenu reaction listener on session end to prevent listener accumulation"
```

---

## Task 8: Fix easy one-line bugs — N1, N4, N5, N7, A7, A13

**Files:**
- Modify: `cogs/slash_commands/rank_commands.py` (N1, N5)
- Modify: `cogs/slash_commands/admin.py` (N4)
- Modify: `cogs/feedback_threads/modules/threads_manager.py` (N7)
- Modify: `modules/promotion_checkers/spotify_promotion_checker.py` (A7)
- Modify: `cogs/user_listener.py` (A13)

- [ ] **Step 1: `rank_commands.py` N1 — pass `new_role.name` not `new_role`**

Find the line: `await update_rank_spreadsheet(user.id, new_role, ...)`
Change to: `await update_rank_spreadsheet(user.id, new_role.name, ...)`

- [ ] **Step 2: `rank_commands.py` N5 — remove duplicate `rank_options` list and duplicate `import datetime`**

Find and delete the second definition of `rank_options` and the second `import datetime` line.

- [ ] **Step 3: `admin.py` N4 — remove module-level print**

Find the bare `print("Processing complete")` at module scope (line ~185) and delete it.

- [ ] **Step 4: `threads_manager.py` N7 — remove dead `setup()` function**

Delete the entire function at the bottom of the file:
```python
async def setup(bot):
    await bot.add_cog(ThreadsManager(bot))
```

- [ ] **Step 5: `spotify_promotion_checker.py` A7 — fix wrong None check**

Find: `if urls is None:`
Change to: `if not urls:`

- [ ] **Step 6: `user_listener.py` A13 — remove unused imports**

Delete lines 1–2:
```python
from re import T
from tarfile import NUL
```

- [ ] **Step 7: Commit all**

```bash
git add cogs/slash_commands/rank_commands.py cogs/slash_commands/admin.py cogs/feedback_threads/modules/threads_manager.py modules/promotion_checkers/spotify_promotion_checker.py cogs/user_listener.py
git commit -m "fix: N1 role.name, N4 remove debug print, N5 dedup rank_options, N7 dead setup(), A7 None check, A13 unused imports"
```

---

## Task 9: Fix hardcoded constants — A4, A5, A8, A12

**Files:**
- Modify: `ml_model/feedback_monitor.py` (A4)
- Modify: `ml_model/export_json.py` (A4)
- Modify: `ml_model/mod_bad_feedback_notification.py` (A4, A5)
- Modify: `cogs/guild_events.py` (A8)
- Modify: `bot.py` (A12)

- [ ] **Step 1: Check that `CO_DEV_ID` exists in `data/constants.py`**

Open `data/constants.py` and confirm `CO_DEV_ID` is defined. If it's missing, add it with the value `412733389196623879`.

- [ ] **Step 2: `feedback_monitor.py` A4 — replace hardcoded ID**

Add import at the top: `from data.constants import CO_DEV_ID`
Find: `f"<@{412733389196623879}> New feedback!"`
Change to: `f"<@{CO_DEV_ID}> New feedback!"`

- [ ] **Step 3: `export_json.py` A4 — replace hardcoded ID**

Add import: `from data.constants import CO_DEV_ID`
Find: `f"<@{412733389196623879}> New Export!"`
Change to: `f"<@{CO_DEV_ID}> New Export!"`

- [ ] **Step 4: `mod_bad_feedback_notification.py` A4 + A5 — replace hardcoded ID and channel ID**

Add import: `from data.constants import CO_DEV_ID, FEEDBACK_ACCESS_CHANNEL_ID`
Find: `self.moderator_user_id = 412733389196623879`
Change to: `self.moderator_user_id = CO_DEV_ID`

Find: `f"Check out <#959150439692128277> if you need help."`
Change to: `f"Check out <#{FEEDBACK_ACCESS_CHANNEL_ID}> if you need help."`

- [ ] **Step 5: `guild_events.py` A8 — cache `pfp_url`**

Find the cog class `__init__` and add: `self.pfp_url = ""`

Find every place `fetch_user` is called to get the pfp (inside a command handler) and wrap it with the cache pattern:
```python
if not self.pfp_url:
    creator_user = await self.bot.fetch_user(self.bot.owner_id)
    self.pfp_url = creator_user.avatar.url
```

- [ ] **Step 6: `bot.py` A12 — remove unused variable, fix IS_READY type, remove unnecessary globals, fix hardcoded guild ID**

  - Delete: `general_chat = bot.get_channel(FEEDBACK_CHANNEL_ID)` (line ~76, result never used)
  - Change: `IS_READY = 0` → `IS_READY = False`
  - Change: `IS_READY += 1` → `IS_READY = True`
  - Remove `global bot` from `on_ready` and `main` (bot is never reassigned in these functions)
  - In the `/sync` command: change `discord.Object(id=server_id)` — `server_id` is already `SERVER_ID` via env; confirm it uses `SERVER_ID` from constants or the env var consistently

- [ ] **Step 7: Commit**

```bash
git add ml_model/feedback_monitor.py ml_model/export_json.py ml_model/mod_bad_feedback_notification.py cogs/guild_events.py bot.py
git commit -m "fix: replace hardcoded IDs with constants; cache pfp_url in guild_events; clean up bot.py flags"
```

---

## Task 10: Fix `user_listener.py` — double audit log query (A6) and param name (B4)

**Files:**
- Modify: `cogs/user_listener.py`

- [ ] **Step 1: Fix double audit log query (A6) — `on_member_remove`**

Find the nested `async for` block (around line 108):

```python
async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
    cutoff_time = discord.utils.utcnow() - timedelta(minutes=2)
    if entry.target == member and entry.created_at >= cutoff_time:
        try:
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                audit_log_entry = entry
                break
        except Exception as e:
            print(str(e))
```

Replace with:

```python
async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
    cutoff_time = discord.utils.utcnow() - timedelta(minutes=2)
    if entry.target == member and entry.created_at >= cutoff_time:
        audit_log_entry = entry
```

- [ ] **Step 2: Rename `on_message` parameter from `ctx` to `message` (B4)**

Change the method signature:
```python
async def on_message(self, message):
```

Then do a find-and-replace within this method only: every `ctx.` → `message.` and every standalone `ctx` reference → `message`. Be careful not to touch other methods.

- [ ] **Step 3: Commit**

```bash
git add cogs/user_listener.py
git commit -m "fix: remove duplicate audit log query in on_member_remove; rename on_message ctx -> message"
```

---

## Task 11: Fix `helpers.py` — `@staticmethod`, unnecessary `async`, wrapper methods, `fetch_channel` (B2, A9, A10, D1)

**Files:**
- Modify: `cogs/feedback_threads/modules/helpers.py`
- Modify: `cogs/feedback_threads/modules/points_logic.py` (callers of `add/remove_points_for_edits`)

- [ ] **Step 1: B2 — Add `@staticmethod` to three methods**

Find `get_thread_id_no_ctx`, `delete_user_from_user_thread`, `delete_user_from_db` (around lines 72, 91, 104).
Add `@staticmethod` decorator above each.

- [ ] **Step 2: A9 — Remove `async` from `shorten_message`**

```python
def shorten_message(self, content: str, max_length: int):
    if len(content) > max_length:
        return content[:max_length - 3] + "..."
    return content
```

Then find all callers: `await self.helpers.shorten_message(...)` → `self.helpers.shorten_message(...)` (remove `await`).

Search for callers in: `points_logic.py`, `message_edits.py`.

- [ ] **Step 3: A10 — Remove `add_points_for_edits` and `remove_points_for_edits`**

Delete both wrapper methods from `helpers.py`.

In `points_logic.py`, find:
```python
await self.helpers.add_points_for_edits(user_id, points_to_add)
```
Replace with:
```python
await db.add_points(user_id, points_to_add)
```

Find:
```python
await self.helpers.remove_points_for_edits(user_id, points_to_remove)
```
Replace with:
```python
await db.reduce_points(user_id, points_to_remove)
```

Confirm `import database.db as db` is already at the top of `points_logic.py` — it is.

- [ ] **Step 4: D1 — Use `get_channel` before falling back to `fetch_channel`**

In `helpers.py` `load_feedback_cog`, find:
```python
thread = await self.bot.fetch_channel(thread_id)
```
Replace with:
```python
thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
```

Apply the same fix anywhere else in `helpers.py` that calls `fetch_channel` on a thread ID.

Also apply to `feedback_threads.py:51` and `cogs/slash_commands/threads.py:37` while you're at it.

- [ ] **Step 5: Commit**

```bash
git add cogs/feedback_threads/modules/helpers.py cogs/feedback_threads/modules/points_logic.py cogs/feedback_threads/feedback_threads.py cogs/slash_commands/threads.py
git commit -m "fix: @staticmethod on helpers; remove async from shorten_message; inline wrapper methods; get_channel before fetch_channel"
```

---

## Task 12: Fix `feedback_monitor.py` — unbounded dict growth and double send (A3, D2)

**Files:**
- Modify: `ml_model/feedback_monitor.py`

- [ ] **Step 1: A3 — Delete validated entries from `pending_validations`**

Find `_handle_validation` (or the equivalent reaction handler). After the code sets `validation_data['validated'] = True` and finishes processing, add:

```python
del self.pending_validations[mod_message_id]
```

Where `mod_message_id` is the key used to look up the entry.

- [ ] **Step 2: D2 — Combine two `dev_spam.send` calls into one**

Find:
```python
await dev_spam.send(f"<@{412733389196623879}> New feedback!")
mod_message = await dev_spam.send(embed=embed)
```

Replace with (using `CO_DEV_ID` from Task 9 if that task has already been completed, otherwise inline the constant):
```python
mod_message = await dev_spam.send(
    content=f"<@{CO_DEV_ID}> New feedback!",
    embed=embed,
    allowed_mentions=discord.AllowedMentions(users=True)
)
```

- [ ] **Step 3: Commit**

```bash
git add ml_model/feedback_monitor.py
git commit -m "fix: delete pending_validations entry after validation; combine two dev_spam sends into one"
```

---

## Task 13: Fix type annotations — `ctx` parameter in `general.py` (B1)

**Files:**
- Modify: `cogs/general.py`

- [ ] **Step 1: Fix all command callback annotations**

At the top of the file, `commands` is already imported via `from discord.ext import commands`.

Change:
```python
async def points(self, ctx: discord.Message, user: discord.Member = None):
async def top(self, ctx: discord.Member):
async def MFR_command(self, ctx: discord.Message):
async def MFs_command(self, ctx: discord.Message):
async def genres(self, ctx: discord.Message, band_name: str):
async def similar(self, ctx: discord.Message, band_name: str):
```

To:
```python
async def points(self, ctx: commands.Context, user: discord.Member = None):
async def top(self, ctx: commands.Context):
async def MFR_command(self, ctx: commands.Context):
async def MFs_command(self, ctx: commands.Context):
async def genres(self, ctx: commands.Context, band_name: str):
async def similar(self, ctx: commands.Context, band_name: str):
```

- [ ] **Step 2: Commit**

```bash
git add cogs/general.py
git commit -m "fix: correct ctx type annotations to commands.Context in general.py"
```

---

## Task 14: Fix `finished_music_message.py` — duplicated message string (A11)

**Files:**
- Modify: `cogs/finished_music_message.py`

- [ ] **Step 1: Find the two identical `message_text` definitions in `send_finished_message` and `delete_and_repost_cycle`**

- [ ] **Step 2: Extract to a class constant**

Add near the top of the class body (before `__init__`):
```python
MESSAGE_TEXT = "**Deleted song?** ..."   # paste the exact string here
```

- [ ] **Step 3: Replace both local `message_text = "..."` assignments with `message_text = self.MESSAGE_TEXT`**

- [ ] **Step 4: Commit**

```bash
git add cogs/finished_music_message.py
git commit -m "refactor: extract duplicated finished-music message string to class constant"
```

---

## Task 15: Fix `member_class.py` — `get_random_message` returns first match not random (N2)

**Files:**
- Modify: `cogs/member_cards/member_class.py`

**Problem:** `random.choice` is called inside the `async for` loop body on the first day that has matching messages — it never collects across multiple days.

- [ ] **Step 1: Find the Strategy 2 block in `get_random_message`**

- [ ] **Step 2: Move the collection outside the loop and `random.choice` after it**

```python
all_candidates = []
async for day_group in channel.history(...):
    messages_by_member_on_day = [m for m in day_group if m.author == member]
    all_candidates.extend(messages_by_member_on_day)

if all_candidates:
    return random.choice(all_candidates)
```

- [ ] **Step 3: Commit**

```bash
git add cogs/member_cards/member_class.py
git commit -m "fix: collect all candidate messages before random.choice in get_random_message Strategy 2"
```

---

## Task 16: Fix `embeds.py` — remove unused parameters (N8)

**Files:**
- Modify: `cogs/feedback_threads/modules/embeds.py`
- Modify: callers in `points_logic.py`, `threads_manager.py`

- [ ] **Step 1: Audit each embed method for unused `thread` and `ctx` parameters**

Methods to check: `mfr`, `mfs`, `mod_add_points`, `mod_remove_points`, `mod_clear_points`, `MFS_to_MFR_embed`, `MFR_to_MFS_embed`, `MFR_to_MFS_with_no_points_embed`, `MFR_to_delete_embed`, `MFR_to_delete_embed_with_no_points`, `MFS_to_delete_embed`.

- [ ] **Step 2: For each unused parameter, remove it from the method signature**

Do not remove `ctx` from `mfr` and `mfs` — they use `ctx.author.id`, `ctx.author.display_name`, `ctx.author.display_avatar.url`, and `self.helpers.get_message_link(ctx)`.

Remove `thread=None` from any method that never references `thread` in its body.

- [ ] **Step 3: Update all call sites in `points_logic.py` and `threads_manager.py` to match the new signatures**

- [ ] **Step 4: Commit**

```bash
git add cogs/feedback_threads/modules/embeds.py cogs/feedback_threads/modules/points_logic.py cogs/feedback_threads/modules/threads_manager.py
git commit -m "refactor: remove unused thread/ctx parameters from embed builder methods"
```
