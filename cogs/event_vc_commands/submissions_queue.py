import discord
import re
from discord.ext import commands
from data.constants import MOD_SUBMISSION_LOGGER_CHANNEL_ID




# randomize queue
# parse the message for the link
# send message to event-text announcing
# limit time of cumulative tracks?

class SubmissionsQueue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.submission_queue = []

    
    async def parse_submission(self, message):

        if not message.author.bot:
            return
        
        content = message.content
        
        link = None
        # Try to find YouTube, SoundCloud, Spotify, or Bandcamp links
        link_match = re.search(
            r"(https?://[^\s]*(youtube\.com|youtu\.be|soundcloud\.com|spotify\.com|bandcamp\.com)[^\s]*)", 
            content, 
            re.IGNORECASE
        )
        
        if link_match:
            link = link_match.group(1)
        else:
            # Fallback: find any http/https link
            general_link = re.search(r"(https?://[^\s]+)", content, re.IGNORECASE)
            if general_link:
                link = general_link.group(1)
            else:
                return None
            
        print(link)

            





    async def add_submission(self, submission):

        self.submission_queue.append(submission)


