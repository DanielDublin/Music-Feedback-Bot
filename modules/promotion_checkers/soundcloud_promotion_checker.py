import re
import aiohttp
import discord
import urlextract
from bs4 import BeautifulSoup


# Initialize the URL extractor 
url_extractor = urlextract.URLExtract()


def extract_soundcloud_url(message_content):
    # Function to extract URLs from text
    out_links = []
    urls = list(url_extractor.find_urls(message_content))
    for url in urls:
        if 'soundcloud' in url:
            out_links.append(url)
    return out_links


async def expand_soundcloud_url(short_url):
    async with aiohttp.ClientSession() as session:
        async with session.head(short_url, allow_redirects=True) as response:
            if response.status == 200:
                # Extract the full URL from the response headers
                full_url = response.url
                full_url = str(full_url).strip("URL('')")

                # Check if the full URL is a SoundCloud URL
                if re.match(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)', full_url):
                    return full_url
                else:
                    return None
            else:
                return None


def extract_soundcloud_channel_name(expanded_url):
    # Regular expression to match the channel name in a SoundCloud URL
    soundcloud_name_pattern = re.compile(r'https?://(www\.)?soundcloud\.com/([A-Za-z0-9_-]+)')

    match = soundcloud_name_pattern.match(expanded_url)

    if match:
        channel_name = match.group(2)
        return channel_name
    else:
        return None


def extract_soundcloud_song_name(expanded_url):
    # Regular expression to match the channel name in a SoundCloud URL
    soundcloud_song_pattern = re.compile(r'https?://soundcloud\.com/[\w-]+/([\w-]*)')

    match = soundcloud_song_pattern.match(expanded_url)

    if match:
        song_name = match.group(1)
        return song_name
    else:
        return None


async def fetch_soundcloud_display_name(expanded_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(expanded_url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                title_element = soup.select_one('title')
                if title_element:
                    # Extract the content of the <title> tag
                    title_content = title_element.text

                    song_name = extract_soundcloud_song_name(expanded_url)
                    display_name_match = None

                    if song_name is not None:  # We are at the main channel
                        display_name_match = re.search(r'by (.*?) \|', title_content)
                    else:
                        display_name_match = re.search(r'Stream (.+?) music \|', title_content)

                    if display_name_match is not None:
                        display_name = display_name_match.group(1)
                        return display_name
                    else:
                        return None
                else:
                    return None


async def check_soundcloud(message):
    content = message.content

    short_urls = extract_soundcloud_url(content)
    if short_urls is None:
        return False

    for url in short_urls:
        expanded_url = await expand_soundcloud_url(url)
        if expanded_url is None:
            print("error while expanding url from soundcloud")
            continue

        soundcloud_default_user_name = extract_soundcloud_channel_name(expanded_url)
        if soundcloud_default_user_name is None:
            print("error while getting username from soundcloud")
            continue

        soundcloud_user_display_name = await fetch_soundcloud_display_name(expanded_url)
        if soundcloud_user_display_name is None:
            print("error while getting display name from soundcloud")
            continue

        author = message.author
        soundcloud_user_display_name = soundcloud_user_display_name \
            .replace(" ", "").replace("-", "").replace("_", "").lower()
        soundcloud_default_user_name = soundcloud_default_user_name \
            .replace(" ", "").replace("-", "").replace("_", "").lower()
        discord_global_name = author.global_name \
            .replace(" ", "").replace("-", "").replace("_", "").lower()
        discord_display_name = author.display_name \
            .replace(" ", "").replace("-", "").replace("_", "").lower()

        try:
            # Check if the Soundcloud username is in the name, nickname or bio of the discord's user
            if soundcloud_user_display_name == discord_global_name \
                    or soundcloud_user_display_name == discord_display_name:
                return True
            elif soundcloud_default_user_name == discord_global_name \
                    or soundcloud_default_user_name == discord_display_name:
                return True

        except discord.errors.NotFound:
            print(f"Unable to fetch the user's profile.")

    return False
