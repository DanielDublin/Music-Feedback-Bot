import discord
from discord.ext import commands
from cogs.feedback_threads import FeedbackThreads
from data.constants import FEEDBACK_CHANNEL_ID

class ScanFeedbackEdits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        """
        handle mispellings, capitalizations, switches, additions
        """

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):


        # check for <MFR to <MFS
        if before.content != after.content:
            if ctx.command.name == 'R': in before.content and "<MFS" in after.content:
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
