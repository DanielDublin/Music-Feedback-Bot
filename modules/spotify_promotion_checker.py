import re
import discord
import urlextract
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()
SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')



# Initialize the URL extractor 
url_extractor = urlextract.URLExtract()
# Create a Spotify client
sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))


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
                track_info = sp.track(link_id)
            elif link_type == 'album':
                track_info = sp.album(link_id)
            elif link_type == 'artist':
                track_info = sp.artist(link_id)
            else:
                return None

            # Extract the artist name
            artist_name = track_info['artists'][0]['name']
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
       
        
        spotify_user_name = fetch_artist_name(url)
        if spotify_user_name is None:
            continue
        
        
        spotify_user_name = spotify_user_name.replace(" ", "").lower()
        discord_global_name = author.global_name.replace(" ", "").lower()
        discord_display_name = author.display_name.replace(" ", "").lower()

        try:
            # Check if the spotify username is in the name, nickname or bio of the discord's user
            if spotify_user_name == discord_global_name \
                    or spotify_user_name == discord_display_name:
                return True

        except discord.errors.NotFound:
            print(f"Unable to fetch the user's profile.")

    return False
