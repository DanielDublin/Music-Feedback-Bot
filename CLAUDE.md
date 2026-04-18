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
- `DB_HOST`, `PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — MySQL connection details

Google Sheets integration requires `mf-bot-402714-b394f37c96dc.json` (gitignored) in the project root.

## Architecture Overview

This is a **discord.py 2.x bot** for a music feedback Discord server. The bot uses a **1-for-1 point system**: users earn MF Points by giving feedback (`<MFR`) and spend them to request feedback on their own music (`<MFS`).

### Entry Points
- `bot.py` — main entry point; loads all cog extensions and starts the bot
- `watchdog.py` — subprocess-based watchdog that restarts `bot.py` on crash
- Deployment: GitHub Actions (`.github/workflows/deploy.yml`) deploys to GCP VM via SSH on push to `master`, running `watchdog.py` inside a tmux session

### Command Prefixes
`<MF`, `<Mf`, `<mF`, `<mf` (case-insensitive, strip-after-prefix)

### Cog Structure
All cogs are registered in `bot.py` in two lists: `initial_extensions` and `slash_extensions`.

| Cog | Purpose |
|-----|---------|
| `cogs/general.py` | Core `<MFR` (give feedback, +1 pt) and `<MFS` (request feedback, -1 pt) commands, plus `<MFpoints`, `<MFtop`, `<MFgenres`, `<MFsimilar` |
| `cogs/feedback_threads/` | Manages per-user private threads that log all feedback activity; handles message edits and deletions with point corrections |
| `cogs/guild_events.py` | Member join/leave/ban handlers |
| `cogs/user_listener.py` | Message listeners for automated point management |
| `cogs/member_cards/` | Image generation for member profile cards (Pillow) |
| `cogs/slash_commands/` | Slash command cogs (admin, rank, threads search/delete, member card, AOTW event) |
| `ml_model/feedback_monitor.py` | ML-powered feedback quality detection cog |
| `cogs/finished_music_message.py` | Listeners for the finished music channel |

### Dual Database System
- **MySQL** (`database/db.py`) — primary persistent store for user points, warnings, and kicks. Uses an in-memory `users_dict` cache that is populated lazily and cleared weekly. Reconnects automatically on "lost connection" errors.
- **SQLite** (`database/threads_db.py`, file: `feedback_threads.sqlite`) — stores the mapping of `user_id → (thread_id, ticket_counter)` for feedback threads. This is loaded into the `user_thread` dict in memory on bot startup.

### Feedback Thread System (`cogs/feedback_threads/`)
Each user gets a single persistent private Discord thread (in `THREADS_CHANNEL`) that acts as a moderation log. The `user_thread` dict (`{user_id: [thread_id, ticket_counter]}`) is the runtime state, backed by SQLite.

Key submodules:
- `threads_manager.py` — creates/retrieves threads, increments ticket counters
- `points_logic.py` — handles all point add/remove logic for MFR/MFS commands, edits, and deletions
- `embeds.py` — builds Discord embeds for thread log entries
- `helpers.py` (`DiscordHelpers`) — shared utility methods for loading cogs, adding/removing points, and getting thread IDs

### ML Feedback Quality System (`ml_model/`)
- `ml_model_loader.py` — loads a scikit-learn model (`model.pkl`) and TF-IDF vectorizer (`vectorizer.pkl`) from `ml_model/simple_feedback_model/`. Predicts Pass/Fail on `<MFR` messages in the audio feedback channel.
- `feedback_monitor.py` — the cog that hooks `on_message` for `AUDIO_FEEDBACK` channel, runs predictions, posts results to `DEV_SPAM` with reaction-based human validation (✅/❌), and exports validated samples to `feedback_json.json` for future retraining.
- `mod_bad_feedback_notification.py` (`FeedbackNotifier`) — notifies moderators when low-quality feedback is detected.

### Constants and Environment Switching
`data/constants.py` contains all hardcoded Discord IDs (channel IDs, role IDs, user IDs). There are two complete blocks: **PROD** (active) and **TESTING** (commented out). To switch environments, comment/uncomment the respective block — do not mix IDs from both blocks.
