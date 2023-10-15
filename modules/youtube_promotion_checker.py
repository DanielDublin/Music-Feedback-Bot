import re
import os
import discord
import yt_dlp as youtube_dl
import urlextract
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_TOKEN')

# youtube_dl options
ydl_opts = {
    'outtmpl': '%(id)s.%(ext)s',
    'quiet': True,  # Optional: Set this to True to suppress output messages
}

# Regular expression to match YouTube URLs and extract video IDs
youtube_url_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:(?:youtube\.com/embed/|youtube\.com/v/|youtube\.com/watch\?v=|youtube\.com/attribution_link\?a=|youtu\.be/)([\w-]+)|(?:youtube\.com/shorts/|youtube\.com/playlist\?list=)([A-Za-z0-9_-]+))(?:&\S*)?$')
# Initialize the URL extractor
url_extractor = urlextract.URLExtract()

# Function to extract the first video ID from a text
def extract_youtube_video_id(text):
    match = youtube_url_pattern.search(text)
    if match:
        return match.group(1) or match.group(2)
    return None


# Function to extract URLs from text
def extract_urls(content):
    out_links = []
    urls = list(url_extractor.find_urls(content))
    for url in urls:
        if 'youtu' in url:
            out_links.append(url)
    return out_links
        


async def check_youtube(message):
    
    content = message.content
    
    # Extract YouTube video ID from the URL
    youtube_links = extract_urls(message.content)
    if youtube_links is None:
        return False
    
    for link in youtube_links:
        youtube_video_id = extract_youtube_video_id(content)
        if youtube_video_id is None:
            continue

        try:
            # Get the author's profile
            profile = message.author

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={youtube_video_id}', download=False)
                creator = info.get('uploader')
            
            # Check if the author's username or display name contains the YouTube creator's name
            if creator and (creator.lower() == profile.global_name.lower() or creator.lower() == profile.display_name.lower()):
                return True
    
        except discord.errors.NotFound:
            print("Unable to fetch the user's profile.")
        except Exception as e:
            print(str(e))
            
    return False
