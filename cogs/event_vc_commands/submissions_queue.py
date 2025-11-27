import discord
import re
import yt_dlp
import asyncio
import random
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

        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
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
            return None
        
        # extract the sender of the link
        try:
            mention_match = re.search(r"<@!?(\d+)>", content)
            if mention_match:
                user_id = int(mention_match.group(1))
                sender = guild.get_member(user_id)
        except Exception as e:
            await mod_chat.send(f"❌ Error parsing ITM submission: {e}")
            return None

        # get the duration of the track
        title, duration_seconds = await self.get_song_duration(link)  
        print(f"Duration: {duration_seconds}s, Title: {title}")

        return {
            'sender': sender,
            'link': link,
            'duration_seconds': duration_seconds, 
            'title': title
        }

    async def get_song_duration(self, url):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration_seconds = info.get('duration', 0)
                title = info.get('title', 'Unknown')
                return title, duration_seconds 
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return "Unknown", 0

    
    async def add_to_queue(self, submission_data):
        try: 
            # Store the FULL submission data, not just the link
            self.submission_queue.append(submission_data)
            print(f"✅ Submission added to queue: {submission_data['title']}")
            print(f"📋 Current queue: {[s['title'] for s in self.submission_queue]}")
        except Exception as e:
            print(f"❌ Error in add_to_queue: {e}")

    def get_queue_length(self):
        try: 
            total_seconds = sum(submission['duration_seconds'] for submission in self.submission_queue)
        except Exception as e:
            print(f"❌ Error calculating queue length: {e}")

        return total_seconds
    
    def get_formatted_queue_length(self):
        total_seconds = self.get_queue_length()
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        secs = int(total_seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def get_queue_count(self):

        return len(self.submission_queue)

    async def play_song(self, link):
        """Play a single song (for AOTW)"""
        
        if not self.bot.voice_clients:
            print("❌ Bot is not connected to a voice channel")
            return
        
        voice_client = self.bot.voice_clients[0]
        
        try:
            # Get song info
            title, duration_seconds = await self.get_song_duration(link)
            print(f"▶️  Now playing AOTW: {title}")
            
            # Extract audio URL
            ytdl_format_options = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ytdl_format_options).extract_info(link, download=False)
            )
            
            # Handle playlists
            if 'entries' in data:
                data = data['entries'][0]
            
            # Get streaming URL
            if 'url' in data:
                audio_url = data['url']
            elif 'formats' in data:
                formats = [f for f in data['formats'] if f.get('acodec') != 'none']
                audio_url = formats[0]['url'] if formats else data['formats'][0]['url']
            else:
                raise Exception("Could not extract audio URL")
            
            print(f"📡 Audio URL extracted, starting playback...")
            
            # Play the audio
            audio_source = discord.FFmpegPCMAudio(audio_url, **self.ffmpeg_options)
            voice_client.play(audio_source)
            
            # Wait for song to finish
            while voice_client.is_playing():
                await asyncio.sleep(1)
                
            print(f"✅ Finished playing AOTW: {title}")
            
        except Exception as e:
            print(f"❌ Error playing AOTW: {e}")
            import traceback
            traceback.print_exc()

    
    async def play_queue(self):
        print(f"🎵 Starting playback. Queue has {len(self.submission_queue)} songs")
        
        # Check if bot is in voice channel
        if not self.bot.voice_clients:
            print("❌ Bot is not connected to a voice channel")
            return
        
        voice_client = self.bot.voice_clients[0]
        
        # Play each song in the queue
        while len(self.submission_queue) > 0:
            
            # randomize the queue first
            random.shuffle(self.submission_queue)

            submission = self.submission_queue.pop(0)
            url = submission['link']
            title = submission['title']
            
            print(f"▶️  Now playing: {title}")
            
            try:
                # Use better yt-dlp options for streaming
                ytdl_format_options = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                }
                
                # Extract info in a non-blocking way
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    None, 
                    lambda: yt_dlp.YoutubeDL(ytdl_format_options).extract_info(url, download=False)
                )
                
                # Handle playlists
                if 'entries' in data:
                    data = data['entries'][0]
                
                # Get the streaming URL
                if 'url' in data:
                    audio_url = data['url']
                elif 'formats' in data:
                    # Find best audio format
                    formats = [f for f in data['formats'] if f.get('acodec') != 'none']
                    if formats:
                        audio_url = formats[0]['url']
                    else:
                        audio_url = data['formats'][0]['url']
                else:
                    raise Exception("Could not extract audio URL")
                
                print(f"📡 Audio URL extracted, starting playback...")
                
                # Create audio source
                audio_source = discord.FFmpegPCMAudio(audio_url, **self.ffmpeg_options)
                
                # Play the audio
                voice_client.play(audio_source)
                
                # Wait for the song to finish
                while voice_client.is_playing():
                    await asyncio.sleep(1)
                    
                print(f"✅ Finished playing: {title}")
                
            except Exception as e:
                print(f"❌ Error playing {title}: {e}")
                import traceback
                traceback.print_exc()
        
        print("🏁 Queue finished!")


async def setup(bot):
    await bot.add_cog(SubmissionsQueue(bot))