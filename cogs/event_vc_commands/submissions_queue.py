import discord
import re
import yt_dlp
from discord.ext import commands
from data.constants import MOD_SUBMISSION_LOGGER_CHANNEL_ID, MODERATORS_CHANNEL_ID




# randomize queue
# parse the message for the link
# send message to event-text announcing
# limit time of cumulative tracks?

class SubmissionsQueue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.submission_queue = []

        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False, 
            'skip_download': True,
        }

    
    async def parse_submission(self, message):

        guild = message.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)

        if not message.author.bot:
            return
        
        content = message.content
        
        # extract YouTube, SoundCloud, Spotify, or Bandcamp links
        link = None
        sender = None

        try:
            link_match = re.search(
                r"(https?://[^\s]*(youtube\.com|youtu\.be|soundcloud\.com|spotify\.com|bandcamp\.com)[^\s]*)", 
                content, 
                re.IGNORECASE
            )
            
            link = link_match.group(1)
        except Exception as e:
            await mod_chat.send(f"❌ Error parsing ITM submission: {e}")
            return
        

        # extract the sender of the link
        try:
            mention_match = re.search(r"<@!?(\d+)>", content)
            if mention_match:
                user_id = int(mention_match.group(1))
                sender = guild.get_member(user_id)
        except Exception as e:
            await mod_chat.send(f"❌ Error parsing ITM submission: {e}")
            return

        # get the duration of the track
        formatted_duration, title = await self.get_song_duration(link)
        print(f"Duration: {formatted_duration}, Title: {title}")

        return {
            'sender': sender,
            'link': link,
            'duration': formatted_duration,
            'title': title
        }

    async def get_song_duration(self, url):

        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)  # duration in seconds
                title = info.get('title', 'Unknown')
                formatted_duration = self.format_duration(duration)
                return formatted_duration, title
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return None, None
    
    def format_duration(self, seconds):

        if not seconds:
            return "Unknown"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

            
    async def add_to_queue(self, submission_data):

        try: 
            link = submission_data['link']
            self.submission_queue.append(link)
            print("Submission added to queue")
            print(self.submission_queue)
        except Exception as e:
            print(e)

            





    async def add_submission(self, submission):

        self.submission_queue.append(submission)


# queue aotw track first!
