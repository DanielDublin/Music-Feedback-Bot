import re
import os
import discord
import youtube_dl
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_TOKEN')

youtube_dl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Regular expressions to match different YouTube URL formats
youtube_url_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(.+)')


# Function to extract the video ID from a YouTube content
def extract_youtube_video_id(content):
    match = youtube_url_pattern.match(content)
    if match:
        return match.group(4)
    return None


async def check_youtube(message):
    
    content = message.content
    
    # Extract YouTube video ID from the URL
    youtube_video_id = extract_youtube_video_id(content)
    if youtube_video_id is None:
        return False

    try:
        # Get the author's profile
        profile = await message.author.fetch()

        # Get the YouTube video's details
        ydl = youtube_dl.YoutubeDL(youtube_dl_opts)
        with ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={youtube_video_id}', download=False)
            creator = info.get('creator')

        # Check if the author's username or display name contains the YouTube creator's name
        if creator and (creator in profile.name or creator in profile.display_name or profile.bio):
            return True
        else:

            # Check if the link to YouTube is in the user's connections
            creator_in_youtube_connections = any(
                    creator in connection.get('name', '') and connection.get('type') == discord.ConnectionType.youtube for connection in profile.connections
                )
            if  creator_in_youtube_connections:
                return True
            else:
                return False
    except discord.errors.NotFound:
        print("Unable to fetch the user's profile.")
