import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from data.constants import EVENT_VC, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_ID
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
        self.submissions_open = False # submissions will be open for 40 minutes or until there's an hour of music
        self.event_start = False # the event will start at the closest :00 or :30 since we usually announce 10 minutes before


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
        self.submissions_open = True
        self.event_start = False

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

        # Bot join event VC
        try:
            await self.itm.join_vc(interaction)
            await interaction.followup.send("✅ In The Mix fully started!", ephemeral=True)
        except Exception as e:
            print(f"Error joining VC: {e}")
            await interaction.followup.send(f"⚠️ Announcements sent but failed to join VC: {e}", ephemeral=True)


        # create task to play aotw song with 10 minutes - duration of track
        # create tasks to track 10 minute countdown + closest :00 or :30 to start the event

        # play the queue
        await self.submissions_queue.play_song()


async def setup(bot):
    await bot.add_cog(EventVC(bot))