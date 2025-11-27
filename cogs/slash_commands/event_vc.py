import discord
import asyncio
import datetime
from discord.ext import commands
from discord import app_commands
from data.constants import EVENT_VC, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_ID, AOTW_CHANNEL
from cogs.event_vc_commands.start_in_the_mix import StartInTheMix

# INSTALLED ffmpeg DIRECTLY TO GCP
""""
gcloud compute ssh bots4fun1@mfbot-1 --zone=us-central1-c
sudo apt update
sudo apt install -y ffmpeg
ffmpeg -version
exit
"""""

class EventVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.itm = StartInTheMix(bot)
        self.submissions_open = False  # Track submission state at cog level
        self.submission_close_time = None
        # submissions will be open for 40 minutes or until there's an hour of music
        # the event will start at the closest :00 or :30 since we usually announce 10 minutes before

    # Listen for messages in event-submissions channel
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore anything but bot messages
        if not message.author.bot:
            return
        
        # Check if message is in event-submissions channel
        if message.channel.id != MOD_SUBMISSION_LOGGER_CHANNEL_ID:
            return

        # Check if submissions are open
        if not self.submissions_open:
            return

        # Get the submissions queue cog
        submissions_queue = self.bot.get_cog('SubmissionsQueue')
        if not submissions_queue:
            print("❌ SubmissionsQueue cog not found")
            return

        # close submissions if time limit reached
        if self.submission_close_time and datetime.datetime.now() >= self.submission_close_time:
            self.submissions_open = False
            event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
            await event_text.send("🔒 **Submissions are now CLOSED** - Time limit reached!")
            return

        try:
            # Parse the message for the link FIRST to get duration
            submission_data = await submissions_queue.parse_submission(message)
            
            if not submission_data:
                await message.add_reaction("❌")
                return

            # Check if adding this song would exceed 1 hour limit
            current_length = submissions_queue.get_queue_length()
            new_song_duration = submission_data['duration_seconds']
            projected_length = current_length + new_song_duration
            
            if projected_length > 3600:  # Would exceed 1 hour
                self.submissions_open = False
                event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
                
                # Send rejection message
                sender = submission_data['sender']
                title = submission_data['title']
                await event_text.send(
                    f"❌ **{sender.mention}** - Sorry, **{title}** would exceed the 1-hour limit!\n"
                    f"🔒 **Submissions are now CLOSED** - Queue is full!"
                )
                await message.add_reaction("⏱️")
                return

            # Add submission to queue 
            await submissions_queue.add_to_queue(submission_data)

            # Send message to event-text announcing the submission
            event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
            sender = submission_data['sender']
            title = submission_data['title']
            
            # Get updated queue info
            queue_count = submissions_queue.get_queue_count()
            queue_length_formatted = submissions_queue.get_formatted_queue_length()
            
            await event_text.send(
                f"✅ **{sender.mention}** added: **{title}**\n"
                f"📊 Queue: {queue_count} songs | {queue_length_formatted} total"
            )
            
        except Exception as e:
            print(f"❌ Error processing submission: {e}")
            import traceback
            traceback.print_exc()

    @app_commands.command(name="start-in-the-mix", description="Start the In-The-Mix event")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_in_the_mix(self, interaction):
        await interaction.response.defer(ephemeral=True)

        # Open submissions 
        submissions_start_time = datetime.datetime.now()
        self.submissions_open = True
        self.submission_close_time = submissions_start_time + datetime.timedelta(minutes=40)
        
        event_start_time = submissions_start_time + datetime.timedelta(minutes=5)  # Event starts 10 min after command

        event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)

        # Configure channel, send announcements, change channel names/perms
        try:
            await self.itm.send_announcement(interaction)
            await interaction.followup.send("✅ Announcements sent!", ephemeral=True)
        except discord.NotFound as e:
            print(f"NotFound error in send_announcement: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            return
        except Exception as e:
            print(f"Error in send_announcement: {e}")
            await interaction.followup.send(f"❌ Command failed: {e}", ephemeral=True)
            return

        # Calculate aotw runtime
        try:    
            calculated_start_time, aotw_link = await self.itm.calculate_aotw_runtime(interaction, event_start_time)
            await interaction.followup.send("✅ AOTW runtime calculated!", ephemeral=True)
        except Exception as e:
            print(f"Error calculating AOTW runtime: {e}")
            await interaction.followup.send(f"⚠️ Failed to calculate AOTW runtime: {e}", ephemeral=True)
            calculated_start_time, aotw_link = None, None

        # Play aotw track 
        # will also call the rest of the queue immediately after playing aotw
        if calculated_start_time and aotw_link:
            try:
                asyncio.create_task(self.itm.play_aotw_song(calculated_start_time, aotw_link))
                await interaction.followup.send("✅ AOTW scheduled!", ephemeral=True)
            except Exception as e:
                print(f"Error scheduling AOTW: {e}")
                await interaction.followup.send(f"⚠️ Failed to schedule AOTW: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Check <#{AOTW_CHANNEL}> for this week's Artist of the Week!", ephemeral=True)
        
        # Schedule automatic submission closing after 40 minutes
        asyncio.create_task(self.close_submissions_timer())
        
        # await self.submissions_queue.play_queue()

    async def close_submissions_timer(self):
        """Automatically close submissions after 40 minutes"""

        await asyncio.sleep(30 * 60)  # Wait 30 minutes first
        if self.submissions_open:
            event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
            await event_text.send("⏳ 10 minutes remaining to submit your tracks!")

        await asyncio.sleep(40 * 60)  # Wait 40 minutes
        
        if self.submissions_open:
            self.submissions_open = False
            event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
            await event_text.send("🔒 **Submissions are now CLOSED** - Time's up!")
            
            # Get final queue stats
            submissions_queue = self.bot.get_cog('SubmissionsQueue')
            if submissions_queue:
                count = submissions_queue.get_queue_count()
                length = submissions_queue.get_formatted_queue_length()
                await event_text.send(f"📊 Final queue: {count} songs | {length} total")

async def setup(bot):
    await bot.add_cog(EventVC(bot))