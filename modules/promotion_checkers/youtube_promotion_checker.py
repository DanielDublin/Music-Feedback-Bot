import re
import os
import logging
import aiohttp
import urlextract
from cachetools import TTLCache
from dotenv import load_dotenv

from modules.promotion_checkers.name_matching import is_match, discord_identity

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_TOKEN')

logger = logging.getLogger(__name__)

YT_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
YT_CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"

# Cache video/channel metadata for an hour to save quota and latency on
# reposts. Race conditions just cost an extra API call -- no correctness issue.
_video_cache: TTLCache = TTLCache(maxsize=1024, ttl=3600)
_channel_cache: TTLCache = TTLCache(maxsize=1024, ttl=3600)

url_extractor = urlextract.URLExtract()

# YouTube URL patterns. Channel handles (@foo) are matched separately so we
# can hit channels.list?forHandle instead of videos.list.
_video_patterns = [
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)'),
    re.compile(r'(?:https?://)?youtu\.be/([A-Za-z0-9_-]+)'),
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]+)'),
]
_channel_pattern = re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(@[A-Za-z0-9_.\-]+)')


def extract_youtube_video_ids(content: str) -> list[str]:
    ids = []
    for url in url_extractor.find_urls(content):
        for pat in _video_patterns:
            m = pat.search(url)
            if m:
                ids.append(m.group(1))
                break
    return ids


def extract_youtube_channel_handles(content: str) -> list[str]:
    handles = []
    for url in url_extractor.find_urls(content):
        m = _channel_pattern.search(url)
        if m:
            handles.append(m.group(1))
    return handles


async def _fetch_video_info(session: aiohttp.ClientSession, video_id: str):
    """Return (channel_title, video_title) or None."""
    if video_id in _video_cache:
        return _video_cache[video_id]
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_TOKEN not configured; cannot fetch video info")
        return None
    params = {"part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY}
    try:
        async with session.get(YT_VIDEOS_ENDPOINT, params=params, timeout=10) as resp:
            if resp.status != 200:
                logger.warning(
                    "YouTube videos.list returned %d for %s", resp.status, video_id,
                )
                return None
            data = await resp.json()
    except Exception:
        logger.error("Error calling YouTube videos.list", exc_info=True)
        return None
    items = data.get("items", [])
    if not items:
        return None
    snippet = items[0].get("snippet", {})
    result = (snippet.get("channelTitle", ""), snippet.get("title", ""))
    _video_cache[video_id] = result
    return result


async def _fetch_channel_title(session: aiohttp.ClientSession, handle: str):
    """Return channel display title for an @handle, or None."""
    if handle in _channel_cache:
        return _channel_cache[handle]
    if not YOUTUBE_API_KEY:
        return None
    params = {"part": "snippet", "forHandle": handle, "key": YOUTUBE_API_KEY}
    try:
        async with session.get(YT_CHANNELS_ENDPOINT, params=params, timeout=10) as resp:
            if resp.status != 200:
                logger.warning(
                    "YouTube channels.list returned %d for %s", resp.status, handle,
                )
                return None
            data = await resp.json()
    except Exception:
        logger.error("Error calling YouTube channels.list", exc_info=True)
        return None
    items = data.get("items", [])
    if not items:
        return None
    title = items[0].get("snippet", {}).get("title", "")
    _channel_cache[handle] = title
    return title


async def check_youtube(message) -> bool:
    content = message.content
    video_ids = extract_youtube_video_ids(content)
    handles = extract_youtube_channel_handles(content)
    if not video_ids and not handles:
        return False

    discord_names = discord_identity(message.author)
    async with aiohttp.ClientSession() as session:
        for vid in video_ids:
            info = await _fetch_video_info(session, vid)
            if info is None:
                continue
            channel_title, video_title = info
            if is_match([channel_title, video_title], discord_names):
                return True

        for handle in handles:
            # Always include the bare handle text as a cheap fallback in case
            # the API lookup fails (or the channel was renamed away from it).
            candidates = [handle.lstrip("@")]
            title = await _fetch_channel_title(session, handle)
            if title:
                candidates.append(title)
            if is_match(candidates, discord_names):
                return True

    return False
