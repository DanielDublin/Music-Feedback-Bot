import re
import aiohttp
import logging
import urlextract
from bs4 import BeautifulSoup

from modules.promotion_checkers.name_matching import is_match, discord_identity

url_extractor = urlextract.URLExtract()

logger = logging.getLogger(__name__)

_SC_CHANNEL_RE = re.compile(r'https?://(?:www\.)?soundcloud\.com/([A-Za-z0-9_-]+)')
_SC_SONG_RE = re.compile(r'https?://soundcloud\.com/[\w-]+/([\w-]+)')


def extract_soundcloud_url(message_content: str) -> list[str]:
    return [u for u in url_extractor.find_urls(message_content) if 'soundcloud' in u]


async def expand_soundcloud_url(short_url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(short_url, allow_redirects=True, timeout=10) as response:
                if response.status != 200:
                    return None
                full_url = str(response.url)
                if _SC_CHANNEL_RE.match(full_url):
                    return full_url
                return None
    except Exception:
        logger.error("Error expanding SoundCloud URL", exc_info=True)
        return None


def extract_soundcloud_channel_name(expanded_url: str):
    m = _SC_CHANNEL_RE.match(expanded_url)
    return m.group(1) if m else None


def extract_soundcloud_song_name(expanded_url: str):
    m = _SC_SONG_RE.match(expanded_url)
    return m.group(1) if m else None


async def fetch_soundcloud_display_name(expanded_url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(expanded_url, timeout=10) as response:
                if response.status != 200:
                    return None
                html = await response.text()
    except Exception:
        logger.error("Error fetching SoundCloud page", exc_info=True)
        return None

    soup = BeautifulSoup(html, 'html.parser')
    title_element = soup.select_one('title')
    if not title_element:
        return None
    title_content = title_element.text

    song_name = extract_soundcloud_song_name(expanded_url)
    if song_name is not None:
        m = re.search(r'by (.*?) \|', title_content)
    else:
        m = re.search(r'Stream (.+?) music \|', title_content)
    return m.group(1) if m else None


async def check_soundcloud(message) -> bool:
    short_urls = extract_soundcloud_url(message.content)
    if not short_urls:
        return False

    discord_names = discord_identity(message.author)
    for url in short_urls:
        expanded_url = await expand_soundcloud_url(url)
        if expanded_url is None:
            logger.warning("Error while expanding URL from SoundCloud")
            continue

        slug = extract_soundcloud_channel_name(expanded_url)
        display = await fetch_soundcloud_display_name(expanded_url)
        candidates = [c for c in (slug, display) if c]
        if not candidates:
            logger.warning("No SoundCloud name candidates from %s", expanded_url)
            continue

        if is_match(candidates, discord_names):
            return True

    return False
