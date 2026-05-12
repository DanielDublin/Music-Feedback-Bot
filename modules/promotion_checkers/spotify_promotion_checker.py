import re
import asyncio
import logging
import os
import urlextract
import spotipy
from cachetools import TTLCache
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

from modules.promotion_checkers.name_matching import is_match, discord_identity

load_dotenv()

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

url_extractor = urlextract.URLExtract()
sp = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    )
)

logger = logging.getLogger(__name__)

# Cache resolved (artists, title) tuples by (link_type, link_id) for an hour.
_spotify_cache: TTLCache = TTLCache(maxsize=1024, ttl=3600)

_SPOTIFY_LINK_RE = re.compile(r'https?://open\.spotify\.com/(track|album|artist)/(\w+)')


def extract_spotify_urls(message_content: str) -> list[str]:
    return [u for u in url_extractor.find_urls(message_content) if 'spotify' in u]


def fetch_spotify_info(spotify_url: str):
    """Return (artist_names, title) for the link, or None on failure.
    title is empty string for artist links."""
    match = _SPOTIFY_LINK_RE.match(spotify_url)
    if not match:
        return None
    link_type, link_id = match.groups()
    cache_key = (link_type, link_id)
    if cache_key in _spotify_cache:
        return _spotify_cache[cache_key]

    try:
        if link_type == 'track':
            info = sp.track(link_id)
            result = ([a['name'] for a in info['artists']], info.get('name', ''))
        elif link_type == 'album':
            info = sp.album(link_id)
            result = ([a['name'] for a in info['artists']], info.get('name', ''))
        elif link_type == 'artist':
            info = sp.artist(link_id)
            result = ([info['name']], '')
        else:
            return None
    except spotipy.SpotifyException:
        logger.warning("Error processing Spotify link: %s", spotify_url)
        return None

    _spotify_cache[cache_key] = result
    return result


async def check_spotify(message) -> bool:
    urls = extract_spotify_urls(message.content)
    if not urls:
        return False

    discord_names = discord_identity(message.author)
    for url in urls:
        info = await asyncio.to_thread(fetch_spotify_info, url)
        if info is None:
            continue
        artists, title = info
        candidates = list(artists)
        if title:
            candidates.append(title)
        if is_match(candidates, discord_names):
            return True

    return False
