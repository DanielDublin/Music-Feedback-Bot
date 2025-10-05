# sends every time a new message sent to feedback channel
import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID

class FeedbackChannelEmbeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_sticky_embed = None

    @commands.Cog.listener()
    async def on_message(self, message):

        feedback_channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)

        if message.channel != feedback_channel:
            return

        # ignore if from the bot
        if message.author.bot:
            return
        
        # check if there's a stored old sticky message
        if self.old_sticky_embed:
            await self.old_sticky_embed.delete()
        
        # otherwise send embed of the recent feedback needed, based on the latest db updates
        embed = discord.Embed(
        title=f"Ticket ",
        description=f"test",
        color=discord.Color.green()
        )

        # store the previously sent embed so that it may be deleted to create sticky effect
        self.old_sticky_embed = await feedback_channel.send(embed=embed)

    

async def setup(bot):
    await bot.add_cog(FeedbackChannelEmbeds(bot))