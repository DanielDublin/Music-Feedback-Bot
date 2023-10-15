import re
import aiohttp
import discord
from discord.audit_logs import F

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
            
def extract_soundcloud_channel_name(expanded_url):
    # Regular expression to match the channel name in a SoundCloud URL
    soundcloud_url_pattern = re.compile(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)')

    match = soundcloud_url_pattern.match(expanded_url)

    if match:
        channel_name = match.group(2)
        return channel_name
    else:
        return None
    
def extract_soundcloud_url(message_content):
    # Function to extract URLs from text
    out_links = []
    urls = list(url_extractor.find_urls(content))
    for url in urls:
        if 'soundcloud' in url:
            out_links.append(url)
    return out_links
        


async def check_soundcloud(message):
    content =message.content
  
    short_urls = extract_soundcloud_url(content)
    if short_url is None:
        return False
    
    for url in short_urls:
        expanded_url = await expand_soundcloud_url(url)
        if expanded_url is None:
            print("error while expanding url from soundcloud")
            continue
    
        soundcloud_user = extract_soundcloud_channel_name(expanded_url)
        if soundcloud_user is None:
            print("error while getting username from soundcloud")
            continue
        
        soundcloud_user = soundcloud_user.lower()
        try:
            author = message.author
            # Check if the the Soundcloud username is in the name, nickname or bio of the discord's user
            if soundcloud_user in author.global_name.replace(" ","").lower() or soundcloud_user in author.display_name.replace(" ","").lower():
                return True

        except discord.errors.NotFound:
            print(f"Unable to fetch the user's profile.")
        
