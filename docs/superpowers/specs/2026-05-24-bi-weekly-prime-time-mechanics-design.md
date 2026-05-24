# Bi-Weekly Prime Time — Laxer Mechanics + Admin Edits

**Date:** 2026-05-24
**Scope:** `cogs/slash_commands/prime_time.py` and `data/prime_time_state.json`

## Motivation

The current Saturday auto-trigger only counts quality `<MFR`s on a single UTC Saturday and demands 50 in 24 hours. In practice it rarely fires. We want a laxer accumulation model that gathers progress across the whole 14-day window, plus admin-side knobs for tuning and a daily-trigger threshold that's easier to hit.

## Mechanics Changes

### Bi-weekly auto-trigger (replaces Saturday)

- **Day restriction removed.** Quality `<MFR` increments the counter regardless of weekday.
- **Window:** 14 days from `bi_weekly_window_start_ts`. Counter is `bi_weekly_count`.
- **Fire condition:** `bi_weekly_count >= bi_weekly_goal` (default 50). Fires a 4-hour (240-min) Prime Time. On fire, `bi_weekly_count` resets to 0 and `bi_weekly_window_start_ts` is stamped to `now`.
- **Window expiration:** If `now - bi_weekly_window_start_ts >= 14 days` and the counter hasn't fired, reset count to 0 and stamp a new window-start.
- **Cooldown removed.** The window reset on fire already enforces ~14-day minimum spacing between fires; a separate cooldown timer is redundant.

### Daily auto-trigger

- **Threshold:** `_DAILY_GOAL` changes from **10 → 5** quality `<MFR`s in the trailing 60 minutes.
- **Rolling window (60 min) unchanged.**
- **24h cooldown unchanged.**
- **Cross-kind extension rule unchanged** (Daily during active Bi-weekly, or vice versa, extends the active event).

## State Persistence

### File: `data/prime_time_state.json`

Schema additions/renames:

| Field | Type | Default | Notes |
|---|---|---|---|
| `daily_goal` | int | 5 | Editable via slash command. |
| `bi_weekly_goal` | int | 50 | Editable via slash command. |
| `daily_rolling_ts` | list[float] | `[]` | Epoch timestamps for entries currently in the 60-min rolling deque. Persisted on every change. |
| `bi_weekly_count` | int | 0 | Renamed from `saturday_count`. |
| `bi_weekly_window_start_ts` | float \| null | null | Renamed from `saturday_window_start_ts`. |
| `last_bi_weekly_nudge_stage` | int | 0 | Renamed from `last_saturday_nudge_stage`. |
| `bi_weekly_progress_message_id` | int \| null | null | Renamed from `saturday_progress_message_id`. |
| `bi_weekly_progress_channel_id` | int \| null | null | Renamed from `saturday_progress_channel_id`. |
| `bi_weekly_fire_count` | int | 0 | Renamed from `saturday_fire_count`. |
| `last_bi_weekly_auto_trigger_ts` | float \| null | null | Renamed from `last_saturday_auto_trigger_ts`. Kept for stats only; no longer used as a cooldown gate. |

Removed fields: none — every Saturday-named field gets renamed, no field is dropped, so the JSON keeps the same shape. The `last_saturday_auto_trigger_ts` field becomes purely informational (last-fire timestamp surfaced by `/primetime stats` and `/primetime status`).

### Migration

One-time silent migration inside `_load_auto_state`:

1. **Key rename:** For each pair below, if the old key is present and the new key is missing, copy old → new:
   - `saturday_count` → `bi_weekly_count`
   - `saturday_window_start_ts` → `bi_weekly_window_start_ts`
   - `last_saturday_nudge_stage` → `last_bi_weekly_nudge_stage`
   - `saturday_progress_message_id` → `bi_weekly_progress_message_id`
   - `saturday_progress_channel_id` → `bi_weekly_progress_channel_id`
   - `saturday_fire_count` → `bi_weekly_fire_count`
   - `last_saturday_auto_trigger_ts` → `last_bi_weekly_auto_trigger_ts`
2. **Active-event value rename:** If `active_kind == "saturday"`, rewrite it to `"biweekly"`. This matters when the upgrade happens during a Saturday-fired event so resume logic and `_evaluate_*` cross-kind checks find the right value.
3. Old keys are not preserved in memory. `_save_auto_state` always writes the full new schema, so the next save overwrites the file with new keys only.

## Restart Behavior

On bot start (`_load_auto_state` + an explicit reconciliation pass that runs immediately after load):

1. **Daily rolling deque:** Read `daily_rolling_ts`. Drop entries older than `now - 60 min`. Rebuild the in-memory deque from the survivors. Save the pruned list back if anything was dropped.
2. **Bi-weekly window check:** If `bi_weekly_window_start_ts` is null, leave as-is (first MFR will stamp it). If it's set and `now - bi_weekly_window_start_ts >= 14 days`, reset `bi_weekly_count` to 0 and stamp `bi_weekly_window_start_ts = now`, clear `last_bi_weekly_nudge_stage`, and clear the persisted progress message (delete on Discord if findable, then null both `_message_id` and `_channel_id`).
3. **Active-event resume** (existing behavior) runs as today.

## Slash Commands

Added to the existing `primetime` group (admin-only, same `default_permissions`):

### `/primetime set_goal <kind> <value>`

- `kind`: Choice — `daily` | `biweekly`
- `value`: int. Refuse if `value <= 0` or `value > 1000` with an ephemeral error.
- Writes the new goal to `_auto_state` and saves.
- Responds ephemerally: `✅ Daily goal set to N` / `✅ Bi-weekly goal set to N`.

### `/primetime set_count <kind> <value>`

- `kind`: Choice — `daily` | `biweekly`
- `value`: int. Refuse if `value < 0` or `value > 1000`.
- **Daily:** clears `_recent_feedbacks` and re-populates it with `value` timestamps all stamped at `now`. (Quirk: they'll all expire from the deque ~60 min later as a block. Documented in command response.)
- **Bi-weekly:** sets `bi_weekly_count = value`. If `value == 0`, also stamps a fresh `bi_weekly_window_start_ts = now` and clears `last_bi_weekly_nudge_stage`. If `value > 0`, the window is unchanged.
- After set, recomputes `_last_nudge_stage` / `last_bi_weekly_nudge_stage` to `max(stage for stage in <stages> if stage <= value, default=0)` so future nudges fire correctly relative to the new count.
- **Does not auto-fire** even if `value >= goal`. The next quality `<MFR` will trigger the fire check normally. (Admins can still use `/primetime force_fire` for an immediate fire.)
- Saves state. Responds ephemerally with the new value plus the post-edit window-start (for biweekly).

### Existing commands updated

- `/primetime status` — rework the bi-weekly section. Drops the "today is/isn't Saturday" branching. Shows:
  - `bi_weekly_count / bi_weekly_goal`
  - Window start (`bi_weekly_window_start_ts` as `<t:...:F>`)
  - Window expires (`window_start + 14 days` as `<t:...:R>`)
  - Last fire (info only; no cooldown line since there's no cooldown)
  - For daily: counter shown against the new editable `daily_goal` instead of the hardcoded constant.
- `/primetime reset_counter` — `kind` choices stay `daily | biweekly | both`. Bi-weekly reset also stamps fresh `bi_weekly_window_start_ts`.
- `/primetime reset_cooldown` — remove the `saturday` and `both` choices' bi-weekly handling (no cooldown to clear). Either: (a) keep the command as daily-only, or (b) keep `biweekly` choice but make it a no-op with a "no cooldown to clear" response. **Decision: option (a)** — strip bi-weekly out of `reset_cooldown` entirely.
- `/primetime stats` — show `bi_weekly_fire_count` instead of `saturday_fire_count`. Labels updated.
- `/primetime force_fire` — `biweekly` choice updates to use `bi_weekly_*` state. No day-check.

## Festival Theme Rewrite

Keep the show/festival vocabulary (headliner, stage, tickets, encore, soundcheck). Remove Saturday-specific words and "today's" qualifier. The nudge copy and announcement strings get rewritten:

- `_SATURDAY_NUDGES` → `_BI_WEEKLY_NUDGES`. Same stage keys (10, 25, 40, 49), same 4-message pool per stage, festival-themed but framed around "the bi-weekly headliner" / "the bi-weekly show" with no day reference.
- Live progress message text (`_build_saturday_progress_text` → `_build_bi_weekly_progress_text`): same bar visual, drop "today" wording.
- Fire announcement (`_fire_auto` `kind == "saturday"` → `"biweekly"`): drop "today's Saturday window" / "Saturday-UTC" mentions, keep "bi-weekly headliner" framing. The "next eligible bi-weekly window" line is dropped (no cooldown → no fixed next-eligible date; the user can read the new window start from `/primetime status`).

Daily nudge stages (3, 5, 7, 9) need a rework now that goal is 5. **New stages: (2, 3, 4)**. Existing `_NUDGES` dict gets pruned to those keys (4 messages per stage, kept on theme).

If goal is changed via `/primetime set_goal`, the hardcoded nudge stages do not scale. This is an acknowledged limitation — for an MVP, the default values (daily=5, biweekly=50) are what the stages are designed for, and changing the goal is admin-only / occasional. Documented in the `/primetime set_goal` response.

## Internal Renames

| Old | New |
|---|---|
| `_SATURDAY_GOAL` | `_DEFAULT_BI_WEEKLY_GOAL` (state-driven now; constant becomes the default) |
| `_SATURDAY_DURATION_MINUTES` | `_BI_WEEKLY_DURATION_MINUTES` |
| `_SATURDAY_NUDGE_STAGES` | `_BI_WEEKLY_NUDGE_STAGES` |
| `_SATURDAY_NUDGES` | `_BI_WEEKLY_NUDGES` |
| `_saturday_window_start` | removed (no day check) |
| `_next_saturday_window_start` | removed |
| `_record_saturday` | `_record_bi_weekly` |
| `_evaluate_saturday` | `_evaluate_bi_weekly` |
| `_post_saturday_progress` | `_post_bi_weekly_progress` |
| `_sync_saturday_progress_message` | `_sync_bi_weekly_progress_message` |
| `_clear_saturday_progress_message` | `_clear_bi_weekly_progress_message` |
| `_build_saturday_progress_text` | `_build_bi_weekly_progress_text` |
| `_active_kind == "saturday"` | `_active_kind == "biweekly"` |

`_DEFAULT_DAILY_GOAL = 5` replaces the old `_DAILY_GOAL = 10`. The runtime goal is read from `_auto_state["daily_goal"]` everywhere it's needed. Same pattern for bi-weekly.

## Out of Scope

- Public-facing progress command — explicitly deferred. Existing admin `/primetime status` is the only status surface.
- Auto-scaling nudge stages to match edited goals.
- Lyric feedback counting toward goals (still audio-only via `feedback_monitor`).
- Changing the daily 24h cooldown or daily duration (60 min).
- Changing the bi-weekly duration (240 min / 4h).
- Changing the cross-kind extension rule.

## Files Touched

- `cogs/slash_commands/prime_time.py` — all mechanics, slash commands, renames, theme copy.
- `data/prime_time_state.json` — schema migration on next save (handled by code, not edited manually).
- `CLAUDE.md` — update the "Prime Time" section to describe the new mechanics, removed cooldown, new threshold (5), persistence, and new commands.
