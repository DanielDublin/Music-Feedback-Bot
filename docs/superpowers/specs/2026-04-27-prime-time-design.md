# Prime Time — Design Spec
**Date:** 2026-04-27

## Summary
A timed double-points event for `<MFR`. An admin starts it with `/mf primetime start [minutes]` (default 60). During the event, quality feedback (≥300 chars) earns 2 pts instead of 1. Deleting a qualifying MFR during the event removes 2 pts. The event ends automatically via background timer or manually via `/mf primetime stop`. Announcement images are posted to three channels on start and end.

---

## State (on the PrimeTime cog)

```python
_active: bool
_start_time: datetime | None   # UTC-aware
_duration: int                  # minutes
_timer_task: asyncio.Task | None
```

- No `end_time` stored — derived as `_start_time + timedelta(minutes=_duration)` when needed
- No message ID set — re-derived on delete from `message.created_at` + `message.content`
- Background `asyncio.Task` sleeps for the full duration then calls `_end_prime_time()`
- Manual stop cancels the task then calls `_end_prime_time()`

---

## Public interface (used by other cogs)

```python
def is_active(self) -> bool
def was_during_prime_time(self, created_at: datetime) -> bool
def time_remaining(self) -> int | None  # seconds, None if inactive
```

---

## Commands — `/mf primetime`

Group: `mf` › Subgroup: `primetime` › Commands: `start`, `stop`, `status`
All require `administrator` permission.

| Command | Parameters | Behaviour |
|---------|-----------|-----------|
| `start` | `minutes: int = 60` | Rejects if already active. Posts start image + text to 3 channels. Starts timer task. |
| `stop`  | — | Rejects if not active. Cancels timer. Posts end image to 3 channels. |
| `status`| — | Ephemeral reply: active/inactive + seconds remaining. |

### Announcement channels
- `GENERAL_CHAT_CHANNEL_ID`
- `AUDIO_FEEDBACK`
- `LYRIC_FEEDBACK`

### Start message
File: `data/assets/prime_time_start.gif`
Text:
```
# PRIME TIME
2x the MF points for the next hour .... *STARTING NOW!!!*

Simply use <MFR in the feedback channels to get 2 points for every feedback given.
Each feedback submission is still 1 point with <MFS.

Feedback __must be quality__ and greater than 300 characters!
Check your available <MF points in <#799751702529572876>.
```

### End message
File: `data/assets/prime_time_end.png`
No additional text.

---

## MFR point logic changes (`cogs/general.py`)

```
if prime_time active AND len(feedback_text) >= 300:
    award 2 pts
    notify: "gained 2 MF points (Prime Time bonus)"
else:
    award 1 pt (unchanged)
    if prime_time active AND len(feedback_text) < 300:
        send quiet notice: feedback too short for double points
```

`feedback_text` = `message.content` with `<MFR` prefix stripped.

---

## MFR delete logic changes (`points_logic.py`)

```
prime_time_cog = bot.get_cog("PrimeTime")
if prime_time_cog and prime_time_cog.was_during_prime_time(message.created_at):
    feedback_text = strip_mfr_prefix(message.content)
    points_to_remove = 2 if len(feedback_text) >= 300 else 1
else:
    points_to_remove = 1  # unchanged

if message.content is empty (uncached): default to 1 pt
```

---

## Images

| Source | Destination |
|--------|-------------|
| `C:\Users\Daniel\Downloads\starting gif.gif` | `data/assets/prime_time_start.gif` |
| `C:\Users\Daniel\Downloads\PRIME TIME IS OVER.png` | `data/assets/prime_time_end.png` |

---

## Files changed

| File | Type |
|------|------|
| `cogs/slash_commands/prime_time.py` | New |
| `data/assets/prime_time_start.gif` | New (moved) |
| `data/assets/prime_time_end.png` | New (moved) |
| `cogs/general.py` | Modified — MFR double pts + 300 char check |
| `cogs/feedback_threads/modules/points_logic.py` | Modified — MFR_delete 2-pt removal |
| `bot.py` | Modified — register cog |

---

## Out of scope
- Persisting prime time state across restarts (event is live, short-duration)
- Double points for MFS
- Any changes to the ML quality model
