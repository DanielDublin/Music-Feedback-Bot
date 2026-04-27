import aiohttp
import os
from urllib.parse import quote
from dotenv import load_dotenv


load_dotenv()
api_key = os.environ.get('LAST_FM_TOKEN')

_session: "aiohttp.ClientSession | None" = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def _get_image(artist_name: str) -> str | None:
    url = f"https://api.deezer.com/search/artist?q={quote(artist_name)}&limit=1"
    session = await _get_session()
    async with session.get(url) as response:
        if response.status != 200:
            return None
        data = await response.json(content_type=None)
        artists = data.get('data', [])
        if artists:
            return artists[0].get('picture_xl') or artists[0].get('picture_big')
    return None


async def fetch_similar_bands(artist_name):
    base_url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'artist.getsimilar',
        'artist': artist_name,
        'api_key': api_key,
        'format': 'json'
    }

    session = await _get_session()
    async with session.get(base_url, params=params) as response:
        if response.status != 200:
            return (f"Error: Failed to retrieve data (HTTP status {response.status})", None)
        data = await response.json()

    if 'error' in data:
        return (f"Error: {data['message']}", None)

    similar_artists = data['similarartists']['artist']

    if not similar_artists:
        return ("No similar bands found.", None)

    result = "".join(
        f"{i + 1}. [{artist['name']}]({artist['url']}) - {float(artist['match']) * 100:.2f}% Match\n"
        for i, artist in enumerate(similar_artists[:10])
    )

    image_url = await _get_image(artist_name)
    return (result, image_url)
