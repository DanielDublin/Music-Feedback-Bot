import re
import discord
import urlextract
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

# Initialize the URL extractor 
url_extractor = urlextract.URLExtract()
# Create a Spotify client
sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

def extract_spotify_urls(message_content):
    # Function to extract URLs from text
    out_links = []
    urls = list(url_extractor.find_urls(message_content))
    for url in urls:
        if 'spotify' in url:
            out_links.append(url)
    return out_links


def fetch_artist_name(spotify_url):
    global sp
    
    try:
        # Extract the type and ID from the Spotify link using regex
        match = re.match(r'https://open\.spotify\.com/(track|album|artist)/(\w+)', spotify_url)
        
        if match:
            link_type, link_id = match.groups()

            # Fetch information based on the link type
            if link_type == 'track':
                link_info = sp.track(link_id)
            elif link_type == 'album':
                link_info = sp.album(link_id)
            elif link_type == 'artist':
                link_info = sp.artist(link_id)
                artist_name = [link_info['name']]
                return artist_name
            
            else:
                return None

            # Extract the artist name
            artists = link_info['artists']
            artist_names = [artist['name'] for artist in artists]
            return artist_names
            
    except spotipy.SpotifyException:
        print(f"Error processing Spotify link: {spotify_url}")
        return None



async def check_spotify(message):
    content = message.content

    urls = extract_spotify_urls(content)
    if urls is None:
        return False

    author = message.author
    
    for url in urls:
       
        
        spotify_artists_names = fetch_artist_name(url)
        if spotify_artists_names is None:
            continue
        
        
        spotify_artists_names = [artist_name.replace(" ", "").lower() for artist_name in spotify_artists_names]
        discord_global_name = author.global_name.replace(" ", "").lower()
        discord_display_name = author.display_name.replace(" ", "").lower()

        try:
            # Check if the spotify username is in the name, nickname or bio of the discord's user
            if discord_global_name in spotify_artists_names or discord_display_name in spotify_artists_names:
                return True

        except discord.errors.NotFound:
            print(f"Unable to fetch the user's profile.")

    return False
