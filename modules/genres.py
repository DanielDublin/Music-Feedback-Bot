import aiohttp
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup


load_dotenv()
api_key = os.environ.get('LAST_FM_TOKEN')

_session: "aiohttp.ClientSession | None" = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def _get_image(data):
    artist_url = data.get('artist', {}).get('url')
    if not artist_url:
        return None
    session = await _get_session()
    async with session.get(artist_url) as response:
        if response.status != 200:
            return None
        soup = BeautifulSoup(await response.text(), 'html.parser')
        meta_tag = soup.find('meta', {'property': 'og:image'})
        if meta_tag and meta_tag.get('content'):
            return meta_tag['content']
    return None


async def fetch_band_genres(band_name):
    default_image = 'https://lastfm.freetls.fastly.net/i/u/avatar170s/4128a6eb29f94943c9d206c08e625904.jpg'
    base_url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'artist.getinfo',
        'artist': band_name,
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

    tags = data.get('artist', {}).get('tags', {}).get('tag', [])
    if tags:
        genres = ", ".join(tag['name'] for tag in tags).title()
    else:
        genres = "No genre information available."

    image_url = await _get_image(data) or default_image
    return (genres, image_url)
