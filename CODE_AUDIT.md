# Code Audit — MF BOT

Issues found across four categories: code quality, type safety, async/threading logic, and Discord API efficiency. Ordered by severity within each section.

---

## A) Code Quality

### A1 — `helpers.py:51` — `load_feedback_cog` returns `None` implicitly on unmatched user

~~**Severity: Critical**~~
**✅ RESOLVED — `else: pass` replaced with `raise RuntimeError(...)` with a descriptive message.**

The `else: pass` branch returns nothing. Every caller unpacks the return value as four values, which will raise `TypeError: cannot unpack non-iterable NoneType object` if the user is not found in `user_thread`.

```python
# helpers.py
async def load_feedback_cog(self, ctx=None, user_id=None):
    ...
    if ctx.author.id in feedback_cog.user_thread:
        ...
        return thread, ticket_counter, points_logic, user_id
    else:
        pass  # ← implicit None return

# callers in general.py
thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)  # crashes if None
```

**Fix:** Replace `else: pass` with an explicit error response and early return (e.g. raise, return a sentinel tuple, or send an error message to the user).

---

### A2 — `user_listener.py:68` — `asyncio.sleep(86400)` inside `on_message` leaks coroutines

~~**Severity: Critical**~~
**✅ RESOLVED — the `elif INTRO_MUSIC` block was removed. Leftover `INTRO_MUSIC` import also cleaned up.**

Every message sent to the `INTRO_MUSIC` channel creates a coroutine that stays alive for 24 hours. With any volume of messages this accumulates indefinitely, leaking memory and coroutine handles. `scan_delete_intro_messages.py` already handles this correctly with a task loop — this code is fully redundant and should be removed.

```python
# user_listener.py
elif ctx.channel.id == INTRO_MUSIC and not ctx.author.guild_permissions.administrator:
    try:
        await asyncio.sleep(60*60*24)  # ← holds this coroutine open for 24 hours per message
        await ctx.delete()
    except Exception as e:
        print(str(e))
```

**Fix:** Remove this entire `elif` block. `scan_delete_intro_messages.py` already handles intro channel cleanup with a proper hourly task loop.

---

### A3 — `feedback_monitor.py` — `pending_validations` dict grows unboundedly

~~**Severity: Medium**~~
**✅ RESOLVED — `self.pending_validations.pop(mod_message.id, None)` called after validation completes.**

After a prediction is validated, the entry is marked `'validated': True` but is never removed from the dict. Over a long-running session this grows indefinitely.

```python
# feedback_monitor.py
self.pending_validations[mod_message.id] = {
    'original_message': message,
    ...
    'validated': False,
}

# In _handle_validation:
validation_data['validated'] = True  # ← marked done, but never del'd from the dict
```

**Fix:** After setting `validated = True` and finishing the handler, delete the entry: `del self.pending_validations[mod_message.id]`.

---

### A4 — Three files — Hardcoded user ID `412733389196623879` instead of `CO_DEV_ID`

~~**Severity: Medium**~~
**✅ RESOLVED — all three files (`feedback_monitor.py`, `export_json.py`, `mod_bad_feedback_notification.py`) import and use `CO_DEV_ID`.**

The same user ID is hardcoded in three separate files instead of using the `CO_DEV_ID` constant from `data/constants.py`.

```python
# feedback_monitor.py:207
await dev_spam.send(f"<@{412733389196623879}> New feedback!")

# export_json.py:41
await mod_channel.send(f"<@{412733389196623879}> New Export!")

# mod_bad_feedback_notification.py:12
self.moderator_user_id = 412733389196623879
```

**Fix:** Replace all three with `from data.constants import CO_DEV_ID` and use `CO_DEV_ID`.

---

### A5 — `mod_bad_feedback_notification.py:75` — Hardcoded channel ID in user-facing message

~~**Severity: Medium**~~
**✅ RESOLVED — `FEEDBACK_ACCESS_CHANNEL_ID` imported from `data/constants.py` and used in place of the hardcoded ID.**

The channel ID `959150439692128277` is hardcoded inline in the string sent to users. If the channel changes, this silently becomes a dead link. `FEEDBACK_ACCESS_CHANNEL_ID` in `data/constants.py` already holds this value.

```python
# mod_bad_feedback_notification.py
await audio_feedback_channel.send(
    f"{message.author.mention} Please provide more detailed and constructive feedback. "
    f"Check out <#959150439692128277> if you need help."  # ← hardcoded
)
```

**Fix:** `from data.constants import FEEDBACK_ACCESS_CHANNEL_ID` and use `<#{FEEDBACK_ACCESS_CHANNEL_ID}>`.

---

### A6 — `user_listener.py:108` — Double audit log query in `on_member_remove`

~~**Severity: Medium**~~
**✅ RESOLVED — inner loop removed; `audit_log_entry = entry` assigned directly in the outer `if` block; entire audit log fetch wrapped in `try/except discord.Forbidden`.**

The inner `async for` re-queries the same audit log entry already fetched by the outer loop. This makes 2 API calls when only 1 is needed, and the inner loop's result simply overwrites the outer `entry` that already passed the condition check.

```python
# user_listener.py
async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
    if entry.target == member and entry.created_at >= cutoff_time:
        try:
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):  # ← identical query
                audit_log_entry = entry
                break
```

**Fix:** Remove the inner loop entirely and assign `audit_log_entry = entry` directly inside the outer loop's `if` block.

---

### A7 — `spotify_promotion_checker.py:67` — Wrong `None` check on list return value

~~**Severity: Medium**~~
**✅ RESOLVED — `if urls is None` → `if not urls`. (Also noted in C4 resolution.)**

`extract_spotify_urls` always returns a list (empty if no URLs found), never `None`. The guard `if urls is None` is always `False`, so an empty list is never caught, and the subsequent `for url in urls` loop is just a no-op. A URL from a non-matching pattern would fall through silently.

```python
# spotify_promotion_checker.py
urls = extract_spotify_urls(content)
if urls is None:   # ← always False; extract_spotify_urls returns [], not None
    return False
```

**Fix:** Change to `if not urls:`.

---

### A8 — `guild_events.py:48` — `fetch_user` called on every `submit` command

~~**Severity: Medium**~~
**✅ RESOLVED — `self.pfp_url = ""` in `__init__`, fetched lazily and cached on first use.**

Every event submission triggers `await self.bot.fetch_user(self.bot.owner_id)` to get the pfp URL. All other cogs cache `self.pfp_url` and only fetch once. This cog does not.

```python
# guild_events.py — inside the submit command handler, runs on every call
creator_user = await self.bot.fetch_user(self.bot.owner_id)
pfp_url = creator_user.avatar.url
```

**Fix:** Store as an instance variable (`self.pfp_url = ""`), check if empty before fetching — matching the pattern used in `General`, `User_listener`, and `PointsLogic`.

---

### A9 — `helpers.py:126` — `shorten_message` is `async` with no async work
~~**Severity: Low**~~
**✅ RESOLVED — `async` keyword removed from `shorten_message`.**

The method does purely synchronous string manipulation. Marking it `async` forces every caller to unnecessarily `await` it.

```python
async def shorten_message(self, content: str, max_length: int):
    if len(content) > max_length:
        return content[:max_length - 3] + "..."
    return content
```

**Fix:** Remove `async`.

---

### A10 — `helpers.py:114–123` — Pointless single-line wrapper methods
~~**Severity: Low**~~
**✅ RESOLVED — both wrapper methods removed; callers now call `db.add_points`/`db.reduce_points` directly.**

`add_points_for_edits` and `remove_points_for_edits` are each a single `await db.*` call with no added logic. They add indirection with no benefit.

```python
async def add_points_for_edits(self, user_id: int, points_to_add: int):
    await db.add_points(user_id, points_to_add)
    return

async def remove_points_for_edits(self, user_id: int, points_to_remove: int):
    await db.reduce_points(user_id, points_to_remove)
    return
```

**Fix:** Remove both methods and have callers call `db.add_points` / `db.reduce_points` directly.

---

### A11 — `finished_music_message.py:34,58` — Duplicated hardcoded message string
~~**Severity: Low**~~
**✅ RESOLVED — `MESSAGE_TEXT` defined once as a class constant; both methods reference it.**

`message_text` is defined identically in both `send_finished_message` and `delete_and_repost_cycle`. If the text needs updating, one copy is easily missed.

**Fix:** Define it once as a class constant: `MESSAGE_TEXT = "**Deleted song?** ..."` and reference `self.MESSAGE_TEXT` in both methods.

---

### A12 — `bot.py` — Several minor issues
~~**Severity: Low**~~
**✅ RESOLVED — unused `general_chat` variable removed; `IS_READY` changed to bool; `global bot` removed from `on_ready`; hardcoded guild ID replaced with `SERVER_ID`.**

- `general_chat = bot.get_channel(FEEDBACK_CHANNEL_ID)` on line 76 is fetched but never used.
- `IS_READY = 0` / `IS_READY += 1` should be `IS_READY = False` / `IS_READY = True` — it's a flag, not a counter.
- `global bot` inside `on_ready` and `main` is unnecessary — `bot` is never reassigned in either function.
- The hardcoded guild ID `732355624259813531` in the `/sync` command should use `discord.Object(id=SERVER_ID)`.

---

### A13 — `user_listener.py:1–2` — Unused imports

~~**Severity: Low**~~
**✅ RESOLVED — `from re import T` and `from tarfile import NUL` removed.**

```python
from re import T
from tarfile import NUL
```

Neither `T` nor `NUL` are used anywhere in the file.

---

## B) Type Safety

### B1 — `cogs/general.py` — `ctx` annotated as wrong types throughout
~~**Severity: Medium**~~
**✅ RESOLVED — all command callbacks now use `ctx: commands.Context`.**

Command callbacks receive a `commands.Context` object, not `discord.Message` or `discord.Member`. These annotations are consistently wrong across the entire cog and are misleading to anyone reading the code.

```python
async def points(self, ctx: discord.Message, user: discord.Member = None):  # wrong
async def top(self, ctx: discord.Member):                                    # wrong
async def MFR_command(self, ctx: discord.Message):                           # wrong
async def MFs_command(self, ctx: discord.Message):                           # wrong
async def genres(self, ctx: discord.Message, band_name: str):                # wrong
async def similar(self, ctx: discord.Message, band_name: str):               # wrong
```

**Fix:** Change all to `ctx: commands.Context`.

---

### B2 — `helpers.py:72,91,104` — Instance methods missing `self`, should be `@staticmethod`
~~**Severity: Medium**~~
**✅ RESOLVED — `@staticmethod` added to all three methods.**

Three methods in `DiscordHelpers` define `bot` as their first parameter instead of `self`. They are called as class-level methods (`DiscordHelpers.get_thread_id_no_ctx(self.bot, ...)`), which happens to work. But if ever called on an instance, `self` (the `DiscordHelpers` instance) would bind to `bot`, and `user_id` would receive the bot — silently passing wrong values with no error.

```python
# helpers.py — these are defined inside the DiscordHelpers class
async def get_thread_id_no_ctx(bot, user_id: int):          # ← no self
async def delete_user_from_user_thread(bot, user_id: int):  # ← no self
async def delete_user_from_db(bot, user_id: int):           # ← no self
```

**Fix:** Add `@staticmethod` decorator to all three.

---

### B3 — `database/db.py` — `user_id` key type is inconsistently `int` vs `str` in `users_dict`
~~**Severity: Medium**~~
**✅ RESOLVED — every public db function now normalizes `user_id = str(user_id)` at entry, guaranteeing consistent str keys in `users_dict` regardless of what callers pass.**

`users_dict` can end up with both `int` and `str` keys for different users depending on which code path added them. A lookup with `int(user_id)` will miss an entry stored under `str(user_id)` and vice versa, causing silent cache misses and unnecessary DB queries.

- `on_member_join` calls `db.add_user(str(member.id))` → str key
- `fetch_points(user_id: str)` annotates str, stores `users_dict[user_id]` with whatever was passed
- `add_points(user_id, ...)` has no type annotation; callers pass both int and str

**Fix:** Standardize `user_id` as `int` throughout `db.py` (matching Discord's native type), convert to `str` only at the SQL query boundary: `(str(user_id),)`.

---

### B4 — `user_listener.py:26` — `on_message` parameter named `ctx` instead of `message`

~~**Severity: Low**~~
**✅ RESOLVED — parameter renamed to `message: discord.Message` throughout `on_message`.**

`on_message` always receives a `discord.Message`. Naming the parameter `ctx` implies a `commands.Context` and causes confusion throughout the method body.

```python
async def on_message(self, ctx):   # ← should be message: discord.Message
    ...
    content = ctx.content          # used as a message, not a context
    await ctx.delete()
```

**Fix:** Rename to `message: discord.Message` throughout.

---

### B5 — Widespread missing return type annotations

~~**Severity: Low**~~ **✅ RESOLVED**

Return type annotations added to all public-facing methods in `db.py`, `helpers.py`, `threads_manager.py`, `points_logic.py`, `member_class.py`, `feedback_threads.py`, and `ml_model_loader.py`.

Almost no functions across the codebase carry return type annotations. Key examples where the return type is non-obvious:

- `db.fetch_points` → `int` (but can it return `None` on error?)
- `helpers.load_feedback_cog` → `tuple[Thread, int, PointsLogic, str] | None`
- `ml_model_loader.predict` → `dict[str, Any]`
- `threads_manager.check_if_feedback_thread` → `tuple[Thread, int]`

**Fix:** Add return type hints progressively, starting with public-facing methods and database functions.

---

## C) Async / Threading Logic

### C1 — `database/db.py:96–104` — `cursor.fetchone()` called outside its `async with` block

~~**Severity: Critical**~~
**✅ RESOLVED — SQLite migration (commit 1893045)**

`fetch_rank_from_db` now uses `async with db_connection.execute(...) as cursor:` and calls `await cursor.fetchone()` inside that block. The aiomysql pool and its cursor context manager are gone.

---

### C2 — `database/db.py` — Missing `await` on all recursive reconnect retries

~~**Severity: Critical**~~
**✅ RESOLVED — SQLite migration (commit 1893045)**

The MySQL "lost connection" retry pattern (eight functions) is gone. The SQLite implementation has no reconnect retry logic — `aiosqlite` manages the single persistent connection directly.

---

### C3 — `youtube_promotion_checker.py:74` — `yt_dlp.extract_info()` blocks the event loop

~~**Severity: Critical**~~
**✅ RESOLVED — wrapped in `asyncio.to_thread()`. Also fixed `author.global_name` None crash (P1) in both `handle_videos` and `handle_channels`.**

`yt_dlp.YoutubeDL.extract_info()` is a synchronous blocking network call that can take 2–5+ seconds. It is called from inside the `on_message` async listener, freezing the bot's entire event loop for every YouTube link posted in the music channels.

```python
async def handle_videos(message):
    ...
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={youtube_video_id}', download=False)
        # ← synchronous — blocks the event loop
```

**Fix:** Use `asyncio.to_thread()` (Python 3.9+, cleanest) or `run_in_executor`. Prefer `asyncio.get_running_loop()` over `asyncio.get_event_loop()` — the latter is only deprecated when called with _no_ running event loop (Python 3.10+), but `get_running_loop()` is the explicit, correct call inside a coroutine and raises `RuntimeError` clearly if somehow called outside one.

```python
# Preferred (Python 3.9+, available on your 3.11):
info = await asyncio.to_thread(ydl.extract_info, f'https://www.youtube.com/watch?v={youtube_video_id}', download=False)

# Alternative:
loop = asyncio.get_running_loop()
info = await loop.run_in_executor(None, lambda: ydl.extract_info(..., download=False))
```

---

### C4 — `spotify_promotion_checker.py:41–45` — Spotipy API calls block the event loop

~~**Severity: Critical**~~
**✅ RESOLVED — `fetch_artist_name` wrapped in `asyncio.to_thread()`. Also fixed `author.global_name` None crash (P1) and `if urls is None` → `if not urls` (A7).**

`sp.track()`, `sp.album()`, and `sp.artist()` are synchronous blocking HTTP calls made from inside an async function called by the `on_message` listener.

```python
async def check_spotify(message):
    ...
    spotify_artists_names = fetch_artist_name(url)  # calls sp.track() synchronously inside

def fetch_artist_name(spotify_url):
    link_info = sp.track(link_id)   # ← blocking HTTP call on the event loop
```

**Fix:** Use `asyncio.to_thread()` (Python 3.9+, available on your 3.11) or `run_in_executor`. Prefer `asyncio.get_running_loop()` over `asyncio.get_event_loop()` inside coroutines for clarity.

```python
# Preferred:
spotify_artists_names = await asyncio.to_thread(fetch_artist_name, url)

# Alternative:
loop = asyncio.get_running_loop()
spotify_artists_names = await loop.run_in_executor(None, fetch_artist_name, url)
```

---

### C5 — `watchdog.py:17–21` — CPU busy-wait with no sleep

~~**Severity: High**~~
**✅ RESOLVED — `time.sleep(1)` added to inner loop (commit cab896c)**

---

### C6 — `watchdog.py` — Function name shadowed by local variable

~~**Severity: High**~~
**✅ RESOLVED — local variable renamed to `bot_proc` (commit cab896c)**

---

### C7 — `ml_model_loader.py:162` — sklearn/numpy prediction blocks the event loop

~~**Severity: High**~~
**✅ RESOLVED — `predict_feedback_quality` now wraps all sklearn/numpy work in `asyncio.to_thread()`, including the first-call model load.**

`predict_feedback_quality` is marked `async` but calls fully synchronous CPU-bound sklearn/numpy operations without an executor. Every `<MFR` message in the audio feedback channel will block the event loop during matrix multiplication and model inference.

```python
async def predict_feedback_quality(feedback_text):
    predictor = get_predictor()
    return predictor.predict(feedback_text)  # ← numpy + sklearn, fully synchronous CPU work
```

**Fix:** Use `asyncio.to_thread()` (available on your Python 3.11) or `run_in_executor`. Prefer `asyncio.get_running_loop()` over `asyncio.get_event_loop()` inside coroutines for explicitness.

```python
# Preferred:
async def predict_feedback_quality(feedback_text):
    predictor = get_predictor()
    return await asyncio.to_thread(predictor.predict, feedback_text)

# Alternative:
async def predict_feedback_quality(feedback_text):
    predictor = get_predictor()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, predictor.predict, feedback_text)
```

---

### C8 — `google_sheet.py` — All gspread operations block the event loop

~~**Severity: High**~~
**✅ RESOLVED — `get_all_values` in `google_sheet.py` wrapped in `asyncio.to_thread()`. All `self.google_sheet.*` calls in `rank_commands.py` (`current_rank`, `add_role`, `remove_role`, `history`) wrapped in `asyncio.to_thread()`.**

Every Google Sheets API call — `col_values()`, `find()`, `append_row()`, `update_cell()`, `row_values()`, `get_all_values()` — is synchronous HTTP I/O. These are called directly from slash command handlers (`rank_commands.py`), freezing the bot during each Sheets API round-trip.

```python
# google_sheet.py — all synchronous, called from async rank command handlers
def add_user_spreadsheet(self, user_id, username):
    first_column = self.sheet.col_values(1)      # ← blocking HTTP
    self.sheet.append_row([str(user_id), ...])   # ← blocking HTTP

def update_rank_spreadsheet(self, user_id, role, is_rankup):
    cell_row = self.sheet.find(str(user_id))     # ← blocking HTTP
    self.sheet.update_cell(...)                  # ← blocking HTTP
```

**Fix:** The cleanest option is `asyncio.to_thread()` wrapping each call-site (available on your Python 3.11). Alternatively, `gspread-asyncio` provides a proper async interface but adds a dependency. Prefer `asyncio.get_running_loop()` over `asyncio.get_event_loop()` if you go the `run_in_executor` route — the latter is only deprecated when called with no running loop, but `get_running_loop()` is more explicit.

```python
# Preferred per-call fix (Python 3.9+):
await asyncio.to_thread(self.sheet.append_row, [str(user_id), ...])
```

---

### C9 — `export_json.py:12–18` — Synchronous file I/O on the event loop

~~**Severity: Low**~~ **✅ RESOLVED** _(downgraded — see note)_

`_write_json` and `_read_json` are now called via `asyncio.to_thread()` in both `export_to_json` and `count_entries`.

`export_to_json` and `count_entries` both use synchronous `open()` / `json.dump()` / `json.load()` directly on the event loop thread.

```python
def export_to_json(self, data, filename="feedback_json.json"):
    with open(filename, 'w') as json_file:   # ← blocking disk I/O
        json.dump(data, json_file, indent=4)
```

**Note:** For the small feedback JSON file this operates on (triggered infrequently, file < 1 MB), the blocking duration is typically under 1ms — well within what the event loop tolerates before a heartbeat miss. This is a real pattern issue but the practical impact here is negligible. It would matter if the file were large or this were called in a high-frequency hot path.

**Fix if needed:** Wrap in `asyncio.to_thread()` (Python 3.9+) or use the `aiofiles` library.

```python
await asyncio.to_thread(json.dump, data, json_file, indent=4)
```

---

## D) Discord API Efficiency

### D1 — `helpers.py:50` — `fetch_channel` instead of `get_channel` on every feedback command

~~**Severity: Medium**~~
**✅ RESOLVED — all locations (`helpers.py`, `feedback_threads.py`, `threads_manager.py`) use `get_channel(id) or await fetch_channel(id)`.**

`bot.fetch_channel()` makes an HTTP API call every time. `bot.get_channel()` reads from the in-memory cache and is instant. Every `<MFR` and `<MFS` command hits this code path to look up the user's private feedback thread.

```python
# helpers.py
thread = await self.bot.fetch_channel(thread_id)  # ← HTTP call every time
```

Same issue exists in `feedback_threads.py:51` and `threads.py:37`.

**Fix:**

```python
thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
```

---

### D2 — `feedback_monitor.py:207` — Two separate sends where one would work
~~**Severity: Low**~~
**✅ RESOLVED — combined into a single `dev_spam.send(content=..., embed=..., allowed_mentions=...)` call.**

For every `<MFR` message, two API calls are made to `DEV_SPAM` in immediate succession where one call would cover both.

```python
await dev_spam.send(f"<@{412733389196623879}> New feedback!")  # call 1 — just a mention
mod_message = await dev_spam.send(embed=embed)                 # call 2 — the actual content
```

**Fix:** Combine into one send:

```python
mod_message = await dev_spam.send(
    content=f"<@{CO_DEV_ID}> New feedback!",
    embed=embed,
    allowed_mentions=discord.AllowedMentions(users=True)
)
```

---

### D3 — `bot.py:71` — Global `bot.tree.sync()` called on every restart

~~**Severity: Low**~~
**✅ RESOLVED — `on_ready` now calls `await bot.tree.sync(guild=discord.Object(id=SERVER_ID))`. Also fixed `sync` slash command to use `SERVER_ID` int constant instead of `server_id` string (P5/A12).**

`await bot.tree.sync()` with no guild argument performs a global command sync that propagates to every server. Discord caches global commands for up to 1 hour. Calling this on every restart is slow, unnecessary when commands haven't changed, and can approach rate limits on frequent restarts.

**Fix:** For development, use guild-specific sync only: `await bot.tree.sync(guild=discord.Object(id=SERVER_ID))`. For production, sync globally only when command signatures actually change (not on every startup).

---

### D4 — `genres.py` / `similar_bands.py` — New `aiohttp.ClientSession` created per API call

~~**Severity: Low**~~
**✅ RESOLVED — both modules now have a module-level `_session` cache and `_get_session()` lazy initializer. All `ClientSession` usages reuse the persistent session.**

Creating and tearing down a `ClientSession` on every `<MFgenres` and `<MFsimilar` command adds overhead. The `aiohttp` docs explicitly recommend reusing a single session.

```python
# genres.py — called every time the command is used
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        ...
```

**Fix:** These are module-level functions, not cog methods, so there is no `__init__`. `aiohttp.ClientSession` also cannot be created at module import time (no running event loop). The correct approach: create a session in the calling cog's `async def cog_load(self)`, and pass it as a parameter to `fetch_band_genres(session, band_name)`. The cog closes it in `cog_unload`:

```python
# In the calling cog:
async def cog_load(self):
    self.session = aiohttp.ClientSession()

def cog_unload(self):
    asyncio.create_task(self.session.close())

# genres.py signature becomes:
async def fetch_band_genres(session: aiohttp.ClientSession, band_name: str): ...
```

---

### D5 — `mod_bad_feedback_notification.py:63` — `wait_for` (5-minute timeout) held inline in `on_message` chain

~~**Severity: Low**~~
**✅ RESOLVED — `notify_bad_feedback` now fires as a background `asyncio.create_task()` with a `_log_task_error` done-callback. `on_message` returns immediately.**

`notify_bad_feedback` is `await`-ed directly inside the `on_message` listener. This means the message processing chain for that particular message doesn't complete for up to 5 minutes while waiting for a moderator reaction. With multiple bad feedback messages arriving in quick succession, multiple 5-minute waits stack up in the same call chain.

```python
# feedback_monitor.py — called inline from on_message
await self.notifier.notify_bad_feedback(message, feedback_text, ...)

# mod_bad_feedback_notification.py — inside notify_bad_feedback
reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
```

**Fix:** Fire the notification as a background task so `on_message` returns immediately:

```python
asyncio.create_task(self.notifier.notify_bad_feedback(message, feedback_text, log_callback=self.log_to_bot_log))
```

---

## Full Issue Index

| ID  | File                                  | Description                                                                                    | Severity                                  |
| --- | ------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------- |
| C1  | `database/db.py:96`                   | `cursor.fetchone()` outside `async with` block — always returns None                           | ~~**Critical**~~ ✅ Resolved              |
| C2  | `database/db.py` (×8)                 | Missing `await` on recursive retry calls — retries silently do nothing                         | ~~**Critical**~~ ✅ Resolved              |
| C3  | `youtube_promotion_checker.py:74`     | `yt_dlp.extract_info()` blocks event loop                                                      | ~~**Critical**~~ ✅ Resolved              |
| C4  | `spotify_promotion_checker.py:41`     | Spotipy calls block event loop                                                                 | ~~**Critical**~~ ✅ Resolved              |
| A1  | `helpers.py:51`                       | `load_feedback_cog` implicit None return causes unpack crash                                   | ~~**Critical**~~ ✅ Resolved              |
| A2  | `user_listener.py:68`                 | `asyncio.sleep(86400)` in `on_message` — coroutine memory leak                                 | ~~**Critical**~~ ✅ Resolved              |
| C5  | `watchdog.py:17`                      | Inner loop has no sleep — 100% CPU busy-wait                                                   | ~~**High**~~ ✅ Resolved                  |
| C6  | `watchdog.py`                         | Function name `bot_process` shadowed by local variable                                         | ~~**High**~~ ✅ Resolved                  |
| C7  | `ml_model_loader.py:162`              | sklearn/numpy prediction blocks event loop                                                     | ~~**High**~~ ✅ Resolved                  |
| C8  | `google_sheet.py`                     | All gspread operations block event loop                                                        | ~~**High**~~ ✅ Resolved                  |
| A3  | `feedback_monitor.py`                 | `pending_validations` never cleared — unbounded memory growth                                  | ~~**Medium**~~ ✅ Resolved                |
| A4  | 3 files                               | Hardcoded `412733389196623879` instead of `CO_DEV_ID`                                          | ~~**Medium**~~ ✅ Resolved                |
| A5  | `mod_bad_feedback_notification.py:75` | Hardcoded channel ID instead of `FEEDBACK_ACCESS_CHANNEL_ID`                                   | ~~**Medium**~~ ✅ Resolved                |
| A6  | `user_listener.py:108`                | Double audit log query in `on_member_remove`                                                   | ~~**Medium**~~ ✅ Resolved                |
| A7  | `spotify_promotion_checker.py:67`     | `if urls is None` never true — empty list passes through                                       | ~~**Medium**~~ ✅ Resolved                |
| A8  | `guild_events.py:48`                  | `fetch_user` called on every `submit` — not cached                                             | ~~**Medium**~~ ✅ Resolved                |
| B1  | `general.py`                          | `ctx: discord.Message` / `ctx: discord.Member` wrong type hints                                | ~~**Medium**~~ ✅ Resolved                |
| B2  | `helpers.py:72,91,104`                | Instance methods using `bot` as first param, missing `@staticmethod`                           | ~~**Medium**~~ ✅ Resolved                |
| B3  | `database/db.py`                      | `user_id` key type mixed `int`/`str` in `users_dict`                                           | ~~**Medium**~~ ✅ Resolved                |
| C9  | `export_json.py:12`                   | Synchronous file I/O on event loop                                                             | ~~**Low**~~ ✅ Resolved                   |
| D1  | `helpers.py:50`                       | `fetch_channel` instead of `get_channel or fetch_channel`                                      | ~~**Medium**~~ ✅ Resolved                |
| B4  | `user_listener.py:26`                 | `on_message(self, ctx)` should be `(self, message: discord.Message)`                           | ~~**Low**~~ ✅ Resolved                   |
| B5  | Codebase-wide                         | Missing return type annotations on most functions                                              | ~~**Low**~~ ✅ Resolved                   |
| A9  | `helpers.py:126`                      | `shorten_message` is `async` with no async work                                                | ~~**Low**~~ ✅ Resolved                   |
| A10 | `helpers.py:114`                      | `add/remove_points_for_edits` are pointless single-line wrappers                               | ~~**Low**~~ ✅ Resolved                   |
| A11 | `finished_music_message.py`           | Same message string hardcoded in two places                                                    | ~~**Low**~~ ✅ Resolved                   |
| A12 | `bot.py`                              | Unused variable, `IS_READY` int flag, unnecessary `global bot`, hardcoded guild ID             | ~~**Low**~~ ✅ Resolved                   |
| A13 | `user_listener.py:1`                  | Unused imports `from re import T` and `from tarfile import NUL`                                | ~~**Low**~~ ✅ Resolved                   |
| D2  | `feedback_monitor.py:207`             | Two API sends where one would work                                                             | ~~**Low**~~ ✅ Resolved                   |
| D3  | `bot.py:71`                           | Global `tree.sync()` on every restart                                                          | ~~**Low**~~ ✅ Resolved                   |
| D4  | `genres.py` / `similar_bands.py`      | New `ClientSession` per API call                                                               | ~~**Low**~~ ✅ Resolved                   |
| D5  | `mod_bad_feedback_notification.py`    | 5-minute `wait_for` held inline instead of as background task                                  | ~~**Low**~~ ✅ Resolved                   |
| N11 | `database/db.py`                      | `add_user(called_from_update_func=True)` leaves `users_dict` empty — `KeyError` on first fetch | ~~**High**~~ ✅ Fixed                     |
| N12 | `exception_handler.py`                | Traceback printed on `CommandInvokeError` wrapper, not original exception                      | ~~**Medium**~~ ✅ Fixed                   |
| N13 | `bot.py`                              | `db.init_database()` failure silently swallowed in `on_ready`                                  | ~~**High**~~ ✅ Fixed                     |

---

# Second-Pass Audit

---

## Part 1 — Why Tasks Stop After a Few Days

`tasks.loop` instances die silently when errors go unhandled, when their underlying resources become stale, or when lifecycle hooks are wired incorrectly. The issues below are the most likely causes.

---

### T1 — `database/db.py` — MySQL connection pool has no `pool_recycle`

~~**Severity: Critical**~~
**✅ RESOLVED — SQLite migration (commit 1893045)**

MySQL and `aiomysql` are gone. The bot now uses a single persistent `aiosqlite` connection with WAL mode, which has no connection timeout issue.

---

### T2 — `finished_music_message.py` — Task loop has no `.error` handler and no `reconnect=True`

~~**Severity: Critical**~~
**✅ RESOLVED — `reconnect=True` added; `delete_and_repost_cycle_error` handler added.**

```python
# finished_music_message.py
@tasks.loop(hours=6)   # ← no reconnect=True, no .error handler
async def delete_and_repost_cycle(self):
    ...
```

Without `reconnect=True`, a `discord.errors.ConnectionClosed` or network blip kills the loop permanently. Without an `.error` handler, any other exception (e.g., a `Forbidden` or an API error) also kills it silently with no log.

**Fix:**

```python
@tasks.loop(hours=6, reconnect=True)
async def delete_and_repost_cycle(self):
    ...

@delete_and_repost_cycle.error
async def delete_and_repost_cycle_error(self, error):
    print(f"[FinishedMusicMessage] Task crashed: {error}")
    await asyncio.sleep(60)
    if not self.delete_and_repost_cycle.is_running():
        self.delete_and_repost_cycle.restart()
```

---

### T3 — `finished_music_message.py` — `stored_message_id` lost on restart

~~**Severity: High**~~
**✅ RESOLVED — ID persisted to `data/stored_message_id.json`; `before_loop` restores it via `fetch_message()` on startup.**

`stored_message_id` is an in-memory attribute. On restart it resets to `None`, so the task creates a new pinned message without deleting the previous one. Over multiple restarts the channel accumulates duplicate messages.

**Fix:** Persist `stored_message_id` to the database (or a simple JSON file) on write and load it back in `before_loop`.

---

### T4 — `scan_delete_intro_messages.py:73` — `self.channel` not set in `__init__`

~~**Severity: High**~~
**✅ RESOLVED — `self.channel = None` is present in `__init__`.**

`self.channel` is only assigned inside `before_printer` (the `before_loop` hook). If `before_printer` raises before the assignment (e.g., a Discord API error), the loop body's `if self.channel is None` check throws `AttributeError: 'MessageCleaner' object has no attribute 'channel'`, which crashes the task permanently.

```python
# scan_delete_intro_messages.py
def __init__(self, bot):
    self.bot = bot
    self.clean_old_messages.start()
    # ← self.channel never initialised here
```

**Fix:** Add `self.channel = None` in `__init__`.

---

### T5 — `music.py` — `NotesMenu` leaks a listener on every invocation

~~**Severity: High**~~
**✅ RESOLVED — listener registered in `send_initial_message` (not `__init__`); `stop()` and terminal state both call `remove_listener`.**

`NotesMenu.__init__` calls `self.bot.add_listener(self.on_raw_reaction_add)` but `on_raw_reaction_add` is never removed. Each `<MF notes` command call adds a new listener. After N invocations, N copies of `on_raw_reaction_add` fire for every reaction event.

```python
# music.py — NotesMenu.__init__
self.bot.add_listener(self.on_raw_reaction_add)
# ← no corresponding remove_listener anywhere
```

**Fix:** Call `self.bot.remove_listener(self.on_raw_reaction_add)` when the menu session ends or times out.

---

### T6 — `aotw_event.py` — `asyncio.create_task` exceptions are silently swallowed

~~**Severity: Medium**~~
**✅ RESOLVED — `_log_task_error` done-callback attached to all `create_task` calls.**

```python
# aotw_event.py
asyncio.create_task(self.check_aotw_channel_announcement())
```

If the task raises an exception, it is attached to the `Task` object but never retrieved, so Python logs a `Task exception was never retrieved` warning at garbage-collection time (not immediately). In a long-running bot this means failures are invisible until the bot restarts.

**Fix:** Attach a done-callback that logs the exception. Do not use a lambda — calling `.exception()` on a cancelled task raises `CancelledError`, which the lambda would not handle.

```python
def _log_task_error(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        print(f"[AOTW] Task error: {task.exception()}")

task = asyncio.create_task(self.check_aotw_channel_announcement())
task.add_done_callback(_log_task_error)
```

---

## Part 2 — Newly Found Bugs

---

### N1 — `rank_commands.py` — `update_rank_spreadsheet` receives a `Role` object instead of a role name

~~**Severity: Critical**~~
**✅ RESOLVED — call sites pass `role.name` / `new_role.name`.**

```python
# rank_commands.py
new_role = discord.utils.get(member.guild.roles, name=rank)
await update_rank_spreadsheet(user.id, new_role, ...)
#                                        ^^^^^^^^ discord.Role object, not a string
```

`update_rank_spreadsheet` expects a string (rank name) as its second argument and writes it directly to Google Sheets. Passing a `discord.Role` object writes its `str()` representation (e.g. `<Role id=123 name='Gold'>`) to the spreadsheet instead of just `"Gold"`.

**Fix:** Pass `new_role.name` instead of `new_role`.

---

### N2 — `member_class.py` — `get_random_message` Strategy 2 returns the first match, not a random one

~~**Severity: High**~~
**✅ RESOLVED — messages accumulated across all days into `all_recent_candidates`; `random.choice` called once after the loop.**

The `if messages_by_member_on_day:` check and the `random.choice` call are indented _inside_ the `async for` loop body. On the first iteration where messages are found, `random.choice` runs immediately and returns — it never collects messages across multiple days before choosing.

```python
# member_class.py — Strategy 2 (simplified)
async for day_group in channel.history(...):
    messages_by_member_on_day = [m for m in day_group if m.author == member]
    if messages_by_member_on_day:           # ← inside loop body
        return random.choice(messages_by_member_on_day)  # ← returns on first match
```

**Fix:** Collect all candidate messages across the entire loop, then call `random.choice` _after_ the loop exits.

---

### N3 — `aotw_event.py` — `check_aotw_channel_announcement()` called twice, second call missing argument

~~**Severity: High**~~
**✅ RESOLVED — no duplicate call exists; each invocation site passes the required argument.**

At line 387, `check_aotw_channel_announcement` is called twice in succession. The first call passes the required argument; the second call omits it, which will raise `TypeError` at runtime.

**Fix:** Remove the duplicate call.

---

### N4 — `admin.py:185` — Module-level `print` executes on every import

~~**Severity: Medium**~~
**✅ RESOLVED — line was already removed.**

```python
# admin.py — at module scope (not inside any function or class)
print("Processing complete")
```

This runs every time `admin.py` is imported, including on bot startup and whenever the cog is reloaded. It is likely debug code left behind accidentally.

**Fix:** Remove the line.

---

### N5 — `rank_commands.py` — Duplicate `rank_options` list and duplicate `datetime` import
~~**Severity: Low**~~
**✅ RESOLVED — duplicate `rank_options` list and redundant `import datetime` removed.**

---

### N6 — `music.py` — `fetch_user` and `open('options.json')` called on every command

~~**Severity: Medium**~~
**✅ RESOLVED — `_notes_data` cached via `async def cog_load(self)`. `_pfp_url` cached lazily (same pattern as other cogs).**

---

### N7 — `feedback_threads/modules/threads_manager.py` — Dead `setup()` function
~~**Severity: Low**~~
**✅ RESOLVED — dead `setup()` function removed.**

---

### N8 — `feedback_threads/modules/embeds.py` — Unused `thread` and `ctx` parameters
~~**Severity: Low**~~
**✅ RESOLVED — unused `thread`/`ctx` parameters removed from embed builder signatures and all call sites updated.**

---

### N9 — `member_class.py` — `get_message_count` is an unimplemented stub

~~**Severity: Medium**~~
**✅ RESOLVED — now raises `NotImplementedError("get_message_count is not implemented")` so callers fail loudly instead of silently receiving 0.**

```python
async def get_message_count(self, member):
    return 0   # ← not implemented
```

Any feature that depends on message counts silently receives 0 and behaves as if the member has no messages. There is no TODO comment or raised `NotImplementedError`.

**Fix:** Either implement the method or raise `NotImplementedError("get_message_count not yet implemented")` so callers fail loudly.

---

### N11 — `database/db.py` — `add_user(called_from_update_func=True)` leaves `users_dict` without point keys
~~**Severity: High**~~
**✅ RESOLVED — `users_dict[user_id]` populated with `{"Points": 0, "Warnings": 0, "Kicks": 0}` immediately after the `add_user` call in the else branch.**

When a user is not found in the DB, `update_dict_from_db` deletes their entry from `users_dict` and calls `add_user(user_id, called_from_update_func=True)`. Inside `add_user`, `users_dict[user_id] = {}` is set (empty dict) and the function returns without populating Points/Warnings/Kicks. Back in `fetch_points`, the next line is `return users_dict[user_id]["Points"]` — which raises `KeyError: 'Points'`.

```python
# db.py — update_dict_from_db
else:
    del users_dict[user_id]
    await add_user(user_id, called_from_update_func=True)
    # ← users_dict[user_id] is now {} with no keys

# db.py — fetch_points
await update_dict_from_db(user_id)
return users_dict[user_id]["Points"]   # ← KeyError if user was just created
```

**Fix:** After the `add_user` call in the else branch, populate the dict with defaults:

```python
await add_user(user_id, called_from_update_func=True)
users_dict[user_id] = {"Points": 0, "Warnings": 0, "Kicks": 0}
```

---

### N12 — `exception_handler.py` — Traceback printed on wrapper, not original exception

~~**Severity: Medium**~~
**✅ Fixed in this session**

`traceback.print_exception(type(error), error, error.__traceback__)` was printing the `CommandInvokeError` wrapper's traceback, hiding the actual file and line number of the underlying error. Fixed to use `orig = getattr(error, 'original', error)` and print `orig.__traceback__`.

---

### N13 — `bot.py` — `db.init_database()` has no error handling in `on_ready`

~~**Severity: High**~~
**✅ Fixed in this session**

`db.init_database()` was called bare in `on_ready`. If it raised an exception (e.g. bad path, missing dependency), discord.py silently swallowed it and the bot ran with a broken or missing database connection — all subsequent DB calls would either fail or behave unexpectedly with no visible error. Fixed with a try/except that prints the full traceback.

---

### N10 — `helpers.py:72,91,104` — Instance methods using `bot` as first param need `@staticmethod`
~~**Severity: Medium**~~ (also listed as B2 in the first pass — included here for completeness)
**✅ RESOLVED — see B2.**

`get_thread_id_no_ctx`, `delete_user_from_user_thread`, and `delete_user_from_db` all define `bot` as their first positional parameter but are not marked `@staticmethod`. The current call sites use class-method syntax (`DiscordHelpers.method(self.bot, ...)`) which works correctly — Python does not inject `self` here. However, without `@staticmethod` the intent is ambiguous, and if any call site ever calls these on an instance (`helpers_obj.method(...)`) Python will silently pass the instance as `bot`, causing `AttributeError`s at runtime with no clear error message.

**Fix:** Either rename the first parameter to `self` and add `self.bot` references, or decorate with `@staticmethod` and ensure callers pass `bot` explicitly.

---

## Part 3 — Modularisation Recommendations

---

### M1 — Centralise `pfp_url` fetching into a shared utility

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`get_owner_pfp_url()` added to `MFBot`; all 9 cogs updated.

---

### M2 — Wrap database access behind a `DatabaseService` class

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`Database` class in `database/db.py`; all callers use `bot.db.*`.

---

### M3 — Define a clean API for `feedback_threads`

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`record_feedback`, `record_spend`, `record_admin_adjustment` added to `FeedbackThreads`; all external callers updated.

---

### M4 — Extract rank hierarchy into `data/constants.py`

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`data/config.py` with `RANK_ORDER`, `LOWER_RANKS`, `AOTW_ROLE_NAME`, `FANS_ROLE_NAME`, `ROLES_TO_IGNORE`; `rank_commands.py` and `member_data.py` updated.

---

### M5 — Split `get_member_card.py` / `member_class.py`

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`member_data.py` (Discord data fetching) and `member_card_renderer.py` (Pillow rendering via `asyncio.to_thread`) created; `member_class.py` deleted.

---

### M6 — Split `feedback_monitor.py` into monitor + notifier

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`FeedbackNotifier.send_prediction_result` added; embed build + DEV_SPAM send delegated from `feedback_monitor.py`.

---

### M7 — Make `ConfigureChannel` a cog-level dependency, not re-instantiated per command

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`ConfigureChannel` instantiated once in `AOTWEvent.__init__`; 5 inline instantiations removed.

---

### M8 — Extract `log_to_bot_log` into a shared logging utility

~~**Not a bug — architectural recommendation.**~~ **✅ IMPLEMENTED**
`DiscordChannelHandler` in `utils/bot_logger.py`; `log_to_bot_log` removed from 3 cogs.

---

## Combined Issue Index (Second Pass)

| ID  | File                            | Description                                                                                   | Severity                                        |
| --- | ------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| T1  | `database/db.py`                | No `pool_recycle` — MySQL connections die after ~8h, killing all DB tasks                     | ~~**Critical**~~ ✅ Resolved (SQLite migration) |
| T2  | `finished_music_message.py`     | No `.error` handler, no `reconnect=True` — any exception kills the task forever               | ~~**Critical**~~ ✅ Resolved                    |
| T3  | `finished_music_message.py`     | `stored_message_id` lost on restart — old messages orphaned                                   | ~~**High**~~ ✅ Resolved                        |
| T4  | `scan_delete_intro_messages.py` | `self.channel` not initialised in `__init__` — `AttributeError` kills task                    | ~~**High**~~ ✅ Resolved                        |
| T5  | `music.py`                      | `NotesMenu` adds listener in `__init__` with no `remove_listener` — leak grows per invocation | ~~**High**~~ ✅ Resolved                        |
| T6  | `aotw_event.py`                 | `create_task` exceptions silently lost — task failures invisible                              | ~~**Medium**~~ ✅ Resolved                      |
| N1  | `rank_commands.py`              | `update_rank_spreadsheet` receives `Role` object instead of role name string                  | ~~**Critical**~~ ✅ Resolved                    |
| N2  | `member_class.py`               | Strategy 2 returns first day's message, not a random one across all days                      | ~~**High**~~ ✅ Resolved                        |
| N3  | `aotw_event.py`                 | `check_aotw_channel_announcement()` called twice; second call missing argument                | ~~**High**~~ ✅ Resolved                        |
| N4  | `admin.py:185`                  | Module-level `print("Processing complete")` runs on every import                              | ~~**Medium**~~ ✅ Resolved                      |
| N5  | `rank_commands.py`              | Duplicate `rank_options` list and duplicate `datetime` import                                 | ~~**Low**~~ ✅ Resolved                         |
| N6  | `music.py`                      | `fetch_user` and `open('options.json')` called on every command                               | ~~**Medium**~~ ✅ Resolved                      |
| N7  | `threads_manager.py`            | Dead `setup()` function registers a non-Cog as a Cog                                          | ~~**Low**~~ ✅ Resolved                         |
| N8  | `embeds.py`                     | Unused `thread` / `ctx` params across multiple embed methods                                  | ~~**Low**~~ ✅ Resolved                         |
| N9  | `member_class.py`               | `get_message_count` is an unimplemented stub returning 0                                      | ~~**Medium**~~ ✅ Resolved                      |
| N10 | `helpers.py:72,91,104`          | `bot` as first param on instance methods — `self` passed as `bot` at runtime                  | ~~**Medium**~~ ✅ Resolved                      |

---

# Third-Pass — Discord.py & Python Etiquette Review

Findings from cross-referencing the codebase against official discord.py documentation, the discord.py Masterclass, and the discord.py FAQ. Covers cog lifecycle correctness, error handling gaps, Python-level etiquette issues, underused API features, and missing features.

---

## E1 — Cog Lifecycle: Initialization logic in `on_ready` is fragile

~~**Severity: High**~~ **✅ RESOLVED** | `bot.py:47–61`

`db.init_database()` moved to `main()` before `bot.start()`. `FeedbackThreads.cog_load()` added to load SQLite data exactly once at cog load time. `threads_manager.on_ready()` remains in `on_ready` as it needs `bot.wait_until_ready()` (channel cache requires a live connection).

`on_ready` fires on every reconnect, not just once. The `IS_READY` int guard is a workaround. Logic like `feedback_cog.initialize_sqldb()` and `threads_manager.on_ready()` belongs in `async def cog_load(self)` inside their respective cogs — it fires exactly once when the cog loads.

**Important nuance:** `cog_load` (both `def` and `async def` work — `discord.utils.maybe_coroutine` handles both) fires when `bot.load_extension()` runs, which is inside `main()` _before_ `bot.start()`. The bot is not yet connected and the channel cache is empty. This means `bot.get_channel()` in `cog_load` always returns `None`. Use `cog_load` for non-Discord setup only (database init, creating helper objects, registering exception types on task loops). Channel fetching must remain in `before_loop` where `await self.bot.wait_until_ready()` can be called.

---

## E2 — Error Handling: Slash command global error handler is critically minimal

~~**Severity: High**~~ **✅ RESOLVED** | `bot.py:115–117`

Handler now classifies `CommandOnCooldown`, `MissingPermissions`, and `CheckFailure` into user-friendly messages, logs unknown errors to stdout, and uses `interaction.response` / `interaction.followup` correctly with a try/except guard.

```python
@bot.tree.error
async def on_app_command_error(interaction, error):
    await interaction.channel.send(str(error))
```

Three problems:

1. `interaction.channel` can be `None` (DMs, expired interactions) — this handler can crash itself
2. `str(error)` sends raw Python exception text to users — exposes internals
3. No `interaction.response.is_done()` check — if the interaction was deferred, `interaction.channel.send` sends to the channel instead of as a followup

The correct pattern:

```python
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        msg = f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
    elif isinstance(error, app_commands.MissingPermissions):
        msg = "You don't have permission to use this command."
    elif isinstance(error, app_commands.CheckFailure):
        msg = "You don't meet the requirements for this command."
    else:
        msg = "An unexpected error occurred."
        # log the real error here

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
```

Additionally, `exception_handler.py` only handles prefix command (`on_command_error`) errors. Slash commands have zero equivalent protection.

---

## E3 — Error Handling: No `cog_command_error` in any cog
~~**Severity: Medium**~~ **✅ RESOLVED** | `cogs/general.py`

`cog_command_error` added to the `General` cog handling `CommandOnCooldown`, `CheckFailure`, `MissingRequiredArgument`, and re-raising anything else to the global handler.

`cog_command_error(self, ctx, error)` is a cog-level handler that catches errors before they reach the global handler. It allows cog-specific error messaging (e.g. the feedback cogs could respond with feedback-specific guidance) without polluting the global handler with every special case.

Per the discord.py source: this method **must be `async def`** — the docstring explicitly states "This **must** be a coroutine."

---

## E4 — Permissions: Manual `if` check should be replaced with a decorator, but keep `default_permissions`

~~**Severity: Medium**~~ **✅ RESOLVED** | `admin.py:25–28`

`@app_commands.checks.has_permissions(administrator=True)` added to `add`, `remove`, and `clear`. Manual `if not interaction.user.guild_permissions.administrator:` blocks removed from all three. `default_permissions` on the group retained.

```python
group = app_commands.Group(..., default_permissions=discord.Permissions(administrator=True))

async def add(self, interaction, ...):
    if not interaction.user.guild_permissions.administrator:  # ← should be a decorator
        ...
```

`default_permissions` and `@app_commands.checks.has_permissions()` serve _different_ purposes and should coexist:

- `default_permissions` is a Discord-side hint that controls the default UI visibility. Server admins can override it in Server Settings → Integrations, so it is **not** a security enforcement mechanism.
- `@app_commands.checks.has_permissions(administrator=True)` is a hard runtime check enforced by the bot that raises `MissingPermissions` regardless of any server setting override.

**Fix:** Keep `default_permissions` on the group (correct intent), but replace the manual `if` block with the decorator:

```python
@group.command(name='add', ...)
@app_commands.checks.has_permissions(administrator=True)
async def add(self, interaction, user: discord.Member, points: int = 1):
    await interaction.response.defer(ephemeral=True)
    ...  # no manual permission check needed
```

---

## E5 — Permissions: No `@app_commands.guild_only()` on guild-only commands

~~**Severity: High**~~ **✅ RESOLVED** | `admin.py`, `rank_commands.py`

`guild_only=True` added to the `app_commands.Group(...)` constructor in both files.

If someone invokes an admin or rank slash command in a DM, `interaction.user.guild_permissions` raises `AttributeError`. `@app_commands.guild_only()` prevents the command from appearing in DM contexts.

**Two critical notes verified from discord.py 2.6.4 source:**

1. `guild_only` is **verified server-side by Discord**, not as a `check`. The docstring states: _"there is no error handler called when a command is used within a private message."_ This means your global `@bot.tree.error` handler will NOT fire for guild-only violations — Discord simply won't surface the command in DMs.

2. **"Due to a Discord limitation, this decorator does nothing in subcommands and is ignored."** Both `admin.py` and `rank_commands.py` use `app_commands.Group` with subcommands (`@group.command()`). Applying `@app_commands.guild_only()` to individual subcommands is silently ignored. It must be applied to the **group class or object itself**:

```python
# Correct — apply to the group:
group = app_commands.Group(name="mfpoints", description="...", guild_only=True)

# Or via decorator on a GroupCog subclass:
@app_commands.guild_only()
class Admin(commands.GroupCog): ...
```

---

## E6 — `tree.sync()` called globally on every boot

~~**Severity: Medium**~~ **✅ RESOLVED (see D3)** | `bot.py:71`

Global `tree.sync()` is rate-limited by Discord to approximately once or twice per day. Calling it on every restart will eventually hit this limit and commands will silently fail to register. The correct workflow: sync to a specific test guild during development, and sync globally only when commands actually change (via the manual `/sync` command you already have).

---

## E7 — Python: `print()` used instead of the `logging` module

~~**Severity: Medium**~~ **✅ RESOLVED** | Codebase-wide

`logging` now used throughout: `import logging` + `logger = logging.getLogger(__name__)` added to every file that had `print()` calls. A `_ColoredFormatter` in `bot.py` colorizes output (DEBUG=grey, INFO=blue, WARNING=yellow, ERROR=red, CRITICAL=bold red). All `print(e)` / `traceback.print_exc()` patterns replaced with `logger.error(..., exc_info=True)`.

Python's `logging` module is the standard for any production application. `print()` has no severity levels, no timestamps without manual formatting, no ability to redirect to files or rotate logs. discord.py itself uses `logging` internally. Setting up a basic logger:

```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

logger.info("Bot is ready")
logger.error("Database failed", exc_info=True)  # includes full traceback automatically
```

The entire `log_to_bot_log` pattern duplicated across 3 cogs would be replaced by a single `logging.Handler` subclass that posts to the Discord `BOT_LOG` channel.

---

## E8 — Python: Raw `dict` used for structured state instead of `dataclasses`

~~**Severity: Low**~~ **✅ RESOLVED** | `feedback_monitor.py`

`PendingValidation` dataclass added to `feedback_monitor.py`; all `pending_validations` dict accesses converted to dot-access. `user_thread` in `threads_manager.py` uses a list `[thread_id, ticket_counter]` shared across `threads_manager.py`, `helpers.py`, `points_logic.py`, and `feedback_threads.py` — converting it requires coordinated changes across all four files; deferred.

`pending_validations`, `user_thread`, and similar dicts store structured multi-field objects as raw dicts. `dataclasses` give free `__repr__`, dot-access instead of string keys, and make the schema explicit:

```python
from dataclasses import dataclass, field

@dataclass
class PendingValidation:
    original_message: discord.Message
    feedback_text: str
    mod_message_id: int
    validated: bool = False
```

---

## E9 — Python: `global bot` in `on_ready` does nothing
~~**Severity: Low**~~ **✅ RESOLVED** | `bot.py:39`

`global bot` removed from `on_ready`; only `global IS_READY` remains, which is correct since `IS_READY` is actually reassigned there.

`global` inside a function is only needed when you _assign_ to the name. `on_ready` never reassigns `bot` — it only reads it. The `global bot` declaration is a no-op and misleads the reader into thinking `bot` is being modified.

---

## E10 — Discord API: No `@app_commands.describe()` on slash command parameters
~~**Severity: Low**~~ **✅ RESOLVED** | `admin.py`, `rank_commands.py`

`@app_commands.describe()` added to all parameterized commands in `admin.py` (add, remove, clear, reload) and `rank_commands.py` (current, add, remove, history).

Discord displays parameter names in the slash command UI but no descriptions unless you add them. Users see raw names like `user`, `points`, `role` with no context. `@app_commands.describe` costs nothing:

```python
@app_commands.describe(
    user="The member to add points to",
    points="Number of points to add (default: 1)"
)
async def add(self, interaction, user: discord.Member, points: int = 1): ...
```

---

## E11 — Discord API: No cooldowns on any slash command
~~**Severity: Medium**~~ **✅ RESOLVED** | `rank_commands.py`

Per-user cooldowns added to all rank commands that hit Google Sheets: `current` (10s), `add` (15s), `remove` (15s), `history` (10s). Admin commands in `admin.py` are gated by the admin permission check which is sufficient.

None of your slash commands have `@app_commands.checks.cooldown`. Commands that hit external APIs (Google Sheets, Spotify, YouTube), generate images (Pillow), or write to a database should have per-user rate limits. Your prefix command error handler already handles `CommandOnCooldown` — the slash equivalent just needs the decorator:

```python
@app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
```

---

## E12 — Discord API: `tasks.loop` not registering third-party exception types

~~**Severity: High**~~ **✅ RESOLVED** | All task loops

`reconnect=True` added to `cleanup_pending_validations` in `feedback_monitor.py`. MySQL-specific `add_exception_type` is no longer applicable after the SQLite migration. Google Sheets tasks (`rank_commands.py`) should still add `add_exception_type(gspread.exceptions.APIError)` if the Sheets integration is reactivated.

`reconnect=True` only handles Discord connectivity errors. Task loops that interact with MySQL (`pymysql.OperationalError`) or Google Sheets (`gspread.exceptions.APIError`) need those exceptions registered explicitly, otherwise any such error crashes the loop permanently instead of triggering the backoff-and-retry logic:

```python
def cog_load(self):
    self.my_task.add_exception_type(pymysql.OperationalError)
    self.my_task.start()
```

---

## E13 — Discord API: Raw reaction listeners instead of `discord.ui.View`

~~**Severity: Medium**~~ **✅ RESOLVED** | `music.py` (NotesMenu), `mod_bad_feedback_notification.py`

- `mod_bad_feedback_notification.py`: `add_reaction` + `wait_for` replaced with `_BadFeedbackView(discord.ui.View)` containing ✅ Dismiss and ❌ Notify User buttons (300s timeout). Buttons disable themselves after use.
- `music.py`: `NotesMenu(menus.Menu)` + manual `add_listener` replaced with `NotesView(discord.ui.View)` using `_OptionButton` and `_NavButton` helper classes. View rebuilds its items on each interaction via `clear_items()`. `on_timeout()` deletes the message.

Both use raw reaction adding + `wait_for` or manual `add_listener` patterns, which were the pre-2.0 approach. discord.py 2.x has `discord.ui.View` with `discord.ui.Button` — these are timeout-aware, handle their own cleanup, and can be made persistent across bot restarts with `persistent=True` and a `custom_id`. The moderator ✅/❌ buttons in `mod_bad_feedback_notification.py` are a perfect candidate: a persistent view means the moderator can react hours later and it still works.

---

## E14 — Discord API: `cog_check` / `interaction_check` not used for cog-wide validation

~~**Severity: Low**~~ **✅ RESOLVED** | `cogs/general.py`, `cogs/guild_events.py`, `cogs/music.py`, `cogs/slash_commands/admin.py`, `cogs/slash_commands/rank_commands.py`

`cog_check` added to `General`, `Guild_events`, and `Music` prefix cogs — replacing all per-command `@commands.check(guild_only)` decorators. `interaction_check` added to `Admin` and `RankCommands` slash cogs for guild-only guard.

`cog_check(ctx)` (prefix) and `interaction_check(interaction)` (slash) run before every command in the cog. They are the right place for guild-only guards, maintenance mode, or bot-not-ready checks — not inside every command handler individually.

```python
class Admin(commands.Cog):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return False
        return True
```

---

## E15 — Missing Feature: Autocomplete on known-value parameters

~~**Severity: Low**~~ **✅ RESOLVED** | `rank_commands.py`

Autocomplete added to the `/reload` extension parameter in `admin.py` (shows all loaded extension names filtered as the user types). Rank command parameters (`rank`, `role`) in `rank_commands.py` also have autocomplete against the known rank list.

Commands where valid values are a known set (rank names, genres) should use `@app_commands.autocomplete` to show filtered dropdowns as the user types. This is the single highest-impact UX improvement available with minimal implementation cost.

```python
async def rank_autocomplete(interaction: discord.Interaction, current: str):
    ranks = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
    return [app_commands.Choice(name=r, value=r) for r in ranks if current.lower() in r.lower()]

@app_commands.autocomplete(rank=rank_autocomplete)
async def add_role(self, interaction, rank: str): ...
```

---

## E16 — Missing Feature: No `/reload` command

~~**Severity: Medium**~~ **✅ RESOLVED**

`/reload` slash command added to the `Admin` cog with `@app_commands.checks.has_permissions(administrator=True)`. Accepts an extension name string and calls `bot.reload_extension(extension)`.

There is no way to reload a cog without restarting the bot. A standard owner-only reload command is essential for development and for applying hotfixes in production without downtime:

```python
@app_commands.command()
@app_commands.checks.has_permissions(administrator=True)
async def reload(self, interaction: discord.Interaction, extension: str):
    await self.bot.reload_extension(extension)
    await interaction.response.send_message(f"Reloaded `{extension}`", ephemeral=True)
```

---

## E17 — Missing Feature: No `/status` or `/health` command

~~**Severity: Medium**~~ **✅ RESOLVED**

`/status` slash command added to the `Admin` cog. Reports latency, loaded cog count, guild count, and a full list of loaded cog names — all ephemeral.

No command exists to inspect runtime state without checking logs or restarting. A status command that reports task loop states, DB pool health, and last sync time is invaluable for diagnosing the "tasks stopped after a few days" problem without a restart.

---

## E18 — Missing Feature: No batching for Google Sheets writes

~~**Severity: Medium**~~ **✅ RESOLVED** | `google_sheet.py`

`update_rank_spreadsheet` now uses `worksheet.batch_update()` to combine the cell-find + cell-write into a single API call. New users are written with `worksheet.append_row()` (already a single call). The rank history read in `rank_commands.py` uses `get_all_values()` (already one call).

Google's Sheets API has a quota of 60 read/write requests per minute per project. Each rank add/remove command makes multiple individual API calls. Under any moderate usage this will hit the quota silently (gspread raises `APIError` with a 429). Writes should be queued and batched using `worksheet.batch_update()`.

---

## Etiquette Review — Issue Index

| ID  | File                                           | Description                                                                    | Severity                   |
| --- | ---------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------- |
| E1  | `bot.py:47–61`                                 | Cog init in `on_ready` instead of `async def cog_load`                         | ~~**High**~~ ✅ Resolved   |
| E2  | `bot.py:115–117`                               | Slash command global error handler sends raw errors, can crash on None channel | ~~**High**~~ ✅ Resolved   |
| E3  | `cogs/general.py`                              | No `cog_command_error` in any cog                                              | ~~**Medium**~~ ✅ Resolved |
| E4  | `admin.py:25`                                  | Manual permission check duplicates decorator logic                             | ~~**Medium**~~ ✅ Resolved |
| E5  | `admin.py`, `rank_commands.py`                 | No `@app_commands.guild_only()` — crashes in DMs                               | ~~**High**~~ ✅ Resolved   |
| E6  | `bot.py:71`                                    | Global `tree.sync()` on every boot — rate limit risk                           | ~~**Medium**~~ ✅ Resolved |
| E7  | Codebase-wide                                  | `print()` instead of `logging` module                                          | ~~**Medium**~~ ✅ Resolved |
| E8  | `feedback_monitor.py` etc.                     | Raw dicts for structured state instead of `dataclasses`                        | ~~**Low**~~ ✅ Resolved    |
| E9  | `bot.py:39`                                    | `global bot` is a no-op                                                        | ~~**Low**~~ ✅ Resolved    |
| E10 | `admin.py`, `rank_commands.py`                 | No `@app_commands.describe()` on parameters                                    | ~~**Low**~~ ✅ Resolved    |
| E11 | `rank_commands.py`                             | No `@app_commands.checks.cooldown` on any command                              | ~~**Medium**~~ ✅ Resolved |
| E12 | All task loops                                 | `add_exception_type()` not called for DB/Sheets exceptions                     | ~~**High**~~ ✅ Resolved   |
| E13 | `music.py`, `mod_bad_feedback_notification.py` | Raw reactions instead of `discord.ui.View`                                     | ~~**Medium**~~ ✅ Resolved |
| E14 | All cogs                                       | `interaction_check` not used for cog-wide guards                               | ~~**Low**~~ ✅ Resolved    |
| E15 | `rank_commands.py` etc.                        | No autocomplete on known-value parameters                                      | ~~**Low**~~ ✅ Resolved    |
| E16 | —                                              | No `/reload` command — must restart to apply changes                           | ~~**Medium**~~ ✅ Resolved |
| E17 | —                                              | No `/status` / `/health` command                                               | ~~**Medium**~~ ✅ Resolved |
| E18 | `google_sheet.py`                              | Individual Sheets writes not batched — quota risk                              | ~~**Medium**~~ ✅ Resolved |
