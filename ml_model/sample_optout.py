"""Opt-out list for ML training-sample collection.

Users on this list still get their <MFR feedback scored by the quality model
(that is moderation), but their text is never written to feedback_json.json.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

OPTOUT_FILE = Path(__file__).resolve().parent.parent / "data" / "feedback_optout.json"

_optout: set[int] | None = None


def _load() -> set[int]:
    global _optout
    if _optout is None:
        try:
            with OPTOUT_FILE.open("r", encoding="utf-8") as f:
                _optout = {int(x) for x in json.load(f)}
        except FileNotFoundError:
            _optout = set()
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.error("Invalid %s; treating as empty", OPTOUT_FILE, exc_info=True)
            _optout = set()
    return _optout


def _save(ids: set[int]) -> None:
    OPTOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = OPTOUT_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)
    os.replace(tmp, OPTOUT_FILE)


def is_opted_out(user_id: int) -> bool:
    return user_id in _load()


def is_opted_out_on_disk(user_id: int) -> bool:
    """Re-read the file (not the in-memory set) to prove a change was persisted."""
    try:
        with OPTOUT_FILE.open("r", encoding="utf-8") as f:
            return user_id in {int(x) for x in json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
        return False


def opted_out_count() -> int:
    return len(_load())


def set_opt_out(user_id: int, opted_out: bool) -> bool:
    """Returns True if the stored state changed."""
    ids = _load()
    if opted_out == (user_id in ids):
        return False
    if opted_out:
        ids.add(user_id)
    else:
        ids.discard(user_id)
    _save(ids)
    logger.info("Sample opt-out for %s set to %s", user_id, opted_out)
    return True
