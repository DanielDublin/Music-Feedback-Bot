import re
import os
import asyncio
import logging
import discord
import yt_dlp as youtube_dl
import urlextract
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_TOKEN')

logger = logging.getLogger(__name__)

# youtube_dl options
ydl_opts = {
    'outtmpl': '%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
}

# YT URL patterns
youtube_url_pattern1 = re.compile(r'(https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)&list=([A-Za-z0-9_-]+)')
youtube_url_pattern2 = re.compile(r'(https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)')
youtube_url_pattern3 = re.compile(r'(https?://)?youtu\.be/([A-Za-z0-9_-]+)(?:\?.*)?$')


# Initialize the URL extractor 
url_extractor = urlextract.URLExtract()


# Function to extract the video ID from a YouTube URL
def extract_youtube_video_id(url):
    if youtube_url_pattern1.match(url.replace('\n', "")):
        match = youtube_url_pattern1.search(url)
        if match:
            return match.group(2)
    elif youtube_url_pattern2.match(url):
        match = youtube_url_pattern2.search(url.replace('\n', ""))
        if match:
            return match.group(2)
    elif youtube_url_pattern3.match(url):
        match = youtube_url_pattern3.search(url.replace('\n', ""))
        if match:
            return match.group(2)
    return None


# Function to extract URLs from text
def extract_video_urls(content):
    out_links = []
    pattern = r'.*https?://'

    urls = list(url_extractor.find_urls(content))
    for url in urls:
        if 'youtu' in url and "channel" not in url and "@" not in url:
            cleaned_url = re.sub(pattern, '', url)
            out_links.append(cleaned_url)
        else:
            out_links.append(url)
    return out_links


async def handle_videos(message):
    # Extract YouTube video ID from the URL
    youtube_links = extract_video_urls(message.content)
    if youtube_links is None:
        return False

    for link in youtube_links:
        youtube_video_id = extract_youtube_video_id(link)
        if youtube_video_id is None:
            continue

        try:
            # Get the author's profile
            profile = message.author

            vid_id = youtube_video_id  # capture loop variable for closure
            def _extract():
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(f'https://www.youtube.com/watch?v={vid_id}', download=False)

            info = await asyncio.to_thread(_extract)
            creator = info.get('uploader')

            # Check if the author's username or display name contains the YouTube creator's name
            discord_global_name = (profile.global_name or "").replace(" ", "").lower()
            discord_display_name = profile.display_name.replace(" ", "").lower()
            creator = creator.replace(" ", "").lower()
            if creator and (creator.lower() == discord_global_name or creator.lower() == discord_display_name):
                return True

        except discord.errors.NotFound:
            logger.warning("Unable to fetch the user's profile.")
        except Exception as e:
            logger.error("Error checking YouTube video", exc_info=True)
    return False


# Function to extract URLs from text
def extract_channel_urls(content):
    out_links = []
    pattern = r'.*https?://'

    urls = list(url_extractor.find_urls(content))
    for url in urls:
        if 'youtu' in url and "@" in url:
            cleaned_url = re.sub(pattern, '', url)
            out_links.append(cleaned_url)
    return out_links


def get_youtube_channel_info(channel_url):
    pattern = r'\.com/(@[\w-]+)'
    # Use re.search to find the match
    match = re.search(pattern, channel_url)
    # Extract the username if a match is found
    if match:
        username = match.group(1)[1:]
        return username
    return None


async def handle_channels(message):
    # Extract YouTube video ID from the URL
    youtube_links = extract_channel_urls(message.content)
    if youtube_links is None:
        return False

    for link in youtube_links:

        try:
            # Get the author's profile
            profile = message.author

            creator = get_youtube_channel_info(link)
            if creator is None:
                continue

            # Check if the author's username or display name contains the YouTube creator's name
            discord_global_name = (profile.global_name or "").replace(" ", "").lower()
            discord_display_name = profile.display_name.replace(" ", "").lower()
            creator = creator.replace(" ", "").lower()
            if creator.lower() == discord_global_name or creator.lower() == discord_display_name:
                return True

        except discord.errors.NotFound:
            logger.warning("Unable to fetch the user's profile.")
        except Exception as e:
            logger.error("Error checking YouTube channel", exc_info=True)
    return False


async def check_youtube(message):

    out = await handle_videos(message)
    if out:
        return True
    else:
        out = await handle_channels(message)

    return out
