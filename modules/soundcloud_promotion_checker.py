import re
import aiohttp
import discord

# Define a regular expression pattern to match SoundCloud URLs
soundcloud_url_pattern = re.compile(r'https?://soundcloud\.com/([A-Za-z0-9_-]+)')

async def expand_soundcloud_url(short_url):
    async with aiohttp.ClientSession() as session:
        async with session.head(short_url, allow_redirects=True) as response:
            if response.status == 200:
                # Extract the full URL from the response headers
                full_url = response.url
                
                # Check if the full URL is a SoundCloud URL
                if re.match(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)', str(full_url)):
                    return full_url
                else:
                    return None
            else:
                return None

def extract_soundcloud_url(message_content):
    # Regular expression to match SoundCloud URLs
    soundcloud_url_pattern = re.compile(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)')

    # Find the first SoundCloud URL in the message
    match = soundcloud_url_pattern.search(message_content)

    if match:
        # Extract the URL
        short_url = match.group(0)
        return short_url
    else:
        return None

def extract_soundcloud_channel_name(expanded_url):
    # Regular expression to match the channel name in a SoundCloud URL
    soundcloud_url_pattern = re.compile(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)')

    match = soundcloud_url_pattern.match(expanded_url)

    if match:
        channel_name = match.group(2)
        return channel_name
    else:
        return None
    

async def check_soundcloud(message):
    content =message.content
  
    short_url = extract_soundcloud_url(content)
    if short_url is None:
        return False
    
    expanded_url = await expand_soundcloud_url(short_url)
    if expanded_url is None:
        print("error while expanding url from soundcloud")
        return False
    
    soundcloud_user = extract_soundcloud_channel_name(expanded_url)
    if soundcloud_user is None:
        print("error while getting username from soundcloud")
        return False
    soundcloud_user = soundcloud_user.lower()

    try:
        # Get the author's profile
        profile = await message.author.fetch()

        # Check if the the Soundcloud username is in the name, nickname or bio of the discord's user
        if soundcloud_user in profile.name.replace(" ","").lower() or soundcloud_user in profile.display_name.replace(" ","").lower() or soundcloud_user in profile.bio.replace(" ","").lower():
            return True
        else:
          
            # Check if the link to SoundCloud is in the user's connections
            soundcloud_in_connections = any(
                soundcloud_user in connection.get('name', '').replace(" ","").lower() and connection.get('type') == discord.ConnectionType.soundcloud for connection in profile.connections
            )
            if  soundcloud_in_connections:
                return True
            else:
                return False
    except discord.errors.NotFound:
        print(f"Unable to fetch the user's profile.")
        
