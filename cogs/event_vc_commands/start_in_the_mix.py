import discord
import asyncio
import datetime
import re
import os
from data.constants import (
    EVENT_VC, ITM_CHANNEL, ITM_ROLE, SUBMISSIONS_CHANNEL_ID, 
    EVENT_CATEGORY, MOD_SUBMISSION_LOGGER_CHANNEL_ID, 
    GENERAL_CHAT_CHANNEL_ID, MODERATORS_CHANNEL_ID, AOTW_CHANNEL
)
from cogs.event_vc_commands.submissions_queue import SubmissionsQueue
from cogs.event_vc_commands.elven_tts import ElevenLabsTTS


class StartInTheMix:
    def __init__(self, bot):
        self.bot = bot
        # Initialize ElevenLabs TTS handler
        self.tts = ElevenLabsTTS(api_key=os.getenv('ELEVENLABS_API_KEY'))

    async def send_announcement(self, interaction):
        guild = interaction.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)

        event_submissions = guild.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        itm_channel = guild.get_channel(ITM_CHANNEL)
        event_category = guild.get_channel(EVENT_CATEGORY)
        event_text = guild.get_channel(SUBMISSIONS_CHANNEL_ID)
        event_vc = guild.get_channel(EVENT_VC)
        general_chat = guild.get_channel(GENERAL_CHAT_CHANNEL_ID)

        # purge the submissions channel
        try:
            await event_submissions.purge(limit=5)
            await mod_chat.send("✅ Purged submissions channel")
            await asyncio.sleep(0.5)
        except Exception as e:
            await mod_chat.send(f"❌ Failed to purge submissions channel: {e}")

        # clear the previous announcement
        try:
            # Only purge if there are messages
            messages = [msg async for msg in itm_channel.history(limit=1)]
            if messages:
                await itm_channel.purge(limit=1)
            await mod_chat.send("✅ Cleared previous ITM announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to clear ITM announcement: {e}")

        # change category name
        try:
            await event_category.edit(name="In-The-Mix")
            await mod_chat.send("✅ Changed category name")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to change category name: {e}")

        # open the channel view for everyone
        try:
            await itm_channel.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened ITM channel view")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open ITM channel view: {e}")

        # open event-text view for everyone
        try:
            await event_text.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened event-text view")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open event-text view: {e}")

        # open the vc view for everyone + change name
        try:
            await event_vc.edit(name="IN-THE-MIX")
            await event_vc.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened VC and changed name")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open VC/change name: {e}")

        # send announcement to itm event channel
        try:
            await itm_channel.send(
                f"<@&{ITM_ROLE}> is starting in 5 minutes!\n\n"
                f"Submissions are now **open** for next week's event. Use `?suggest (link)` in <#{SUBMISSIONS_CHANNEL_ID}> to get your song played!"
            )
            await mod_chat.send("✅ Sent ITM channel announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to send ITM announcement: {e}")

        # send message to general chat
        try:
            await general_chat.send(
                f"<@&{ITM_ROLE}> is starting in 5 minutes!\n\n"
                f"Submissions are now **open** for next week's event. Use `?suggest (link)` in <#{SUBMISSIONS_CHANNEL_ID}> to get your song played!"
            )
            await mod_chat.send("✅ Sent general chat announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to send general chat announcement: {e}")

    async def join_vc(self, interaction):
        guild = interaction.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)

        try:
            guild = interaction.guild
            event_vc = guild.get_channel(EVENT_VC)

            await event_vc.connect()
            await mod_chat.send("✅ Bot joined VC")

        except Exception as e:
            await mod_chat.send(f"❌ Failed to join VC: {e}")

    async def calculate_aotw_runtime(self, interaction, event_start_time):
        guild = interaction.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)
        aotw_channel = guild.get_channel(AOTW_CHANNEL)
        event_text = guild.get_channel(SUBMISSIONS_CHANNEL_ID)

        async for message in aotw_channel.history(limit=1):
            link = re.search(r"(https?://\S+)", message.content).group(1)
            break

        submissions_cog = self.bot.get_cog('SubmissionsQueue')

        try:
            # parse the time
            title, duration_seconds = await submissions_cog.get_song_duration(link)
            
            # Check if song is too long (more than 10 minutes)
            if duration_seconds > 600:
                await mod_chat.send(f"⚠️ AOTW track '{title}' is too long ({duration_seconds}s). Max 10 minutes.")
                await event_text.send(f"# Make sure to check out our Artist of the Week's winning track after the event!\n\n{link}")
                return None, None, None

            # allow a time to buffer
            calculated_start_time = event_start_time - datetime.timedelta(seconds=duration_seconds - 45)
            
            await mod_chat.send(f"✅ AOTW: '{title}' ({duration_seconds}s) will play at {calculated_start_time.strftime('%I:%M:%S %p')}")
            return calculated_start_time, link, title

        except Exception as e:
            await mod_chat.send(f"❌ Failed to get song duration: {e}")
            return None, None, None
    
    async def play_welcome_announcement(self, voice_client, mod_chat, title):
        """Play welcome TTS message"""
        welcome_text = "Welcome to In The Mix! Listening to the latest tracks from our community. First we have our Artist of the Week with {title}."
        
        await mod_chat.send("🎤 Playing welcome message...")
        success = await self.tts.play_tts_in_vc(voice_client, welcome_text, voice_id="TxGEqnHWrfWFTfGW9XjX")
        
        if success:
            await mod_chat.send("✅ Welcome message played")
        else:
            await mod_chat.send("❌ Failed to play welcome message")
        
        return success
    
    async def play_now_playing_announcement(self, voice_client, mod_chat, title, artist=None):
        """Play 'now playing' TTS announcement"""
        if artist:
            announcement = f"Now playing: {title} by {artist}"
        else:
            announcement = f"Now playing: {title}"
        
        await mod_chat.send(f"🎤 Announcing: {title}")
        success = await self.tts.play_tts_in_vc(voice_client, announcement, voice_id="TxGEqnHWrfWFTfGW9XjX")
        
        if success:
            await mod_chat.send("✅ Announcement played")
        else:
            await mod_chat.send("❌ Failed to play announcement")
        
        return success
    
    async def play_aotw_song(self, calculated_start_time, link, title, artist=None):
        """
        Play AOTW song with optional TTS announcements
        
        Args:
            calculated_start_time: When to start playing
            link: Song URL
            title: Song title
            artist: Artist name (optional)
        """
        submissions_cog = self.bot.get_cog('SubmissionsQueue')
        
        # Get guild and mod chat
        guild = self.bot.guilds[0] 
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)
        
        # Calculate wait time with extra buffer for TTS announcements (15 seconds)
        wait_time = (calculated_start_time - datetime.datetime.now()).total_seconds() - 15
        
        if wait_time > 0:
            await mod_chat.send(f"⏳ Waiting {wait_time:.0f} seconds before joining VC for AOTW...")
            await asyncio.sleep(wait_time)
        
        # Join VC early for announcements
        try:
            event_vc = guild.get_channel(EVENT_VC)
            voice_client = None
            
            if not self.bot.voice_clients:
                voice_client = await event_vc.connect()
                await mod_chat.send("✅ Bot joined VC for AOTW")
            else:
                voice_client = self.bot.voice_clients[0]
            
            # Wait for connection to stabilize
            await asyncio.sleep(2)
            
            # Play welcome announcement (optional - can be toggled)
            await self.play_welcome_announcement(voice_client, mod_chat)
            await asyncio.sleep(1)
            
            # Announce AOTW track
            await self.play_now_playing_announcement(voice_client, mod_chat, title, artist)
            await asyncio.sleep(1)
            
        except Exception as e:
            await mod_chat.send(f"❌ Failed to join VC or play announcements: {e}")
        
        # Play the AOTW song
        try: 
            await submissions_cog.play_song(link)
            await mod_chat.send("✅ AOTW finished playing")
            
        except Exception as e:
            await mod_chat.send(f"❌ Failed to play AOTW song: {e}")

        # Play the rest of the queue
        try:
            await submissions_cog.play_queue()
            await mod_chat.send("✅ Finished playing submission queue")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to play submission queue: {e}")


        # take the last message in aotw and check duration
        # subtract from 10 to b the start time

        
    

    # make listener for if messages are sent to event-submissions
    # allow until the :30 (+40 minutes of when the event starts)
    # then close submissions


    # check if a playlist submitted



    