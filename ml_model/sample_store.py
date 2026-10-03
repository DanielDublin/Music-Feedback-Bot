"""Locate and remove ML training samples (shared by /samples find and <mf deletedata).

A sample is {message_id, feedback, rating, timestamp}; it has no author, so the author
is resolved by fetching the original message from AUDIO_FEEDBACK. Samples live in two
places: the local feedback_json.json and the JSON batches the bot posted to EXPORTS_CHANNEL.
"""

import asyncio
import io
import json
import logging

import discord

from data.constants import AUDIO_FEEDBACK, EXPORTS_CHANNEL

logger = logging.getLogger(__name__)

LOCAL_SAMPLE_FILE = "feedback_json.json"


def _read_local() -> list[dict]:
    try:
        with open(LOCAL_SAMPLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_local(samples: list[dict]) -> None:
    with open(LOCAL_SAMPLE_FILE, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=4)


async def _export_messages(bot):
    """Yield (message, attachment) for every JSON batch the bot posted to the exports channel."""
    channel = bot.get_channel(EXPORTS_CHANNEL)
    if channel is None:
        logger.warning("Exports channel %s not found", EXPORTS_CHANNEL)
        return
    async for msg in channel.history(limit=None):
        if msg.author.id != bot.user.id:
            continue
        for att in msg.attachments:
            if att.filename.endswith(".json"):
                yield msg, att


async def collect_samples(bot) -> list[dict]:
    """Local file + all export batches, de-duplicated by message_id."""
    samples = await asyncio.to_thread(_read_local)
    async for _, att in _export_messages(bot):
        try:
            samples.extend(json.loads(await att.read()))
        except (json.JSONDecodeError, discord.HTTPException):
            logger.warning("Could not read export attachment %s", att.url, exc_info=True)

    seen, unique = set(), []
    for sample in samples:
        mid = sample.get("message_id")
        if mid is not None and mid not in seen:
            seen.add(mid)
            unique.append(sample)
    return unique


async def find_user_messages(bot, user_id: int, samples: list[dict]):
    """Returns (matches, unresolved): matches is a list of (sample, discord.Message) authored by
    user_id; unresolved counts samples whose original message is gone/unreachable."""
    source = bot.get_channel(AUDIO_FEEDBACK)
    if source is None:
        raise RuntimeError("Audio feedback channel not found")

    gate = asyncio.Semaphore(5)
    matches: list[tuple[dict, discord.Message]] = []
    unresolved = 0

    async def check(sample: dict):
        nonlocal unresolved
        async with gate:
            try:
                message = await source.fetch_message(int(sample["message_id"]))
            except discord.NotFound:
                unresolved += 1
                return
            except discord.HTTPException:
                logger.warning("Could not fetch sample message %s", sample["message_id"], exc_info=True)
                unresolved += 1
                return
        if message.author.id == user_id:
            matches.append((sample, message))

    await asyncio.gather(*(check(s) for s in samples))
    return matches, unresolved


async def remove_samples(bot, message_ids: set[int]) -> int:
    """Remove the given message IDs from the local file and from every export batch.
    Returns how many sample entries were removed. Raises on a failed edit so callers
    can report it instead of claiming success."""
    removed = 0

    local = await asyncio.to_thread(_read_local)
    kept = [s for s in local if s.get("message_id") not in message_ids]
    if len(kept) != len(local):
        await asyncio.to_thread(_write_local, kept)
        removed += len(local) - len(kept)

    async for msg, att in _export_messages(bot):
        try:
            batch = json.loads(await att.read())
        except (json.JSONDecodeError, discord.HTTPException):
            continue
        kept = [s for s in batch if s.get("message_id") not in message_ids]
        if len(kept) == len(batch):
            continue
        removed += len(batch) - len(kept)
        only_attachment = len(msg.attachments) == 1
        if not kept and only_attachment:
            await msg.delete()
            continue
        new_file = discord.File(io.BytesIO(json.dumps(kept, indent=4).encode("utf-8")), filename=att.filename)
        others = [a for a in msg.attachments if a.id != att.id]
        await msg.edit(attachments=others + [new_file])
    return removed
