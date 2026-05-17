# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the bot (development):**
```bash
python bot.py
```

**Run with auto-restart watchdog (production-style):**
```bash
python watchdog.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

There are no automated tests in this project.

## Environment Variables

The bot requires a `.env` file (gitignored) with:
- `DISCORD_TOKEN` — Discord bot token
- `SERVER_ID` — main Discord guild ID (also duplicated in `data/constants.py`)
- `DB_HOST`, `PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — MySQL connection details

Google Sheets integration requires `mf-bot-402714-b394f37c96dc.json` (gitignored) in the project root.

## Architecture Overview

This is a **discord.py 2.x bot** for a music feedback Discord server. The bot uses a **1-for-1 point system**: users earn MF Points by giving feedback (`<MFR`) and spend them to request feedback on their own music (`<MFS`).

### Entry Points
- `bot.py` — main entry point; constructs the `MFBot` (subclass of `commands.Bot`), loads all cog extensions, configures logging, and starts the bot
- `watchdog.py` — subprocess-based watchdog that restarts `bot.py` on crash
- Deployment: GitHub Actions (`.github/workflows/deploy.yml`) deploys to a GCP VM via SSH on push to `master`, running `watchdog.py` inside a tmux session

### Required Intents
Set in `bot.py`:
- `members` — needed for join/leave/ban handlers and member lookups
- `message_content` — needed because the bot uses prefix commands and inspects message text
- `moderation` — required for `on_audit_log_entry_create` (used by the captcha counter)

### Command Prefixes
`<MF`, `<Mf`, `<mF`, `<mf` (case-insensitive, strip-after-prefix). Slash commands are registered globally and per-guild via `bot.tree.sync()` on `on_ready`.

### Cog Structure
All cogs are registered in `bot.py` in two lists: `initial_extensions` (prefix-command and listener cogs) and `slash_extensions` (slash-command cogs). Anything not in those lists is **not loaded**, regardless of whether the file exists.

#### `initial_extensions`
| Cog | Purpose |
|-----|---------|
| `cogs.general` | Core `<MFR` (give feedback, +1 pt) and `<MFS` (request feedback, -1 pt) commands, plus `<MFpoints`, `<MFtop`, `<MFgenres`, `<MFsimilar` |
| `cogs.user_listener` | Message listeners for automated point management and channel hygiene |
| `cogs.guild_events` | Member join / leave / ban handlers |
| `cogs.music` | `<MFnotes` paged notes browser with `_OptionButton` / `_NavButton` / `NotesView` UI |
| `cogs.owner_utilities` | Owner-only debug / maintenance commands |
| `cogs.help_command` | Custom paged help menu (built on `discord-ext-menus`) — replaces the default `help` command (removed in `bot.py`) |
| `modules.scan_delete_intro_messages` | Sweeps the intros channel and removes non-conforming messages |
| `cogs.feedback_threads.feedback_threads` | Manages per-user private threads that log all feedback activity; handles message edits and deletions with point corrections |
| `ml_model.feedback_monitor` | ML-powered feedback quality detection cog |
| `cogs.finished_music_message` | Listeners for the finished music channel |
| `cogs.captcha_counter` | Tracks bots kicked by Captcha.bot via audit log; renders a Components V2 counter card |

#### `slash_extensions`
| Cog | Purpose |
|-----|---------|
| `cogs.slash_commands.timer` | `/timer` — countdown timer utility |
| `cogs.slash_commands.admin` | Admin/dev commands: reload/load/unload extensions (with autocomplete), other maintenance |
| `cogs.slash_commands.rank_commands` | Rank role management and queries |
| `cogs.slash_commands.threads` | Search / delete feedback threads |
| `cogs.slash_commands.get_member_card` | `/membercard` — renders the Pillow member card image |
| `cogs.slash_commands.aotw_event` | Album of the Week event flow (poll creation, channel configuration, scheduling) |
| `cogs.slash_commands.prime_time` | "Prime Time" 2× feedback window. Manual `/primetime start|stop|status` slash commands **plus** auto-trigger driven by `record_quality_feedback()` called from `ml_model.feedback_monitor`. See "Prime Time" section below |

`cogs/slash_commands/hello.py` and `cogs/slash_commands/timer_cogs/` exist on disk but are **not** registered in `bot.py`.

### Dual Database System
- **MySQL** (`database/db.py`) — primary persistent store for user points, warnings, and kicks. Uses an in-memory `users_dict` cache that is populated lazily and cleared weekly via `schedule_weekly_task()` (created in `bot.py:main()`). Reconnects automatically on "lost connection" errors.
- **SQLite** (`database/threads_db.py`, file: `feedback_threads.sqlite`) — stores the mapping of `user_id → (thread_id, ticket_counter)` for feedback threads. Loaded into the `user_thread` dict in memory on bot startup.

### Feedback Thread System (`cogs/feedback_threads/`)
Each user gets a single persistent private Discord thread (in `THREADS_CHANNEL`) that acts as a moderation log. The `user_thread` dict (`{user_id: [thread_id, ticket_counter]}`) is the runtime state, backed by SQLite.

Key submodules under `cogs/feedback_threads/modules/`:
- `threads_manager.py` — creates/retrieves threads, increments ticket counters
- `points_logic.py` — handles all point add/remove logic for MFR/MFS commands, edits, and deletions
- `embeds.py` — builds Discord embeds for thread log entries
- `helpers.py` (`DiscordHelpers`) — shared utility methods for loading cogs, adding/removing points, and getting thread IDs
- `ctx_class.py` (`ContextLike`) — unifies `commands.Context` and `discord.Interaction` so prefix and slash command paths can call the same thread-creation logic
- `check_rank_embed.py` (`PaginationView`) — paginated rank embed

### Member Cards (`cogs/member_cards/`)
Pillow-based profile card renderer used by `/membercard` and the rank flow.
- `member_card_renderer.py` — `generate_card()` (sync, heavy) and `render_member_card()` (async wrapper). Handles wrapping, stars, top-MFR badge, animated variants
- `member_data.py` (`MemberData`) — pulls the values that feed `generate_card()`
- `add_rank_member_card.py` — cog wiring for the rank flow

### Captcha Counter (`cogs/captcha_counter.py`)
Reactive counter for bots kicked by `CAPTCHA_BOT_ID` (a separate moderation bot).
- Listens to `on_audit_log_entry_create`, filters to `AuditLogAction.kick` entries authored by the captcha bot
- Persists state to `data/captcha_counter.json` (`count`, `message_id`, `last_catch_ts`) via atomic temp-file rename
- Renders a Components V2 `LayoutView` (`CounterDisplay`) — a single `Container` with title, flavor, rank/last-catch line, a disabled "Bots Caught: N" button, and a randomized footer. Tiers, footers, milestone messages, and chat-warmer lines are module-level pools at the top of the file
- After each kick: bumps state, edits or recreates the pinned counter message, announces one-time milestones, then sends and immediately deletes a short "chat warmer" message to nudge the channel as unread without leaving visible spam

### Prime Time (`cogs/slash_commands/prime_time.py`)
2× MFR points window. Two operation modes:

**Slash commands** (all admin-only, in the `/primetime` group):
- `/primetime start [minutes]` — manual start (sets `_active_kind = "manual"`)
- `/primetime stop` — end the active event early
- `/primetime status` — full snapshot: active event + both auto-trigger counters + last fire timestamps + next-eligible timestamps
- `/primetime reset_cooldown <daily|saturday|both>` — admin testing helper
- `/primetime reset_counter <daily|saturday|both>` — clear the rolling deque (daily) or today's count (saturday)
- `/primetime force_fire <daily|saturday>` — fire an auto event as if its goal had been hit; refuses if anything is already active

**Auto-trigger** — `record_quality_feedback()` is called by `ml_model.feedback_monitor` for every ML-pass `<MFR` submission. Two goals run concurrently:
- **Daily rolling**: `_DAILY_GOAL=10` quality feedbacks within `_DAILY_WINDOW_SECONDS=3600` (1 hour) fires a 60-min Prime Time. Cooldown `_DAILY_COOLDOWN_HOURS=24`. As the rolling counter climbs, staged build-up nudges post at `_NUDGE_STAGES = (3, 5, 7, 9)` — one message per stage crossed, drawn from the `_NUDGES` per-stage pool (music/mix-themed copy)
- **Bi-weekly Saturday**: `_SATURDAY_GOAL=50` quality feedbacks across a UTC Saturday fires a 240-min (4h) Prime Time. Cooldown `_SATURDAY_COOLDOWN_DAYS=14`. Build-up nudges at `_SATURDAY_NUDGE_STAGES = (10, 25, 40, 49)` from the festival-themed `_SATURDAY_NUDGES` pool; the highest crossed stage is persisted as `last_saturday_nudge_stage` so a restart mid-Saturday doesn't re-post

**Extension rule** — `_extend_active` only runs on *cross-kind* overlap (Daily goal hits during an active Saturday, or vice versa). Same-kind re-triggers and any goal during a manual event drain the counter without extending. When extension does happen, it appends the full fresh-duration of the incoming kind onto the remaining time of the active event (no cap — cross-kind overlaps are naturally rate-limited by the per-kind cooldowns).

Auto-trigger state persists in `data/prime_time_state.json` (cooldown timestamps + saturday-day counter). The rolling-window deque is in-memory only — it loses progress on restart, which is intended.

Only **quality-passing** feedbacks count toward goals. Lyric-feedback `<MFR` posts are not currently tracked (feedback_monitor only watches `AUDIO_FEEDBACK`).

**Bonus eligibility rule** — what earns 2× during an active Prime Time:
- In `AUDIO_FEEDBACK`: `ml_model.ml_model_loader.quality_qualifies_for_bonus()` must return True (model says `is_good` with confidence ≥ `BONUS_QUALITY_THRESHOLD`, default 0.60)
- In `LYRIC_FEEDBACK`: feedback must be ≥ 300 characters (the ML model wasn't trained on lyric feedback, so we keep the length-based rule there)
- When the ML predictor errors (model not loaded, crash), audio feedback falls back to the 300-char rule too so an outage doesn't strip the bonus from everyone

Mirrored in `general.py` (MFR award) and `cogs/feedback_threads/modules/points_logic.py` (MFR_delete refund) — keep them in sync if you change the rule.

### ML Feedback Quality System (`ml_model/`)
- `ml_model_loader.py` — loads a scikit-learn model (`model.pkl`) and TF-IDF vectorizer (`vectorizer.pkl`) from `ml_model/simple_feedback_model/`. Predicts Pass/Fail on `<MFR` messages in the audio feedback channel
- `feedback_monitor.py` — the cog that hooks `on_message` for `AUDIO_FEEDBACK` channel, runs predictions, posts results to `DEV_SPAM` with reaction-based human validation (✅/❌), and exports validated samples to `feedback_json.json` for future retraining
- `mod_bad_feedback_notification.py` (`FeedbackNotifier`) — notifies moderators when low-quality feedback is detected

### Supporting Modules (`modules/`)
- `scan_delete_intro_messages.py` — registered as a cog; sweeps the intros channel
- `cooldowns.py` — shared cooldown helpers used by command cogs
- `genres.py`, `similar_bands.py` — data/logic for `<MFgenres` and `<MFsimilar`
- `promotion_checkers/` — role-promotion eligibility checks
- `modules/aotw/` is a sibling of `cogs/aotw/`; both feed the AOTW flow

### Constants and Environment Switching
`data/constants.py` holds all hardcoded Discord IDs (channels, roles, users). Driven by the **`MF_ENV`** env var:
- `MF_ENV=prod` (default, also when unset) — uses the canonical production guild IDs
- `MF_ENV=test` — applies the TEST overrides at the bottom of the file on top of the prod defaults

Set `MF_ENV=test` in your `.env` to flip the bot to the test guild. The file exposes `MF_ENV` so other modules can branch on it (e.g., skip a Google Sheets write in test mode). Constants not present in the TEST override block automatically fall back to their PROD value — that's safer than the old comment-toggle pattern, which would leave newly-added constants undefined whenever the testing block hadn't been kept in sync.

### Persisted JSON State
Several cogs persist small bits of state as JSON files alongside the code:
- `data/captcha_counter.json` — captcha counter state
- `MF_Points.json`, `user_ids.json`, `output.json` — legacy / auxiliary data files in the project root
- `cogs/options.json` — options for the music notes browser

When writing new state files, prefer the atomic write pattern used in `captcha_counter.py:_save_state()` (write to `.tmp`, then `os.replace`).

### Logging Convention
Every module uses the standard Python `logging` module. **Never use `print()`.** The pattern is:

```python
import logging
logger = logging.getLogger(__name__)
```

Use appropriate levels:
- `logger.debug(...)` — verbose tracing (per-message processing steps, cache hits)
- `logger.info(...)` — normal operational events (cog loaded, task completed, role changed)
- `logger.warning(...)` — recoverable issues (channel not found, rate limited)
- `logger.error("...", exc_info=True)` — failures with full traceback; replaces `print(e)` + `traceback.print_exc()`
- `logger.critical(...)` — fatal startup failures only

The root logger is configured in `bot.py:main()` with a `_ColoredFormatter` that colorizes terminal output by level (DEBUG=grey, INFO=blue, WARNING=yellow, ERROR=red, CRITICAL=bold red).

**Discord-side log mirror:** `utils/bot_logger.py:DiscordChannelHandler` is attached at WARNING+ and forwards each record to the `BOT_LOG` channel (defined in `data/constants.py`), chunked to fit Discord's 2000-char limit. It silently drops records emitted before `bot.is_ready()` or after the event loop is gone. This means any `logger.warning(...)` or worse will appear in `BOT_LOG` — keep that in mind when adding noisy warnings.

### Error Handling
- Prefix-command errors flow through `exception_handler.handle_exception()` (registered as `on_command_error` in `bot.py`)
- Slash-command errors are handled inline in `bot.py:on_app_command_error` (cooldown / missing-perms / check-failure / fallback). When adding new slash commands, rely on this handler rather than duplicating try/except in every command
