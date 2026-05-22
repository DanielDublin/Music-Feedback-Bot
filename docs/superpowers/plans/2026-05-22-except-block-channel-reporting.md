# Except-Block Reporting to BOT_LOG — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every meaningful caught exception in the project surface in the `BOT_LOG` Discord channel, with duplicate-suppression so hot-path errors cannot flood it.

**Architecture:** Two pieces. (1) Add a 60-second sliding-window dedup cache to `DiscordChannelHandler` so identical records collapse. (2) Audit every in-scope `except` block so it logs at WARNING+ — the existing handler already routes WARNING+ to the channel, so no new logging API is needed.

**Tech Stack:** Python 3.11, `logging` stdlib, discord.py 2.6.4. No automated test framework in this project (per CLAUDE.md) — verification is `ast.parse`/`py_compile` + import tests, plus a temporary self-check script for the dedup logic.

**Spec:** `docs/superpowers/specs/2026-05-22-except-block-channel-reporting-design.md`

---

## Shared Audit Rules (Piece 2 — referenced by Tasks 2–11)

Apply these to every `except` block in the files a task names.

**Fix patterns** — smallest change that emits a WARNING+ record:

| Current form | Fix |
|---|---|
| `except X: pass` (or silent — only `return`/`continue`/restore-default) | add `logger.error("<context message>", exc_info=True)` before the recovery action (or `logger.warning(...)` if benign-but-notable) |
| `except X:` logging at `logger.debug(...)` / `logger.info(...)` | raise the level to `logger.warning` or `logger.error` |
| `except X: print(...)` | replace with `logger.error("<context>", exc_info=True)` |
| already `logger.warning(...)` / `logger.error(...)` | leave unchanged |

**Severity guide:** structural / network / database / data-access / filesystem / JSON / logic failures → `logger.error(..., exc_info=True)`. Recoverable or expected-but-notable conditions → `logger.warning(...)`.

**If a file has no module logger**, add at the top after imports:
```python
import logging
logger = logging.getLogger(__name__)
```

**OUT OF SCOPE — do NOT bump these to WARNING+** (routine user behavior, not failures): `except` blocks catching `commands.CommandNotFound`, `commands.BadArgument`, `commands.CheckFailure`, `commands.MissingRequiredArgument`, `commands.CommandOnCooldown`, or an obvious custom "expected user input error". Leave them as-is, or at `logger.debug` if they currently log louder.

**HARD CARVE-OUTS — never touched by this plan:** `utils/bot_logger.py` (its own `except` blocks must stay `print`-to-stderr — logging inside the log handler risks recursion) and `watchdog.py` (separate process, no Discord connection).

**Per-file verification** (used in every Piece 2 task):
```bash
python -c "import ast; ast.parse(open('PATH', encoding='utf-8').read()); print('syntax OK')"
python -c "import importlib; importlib.import_module('MODULE'); print('import OK')"
```
Then read the task's own diff and confirm every modified `except` block emits WARNING+.

---

## Task 1: Dedup / rate-limit in `DiscordChannelHandler`

**Files:**
- Modify: `utils/bot_logger.py`
- Test: `verify_dedup.py` (temporary, repo root — created, run, then deleted)

- [ ] **Step 1: Write the temporary verification script**

Create `verify_dedup.py` at the repo root:

```python
# verify_dedup.py - temporary self-check for DiscordChannelHandler dedup. Delete after running.
import logging
import utils.bot_logger as bl


class _FakeBot:
    def is_ready(self):
        return True

    def get_channel(self, _):
        return None


def _record(msg, level=logging.ERROR, name="test"):
    return logging.LogRecord(name, level, __file__, 0, msg, None, None)


def main():
    fake_now = [1000.0]
    bl.time.monotonic = lambda: fake_now[0]

    h = bl.DiscordChannelHandler(_FakeBot())

    assert h._dedup_check(_record("boom")) == (True, 0), "first send"
    assert h._dedup_check(_record("boom")) == (False, 0), "repeat suppressed"
    assert h._dedup_check(_record("boom")) == (False, 0), "repeat suppressed"
    assert h._dedup_check(_record("other")) == (True, 0), "distinct msg sends"

    fake_now[0] += 61
    assert h._dedup_check(_record("boom")) == (True, 2), "post-window flush with count"
    assert h._dedup_check(_record("boom")) == (False, 0), "suppressed again after flush"

    print("dedup verification: ALL PASS")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python verify_dedup.py`
Expected: `AttributeError: 'DiscordChannelHandler' object has no attribute '_dedup_check'`

- [ ] **Step 3: Rewrite `utils/bot_logger.py` with the dedup cache**

Full new file content:

```python
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
```

- [ ] **Step 4: Run the verification script to verify it passes**

Run: `python verify_dedup.py`
Expected: `dedup verification: ALL PASS`

- [ ] **Step 5: Delete the temporary script**

Run: `python -c "import os; os.remove('verify_dedup.py')"`

- [ ] **Step 6: Commit**

```bash
git add utils/bot_logger.py
git commit -m "logging: dedup repeated records in DiscordChannelHandler"
```

---

## Task 2: Audit `ml_model/feedback_monitor.py` (21 except blocks)

This is the spec's example file (the attribute-access cleanup case). Apply the **Shared Audit Rules** above.

**Files:**
- Modify: `ml_model/feedback_monitor.py`

- [ ] **Step 1: Apply the audit**

Read every `except` block in the file. For each non-compliant block (silent `pass`, `debug`/`info`-level log, or `print`), apply the fix-pattern table from Shared Audit Rules. In-scope here: ML prediction errors, message-processing errors, validation-export I/O. No command/validation `except` blocks expected in this file.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; ast.parse(open('ml_model/feedback_monitor.py', encoding='utf-8').read()); print('syntax OK')"
python -c "import importlib; importlib.import_module('ml_model.feedback_monitor'); print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add ml_model/feedback_monitor.py
git commit -m "error visibility: route feedback_monitor except blocks to BOT_LOG"
```

---

## Task 3: Audit `cogs/slash_commands/aotw_event.py` (37 except blocks)

Largest file in the audit. Apply the **Shared Audit Rules**.

**Files:**
- Modify: `cogs/slash_commands/aotw_event.py`

- [ ] **Step 1: Apply the audit**

Read every `except` block. Bump silent / sub-WARNING / `print` blocks per the fix patterns. Watch for the OUT-OF-SCOPE rule: any block catching command/argument-validation errors stays quiet. Slash-command flow errors (Discord API, scheduling, channel ops) are in scope.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; ast.parse(open('cogs/slash_commands/aotw_event.py', encoding='utf-8').read()); print('syntax OK')"
python -c "import importlib; importlib.import_module('cogs.slash_commands.aotw_event'); print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/slash_commands/aotw_event.py
git commit -m "error visibility: route aotw_event except blocks to BOT_LOG"
```

---

## Task 4: Audit `cogs/member_cards/` (23 except blocks)

**Files:**
- Modify: `cogs/member_cards/member_data.py` (14)
- Modify: `cogs/member_cards/member_card_renderer.py` (5)
- Modify: `cogs/member_cards/add_rank_member_card.py` (4)

- [ ] **Step 1: Apply the audit to all three files**

Apply the **Shared Audit Rules**. In scope: Pillow rendering errors, data-fetch errors, font/asset I/O. No command/validation blocks expected.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['cogs/member_cards/member_data.py','cogs/member_cards/member_card_renderer.py','cogs/member_cards/add_rank_member_card.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['cogs.member_cards.member_data','cogs.member_cards.member_card_renderer','cogs.member_cards.add_rank_member_card']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/member_cards/
git commit -m "error visibility: route member_cards except blocks to BOT_LOG"
```

---

## Task 5: Audit `cogs/slash_commands/` remainder (27 except blocks)

**Files:**
- Modify: `cogs/slash_commands/prime_time.py` (13)
- Modify: `cogs/slash_commands/rank_commands.py` (7)
- Modify: `cogs/slash_commands/get_member_card.py` (6)
- Modify: `cogs/slash_commands/admin/runtime.py` (1)

- [ ] **Step 1: Apply the audit to all four files**

Apply the **Shared Audit Rules**. In scope: Prime Time state/persistence errors, rank role ops, member-card rendering, extension reload errors. `admin/runtime.py`'s `except` in `handle_reload` reports failure to the user already — also ensure it logs at `error`.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['cogs/slash_commands/prime_time.py','cogs/slash_commands/rank_commands.py','cogs/slash_commands/get_member_card.py','cogs/slash_commands/admin/runtime.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['cogs.slash_commands.prime_time','cogs.slash_commands.rank_commands','cogs.slash_commands.get_member_card','cogs.slash_commands.admin']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/slash_commands/prime_time.py cogs/slash_commands/rank_commands.py cogs/slash_commands/get_member_card.py cogs/slash_commands/admin/runtime.py
git commit -m "error visibility: route slash-command except blocks to BOT_LOG"
```

---

## Task 6: Audit `cogs/feedback_threads/` (20 except blocks)

**Files:**
- Modify: `cogs/feedback_threads/feedback_threads.py` (8)
- Modify: `cogs/feedback_threads/modules/points_logic.py` (12)

- [ ] **Step 1: Apply the audit to both files**

Apply the **Shared Audit Rules**. In scope: thread create/fetch errors, point add/remove/refund logic errors, embed/send failures. No command/validation blocks expected.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['cogs/feedback_threads/feedback_threads.py','cogs/feedback_threads/modules/points_logic.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['cogs.feedback_threads.feedback_threads','cogs.feedback_threads.modules.points_logic']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/feedback_threads/feedback_threads.py cogs/feedback_threads/modules/points_logic.py
git commit -m "error visibility: route feedback_threads except blocks to BOT_LOG"
```

---

## Task 7: Audit `cogs/aotw/` (13 except blocks)

**Files:**
- Modify: `cogs/aotw/configure_channel.py` (8)
- Modify: `cogs/aotw/create_poll.py` (5)

- [ ] **Step 1: Apply the audit to both files**

Apply the **Shared Audit Rules**. In scope: channel-config errors, poll state save/restore/clear (JSON I/O), channel scrape/purge errors.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['cogs/aotw/configure_channel.py','cogs/aotw/create_poll.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['cogs.aotw.configure_channel','cogs.aotw.create_poll']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/aotw/configure_channel.py cogs/aotw/create_poll.py
git commit -m "error visibility: route aotw except blocks to BOT_LOG"
```

---

## Task 8: Audit `cogs/` top-level + `cogs/general/` (27 except blocks)

**Files:**
- Modify: `cogs/captcha_counter.py` (9)
- Modify: `cogs/finished_music_message.py` (5)
- Modify: `cogs/user_listener.py` (3)
- Modify: `cogs/owner_utilities.py` (3)
- Modify: `cogs/general/feedback.py` (3)
- Verify-only: `cogs/backup.py` (3)
- Modify: `cogs/music.py` (1)

- [ ] **Step 1: Apply the audit to all seven files**

Apply the **Shared Audit Rules**. In scope: captcha-counter state/render errors, finished-music channel ops, listener errors, owner-utility errors, MFR/MFS DM-send failures, notes-browser errors. `cogs/general/feedback.py`'s DM-failure `except` blocks already log at `warning` — leave them. `cogs/backup.py`'s 3 `except` blocks already log at `logger.error` (added during the task-loop hardening work) — confirm and leave them; expect no diff for that file. No command/validation blocks expected (those go through `cog_command_error`).

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['cogs/captcha_counter.py','cogs/finished_music_message.py','cogs/user_listener.py','cogs/owner_utilities.py','cogs/general/feedback.py','cogs/backup.py','cogs/music.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['cogs.captcha_counter','cogs.finished_music_message','cogs.user_listener','cogs.owner_utilities','cogs.general','cogs.backup','cogs.music']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add cogs/captcha_counter.py cogs/finished_music_message.py cogs/user_listener.py cogs/owner_utilities.py cogs/general/feedback.py cogs/music.py
git commit -m "error visibility: route core cog except blocks to BOT_LOG"
```

---

## Task 9: Audit `ml_model/` remainder (10 except blocks)

**Files:**
- Modify: `ml_model/ml_model_loader.py` (4)
- Modify: `ml_model/mod_bad_feedback_notification.py` (3)
- Modify: `ml_model/export_json.py` (3)

- [ ] **Step 1: Apply the audit to all three files**

Apply the **Shared Audit Rules**. In scope: model/vectorizer load errors, prediction errors, moderator-notification send errors, JSON export I/O.

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['ml_model/ml_model_loader.py','ml_model/mod_bad_feedback_notification.py','ml_model/export_json.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['ml_model.ml_model_loader','ml_model.mod_bad_feedback_notification','ml_model.export_json']]; print('import OK')"
```
Expected: both print OK.

- [ ] **Step 3: Commit**

```bash
git add ml_model/ml_model_loader.py ml_model/mod_bad_feedback_notification.py ml_model/export_json.py
git commit -m "error visibility: route ml_model except blocks to BOT_LOG"
```

---

## Task 10: Audit `modules/` + `database/` (20 except blocks)

**Files:**
- Modify: `modules/scan_delete_intro_messages.py` (5)
- Modify: `modules/promotion_checkers/youtube_promotion_checker.py` (2)
- Modify: `modules/promotion_checkers/soundcloud_promotion_checker.py` (2)
- Modify: `modules/promotion_checkers/spotify_promotion_checker.py` (1)
- Modify: `database/threads_db.py` (7)
- Modify: `database/db.py` (2)
- Modify: `database/google_sheet.py` (1)

- [ ] **Step 1: Apply the audit to all seven files**

Apply the **Shared Audit Rules**. In scope: intro-message sweep errors, promotion-checker network/parse errors, SQLite errors (`threads_db.py`), MySQL errors (`db.py`), Google Sheets API errors. `scan_delete_intro_messages.py`'s before_loop `except` already logs at `error` — leave it. Database `except` blocks are all in scope (structural).

- [ ] **Step 2: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['modules/scan_delete_intro_messages.py','modules/promotion_checkers/youtube_promotion_checker.py','modules/promotion_checkers/soundcloud_promotion_checker.py','modules/promotion_checkers/spotify_promotion_checker.py','database/threads_db.py','database/db.py','database/google_sheet.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['modules.scan_delete_intro_messages','database.threads_db','database.db']]; print('import OK')"
```
Expected: both print OK. (Promotion checkers and `google_sheet` may need credentials to import — if import fails on a credentials/network error rather than a syntax error, `ast.parse` passing is sufficient for those.)

- [ ] **Step 3: Commit**

```bash
git add modules/scan_delete_intro_messages.py modules/promotion_checkers/ database/threads_db.py database/db.py database/google_sheet.py
git commit -m "error visibility: route modules and database except blocks to BOT_LOG"
```

---

## Task 11: Audit `bot.py` + `exception_handler.py` and review central error handlers (8 except blocks)

**Files:**
- Modify: `bot.py` (5 except blocks)
- Modify: `exception_handler.py` (3 except blocks)

- [ ] **Step 1: Audit the `except` blocks**

In `bot.py` and `exception_handler.py`, apply the **Shared Audit Rules** to their `except` blocks (startup/init errors, extension-load errors — all structural, in scope).

- [ ] **Step 2: Review the three central error handlers for command-path noise**

These are error *handlers*, not `except` blocks, but they decide what reaches the channel. Confirm — and adjust if needed — that **routine** command/validation outcomes are logged below WARNING (DEBUG/INFO) or not at all, while genuine/unexpected errors in the fallback branches log at `error`:
- `exception_handler.py:handle_exception` (registered as `on_command_error`) — routine `CommandNotFound` / `BadArgument` / `MissingRequiredArgument` / `CheckFailure` / `CommandOnCooldown` must NOT log at WARNING+. The unrecognised/fallback branch logs at `error`.
- `bot.py:on_app_command_error` — cooldown / missing-perms / check-failure branches must NOT log at WARNING+. The fallback `except Exception` block logs at `error`.
- `cog_command_error` methods (e.g. `cogs/general/__init__.py`) — the cooldown / `CheckFailure` / `MissingRequiredArgument` branches stay quiet; only an unexpected error path logs at `error`.

- [ ] **Step 3: Verify syntax and import**

```bash
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['bot.py','exception_handler.py','cogs/general/__init__.py']]; print('syntax OK')"
python -c "import importlib; [importlib.import_module(m) for m in ['exception_handler','cogs.general']]; print('import OK')"
```
Expected: both print OK. (`bot.py` runs the bot on import-as-main; `ast.parse` passing is the syntax check for it.)

- [ ] **Step 4: Full compile sweep**

```bash
python -m compileall -q bot.py cogs ml_model modules database utils exception_handler.py
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add bot.py exception_handler.py cogs/general/__init__.py
git commit -m "error visibility: route startup except blocks to BOT_LOG; keep command-path noise quiet"
```

---

## Self-Review Notes

- **Spec coverage:** Piece 1 → Task 1. Piece 2 audit → Tasks 2–11 cover all ~33 in-scope files. Scope carve-out (command/validation) → Shared Audit Rules + Task 11 Step 2. Hard carve-outs (`bot_logger.py`, `watchdog.py`) → Shared Audit Rules, and neither appears in any task's file list. Dedup verification → Task 1 Steps 1–5.
- **Sequencing:** Task 1 (Piece 1) before Tasks 2–11 (Piece 2), matching the spec.
- **Loop-hardening files:** the 6 task-loop hardening files are a separate, already-completed commit — not part of this plan.
- **Note on audit granularity:** Piece 2 tasks specify the complete decision procedure (Shared Audit Rules) and the exact files; the specific lines are discovered per file because an audit is inherently discovery-based. The two-stage review in subagent-driven execution catches misapplied fixes.
