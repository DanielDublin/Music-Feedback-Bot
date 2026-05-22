# Except-Block Reporting to BOT_LOG — Design

**Date:** 2026-05-22
**Status:** Approved (design)

## Goal

Every meaningful caught exception in the project surfaces in the `BOT_LOG`
Discord channel (`1462921563329532026`), with duplicate-suppression so that
errors in hot paths (per-message handlers, loop iterations) cannot flood the
channel or burn Discord API rate limits.

## Current State

- `utils/bot_logger.py:DiscordChannelHandler` is attached to the **root**
  logger at `WARNING` level (`bot.py:main()`), forwarding every WARNING+
  record to `BOT_LOG`, chunked to fit Discord's 2000-char limit.
- An `except` block that calls `logger.error(...)` or `logger.warning(...)`
  therefore **already** reaches the channel.
- An `except` block that does `pass`, logs at `debug`/`info`, or `print()`s
  does **not** reach the channel — it fails silently as far as Discord is
  concerned.
- There are ~206 `except` blocks across ~33 project files (excluding `venv/`).

There is no Python hook for *caught* exceptions (`sys.excepthook` fires only
for *uncaught* ones), so coverage requires touching except blocks directly.

## Approach

**Approach A — "every in-scope except logs at ≥ WARNING".** Leverage the
existing logging pipeline: the rule is that every in-scope `except` block
must emit a record at `warning` or `error`, which the existing handler then
routes to the channel. No new logging API, no secondary framework. Only
non-compliant blocks change; the many that already use `logger.error` are
left untouched.

Rejected alternatives: a dedicated `report_exception()` helper (adds an API
to thread through every site for no gain over the existing pipeline);
lowering the handler threshold to DEBUG (floods the channel with all
debug/info logs bot-wide and still does not fix `except: pass`).

## Piece 1 — Dedup / Rate-Limit in `DiscordChannelHandler`

Add an in-memory dedup cache local to the handler (`utils/bot_logger.py`).

- **Key:** `(record.name, record.levelno, record.getMessage())` — stable
  across timestamps and traceback text.
- **Sliding 60-second window:**
  - First occurrence of a key, or first after >60s of quiet: send
    immediately. If a suppressed count `N` is pending for that key, append
    `\n(+N duplicate(s) suppressed in the last 60s)` — **only when N > 0**.
  - Repeat within 60s: increment the suppressed count, refresh the
    last-seen timestamp (sliding), and do **not** send.
- **Thread safety:** a `threading.Lock` guards the cache bookkeeping —
  `logging` can be called from `asyncio.to_thread` worker threads.
- **Bounded memory:** cap the cache at 256 keys; when exceeded, drop the
  oldest entries by last-seen timestamp.
- **No background flush timer:** an error storm that simply stops will not
  emit its trailing summary count. Accepted (YAGNI) — the first occurrence
  has already alerted; only the final tally is lost.
- **Recursion safety unchanged:** the handler's own `_send` failure path
  still `print()`s to stderr and never logs.

## Piece 2 — Except-Block Audit (~33 files)

For every in-scope `except` block, apply the smallest fix that gets a
WARNING+ record emitted:

| Current form | Fix |
|---|---|
| `except X: pass` | add `logger.error("<context>", exc_info=True)` (or `logger.warning` if benign-but-notable) |
| `except X:` logging at `debug`/`info` | bump the level to `warning` or `error` |
| `except X: print(...)` | `logger.error(..., exc_info=True)` (also satisfies the CLAUDE.md no-`print()` rule) |
| already `logger.warning` / `logger.error` | unchanged |

- Files lacking a module logger get the standard
  `logger = logging.getLogger(__name__)`.
- **Severity guide:** structural / network / database / data-access /
  filesystem / logic failures → `error` with `exc_info=True`. Recoverable
  or expected-but-notable conditions → `warning`.
- Exception *handling* behavior is unchanged — every block still catches and
  recovers exactly as before; only the log emission changes.

## Scope — In vs Out

**In scope:** structural, network, database, data-access, filesystem/JSON,
and logic `except` blocks (e.g. the attribute-access cleanup in
`ml_model/feedback_monitor.py`).

**Out of scope (kept quiet — leave as-is or log at DEBUG):** `except`
blocks catching routine user-input / command-validation exceptions —
`commands.CommandNotFound`, `commands.BadArgument`, `commands.CheckFailure`,
`commands.MissingRequiredArgument`, `commands.CommandOnCooldown`, and
equivalent custom "expected user error" cases. These are routine user
interaction, not system failures, and would be pure channel noise.

**Central error handlers:** `exception_handler.py:handle_exception`,
`bot.py:on_app_command_error`, and the cogs' `cog_command_error` methods are
each reviewed once to confirm routine command/validation outcomes are not
logged at WARNING+ (DEBUG/INFO instead), while genuine or unexpected errors
in their fallback branches are. (These are error handlers, not `except`
blocks, but they are where command-path noise would otherwise originate.)

## Hard Carve-Outs (must NOT route to the channel)

- **`utils/bot_logger.py`** — its own `except` blocks stay `print`-to-stderr.
  Logging from inside the log handler risks infinite recursion.
- **`watchdog.py`** — a separate supervising process with no Discord
  connection; its `except` block stays as-is.

## Non-Goals

- No new logging API or secondary reporting framework.
- No change to how exceptions are *handled* or recovered from.
- No background flush timer for trailing dedup counts.
- No change to the handler's WARNING threshold.

## Verification

This project has no automated test suite (per CLAUDE.md). Verification:

- **Piece 1:** a focused self-check — feed `DiscordChannelHandler` synthetic
  `LogRecord`s and assert the send/suppress decisions and the `+N` suffix
  (first send, suppressed repeat, post-window flush, N>0 only).
- **Piece 2:** per touched file, `ast.parse` / `py_compile` plus an import
  test; confirm every modified `except` block now emits WARNING+.
- **Overall:** import-test the affected cogs/modules so cog loading is not
  broken.

## Sequencing

1. **Piece 1** first — contained, single file (`utils/bot_logger.py`).
2. **Piece 2** next — grouped by area/file, reviewable in batches.

The 6 already-completed task-loop hardening files are committed as their own
separate commit (complete and verified independently), not folded into this
change. All of it ships on the same branch.
