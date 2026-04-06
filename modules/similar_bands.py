import aiohttp
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup


load_dotenv()
api_key = os.environ.get('LAST_FM_TOKEN')


async def _get_image(artist_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(artist_url) as response:
            if response.status != 200:
                return None
            soup = BeautifulSoup(await response.text(), 'html.parser')
            meta_tag = soup.find('meta', {'property': 'og:image'})
            if meta_tag and meta_tag.get('content'):
                return meta_tag['content']
    return None


async def fetch_similar_bands(artist_name):
    base_url = 'http://ws.audioscrobbler.com/2.0/'
    default_image = 'https://lastfm.freetls.fastly.net/i/u/avatar170s/4128a6eb29f94943c9d206c08e625904.jpg'

    params = {
        'method': 'artist.getsimilar',
        'artist': artist_name,
        'api_key': api_key,
        'format': 'json'
    }

    async with aiohttp.ClientSession() as session:
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

    # Fetch artist image from getinfo
    info_params = {
        'method': 'artist.getinfo',
        'artist': artist_name,
        'api_key': api_key,
        'format': 'json'
    }
    image_url = default_image
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=info_params) as response:
            if response.status == 200:
                info_data = await response.json()
                artist_url = info_data.get('artist', {}).get('url')
                if artist_url:
                    image_url = await _get_image(artist_url) or default_image

    return (result, image_url)
