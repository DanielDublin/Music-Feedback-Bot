import discord
import asyncio
import datetime
from discord.ext import commands
from discord import app_commands
from data.constants import EVENT_VC, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_ID, AOTW_CHANNEL
from cogs.event_vc_commands.start_in_the_mix import StartInTheMix
from cogs.event_vc_commands.submissions_queue import SubmissionsQueue

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
        self.submissions_queue = SubmissionsQueue(bot)
# submissions will be open for 40 minutes or until there's an hour of music
# the event will start at the closest :00 or :30 since we usually announce 10 minutes before


    # Listen for messages in event-submissions channel
    @commands.Cog.listener()
    async def on_message(self, message):

        event_text = self.bot.get_channel(SUBMISSIONS_CHANNEL_ID)
        # Ignore anything but bot messages
        if not message.author.bot:
            return
        
        # Check if message is in event-submissions channel
        if message.channel.id != MOD_SUBMISSION_LOGGER_CHANNEL_ID:
            return
        
        # Check if submissions are open
        # if not self.itm.submissions_open:
        #     await message.delete()
        #     await message.channel.send(
        #         f"{message.author.mention} Sorry, submissions are now closed!",
        #         delete_after=60
        #     )
        #     return

        # parse the message for the link
        link = await self.submissions_queue.parse_submission(message)

        # add submission to queue, get track info
        await self.submissions_queue.add_to_queue(link)


        await message.add_reaction("✅")

    @app_commands.command(name="start-in-the-mix", description="Start the In-The-Mix event")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_in_the_mix(self, interaction):
        await interaction.response.defer(ephemeral=True)

        # open submissions 
        submissions_start_time = datetime.datetime.now()
        submissions_open = True
        event_start_time = submissions_start_time + datetime.timedelta(minutes=5)
        event_start = False

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

        # calculate aotw runtime
        try:    
            calculated_start_time, aotw_link = await self.itm.calculate_aotw_runtime(interaction, event_start_time)
            await interaction.followup.send("✅ AOTW runtime calculated!", ephemeral=True)
        except Exception as e:
            print(f"Error calculating AOTW runtime: {e}")
            await interaction.followup.send(f"⚠️ Failed to calculate AOTW runtime: {e}", ephemeral=True)
            calculated_start_time, aotw_link = None, None

        # play aotw track (run as background task so it doesn't block)
        if calculated_start_time and aotw_link:
            try:
                asyncio.create_task(self.itm.play_aotw_song(calculated_start_time, aotw_link))
                await interaction.followup.send("✅ AOTW scheduled!", ephemeral=True)
            except Exception as e:
                print(f"Error scheduling AOTW: {e}")
                await interaction.followup.send(f"⚠️ Failed to schedule AOTW: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Check <#{AOTW_CHANNEL}> for this week's Artist of the Week!", ephemeral=True)
        # play the queue
        # await self.submissions_queue.play_queue()


async def setup(bot):
    await bot.add_cog(EventVC(bot))