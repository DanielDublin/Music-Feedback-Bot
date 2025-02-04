import discord
from discord.ext import commands
from cogs.feedback_threads import FeedbackThreads
from data.constants import FEEDBACK_CHANNEL_ID

class ScanFeedbackEdits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    print("entering")
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        print("entered")
        """
        This listener triggers when a message is edited. If <MFR> is changed to <MFS>, it will call the
        function to handle the edit and send a log.
        """
        # check for <MFR to <MFS
        if before.content != after.content:
            if "<MFR" in before.content and "<MFS" in after.content:
                print("Detected <MFR> to <MFS> change.")
                await self.MFR_to_MFS(before, after)

    async def MFR_to_MFS(self, before: discord.Message, after: discord.Message):
        """
        This function is called when a message is edited from <MFR> to <MFS>. It sends a ticket
        and logs the change.
        """
        # Log the change in the channel
        print("mfr changed to mfs")
async def setup(bot):
    await bot.add_cog(ScanFeedbackEdits(bot))
