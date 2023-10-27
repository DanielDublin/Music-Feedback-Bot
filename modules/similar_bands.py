import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup


load_dotenv()
api_key = os.environ.get('LAST_FM_TOKEN')


async def get_image(data):
    artist_info = data.get('artist', {})
    artist_url = artist_info.get('url')
            
    if artist_url:
        # Make a request to the artist's Last.fm page
        async with aiohttp.ClientSession() as session:
            async with session.get(artist_url) as artist_page_response:
                if artist_page_response.status != 200:
                    return None  # Failed to retrieve artist page

                # Parse the HTML of the artist's page
                artist_page_html = await artist_page_response.text()
                soup = BeautifulSoup(artist_page_html, 'html.parser')

                # Find the 'meta' tag with 'property' attribute set to 'og:image'
                meta_tag = soup.find('meta', {'property': 'og:image'})

                if meta_tag and meta_tag.get('content'):
                    # Extract the content attribute as the image URL
                    image_url = meta_tag['content']
                    return image_url
    return 'https://lastfm.freetls.fastly.net/i/u/avatar170s/4128a6eb29f94943c9d206c08e625904.jpg'
                    

async def fetch_similar_bands(artist_name):
    global api_key
    base_url = 'http://ws.audioscrobbler.com/2.0/'

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

            if similar_artists:
                similar_bands = [
                f"{i + 1}. [{artist['name']}]({artist['url']}) - {(float(artist['match'])*100):0.2f}% Match\n"
                for i, artist in enumerate(similar_artists[:10])]

                return "".join(similar_bands)
            else:
                return "No similar bands found"
         

