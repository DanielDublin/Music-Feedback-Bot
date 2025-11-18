import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from data.constants import EVENT_VC, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_ID
from cogs.event_vc_commands.start_in_the_mix import StartInTheMix


class EventVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.itm = StartInTheMix(bot)

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
        
        # Submission is valid
        await event_text.send(f"{message.author.mention} READ!")
        await message.add_reaction("✅")

    @app_commands.command(name="start-in-the-mix", description="Start the In-The-Mix event")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_in_the_mix(self, interaction):
        await interaction.response.defer(ephemeral=True)

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


async def setup(bot):
    await bot.add_cog(EventVC(bot))