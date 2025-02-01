import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_feedback_thread(self, ctx):
        """Create a thread in the feedback channel"""
        # Ensure bot is fully initialized
        await self.bot.wait_until_ready()

        # Attempt to get the feedback channel
        thread_channel = self.bot.get_channel(1103427357781528597)

        if thread_channel:
            # Send a new message in the channel (this is the message that will start the thread)
            message = await ctx.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

            # Create the thread from the newly sent message
            thread = await thread_channel.create_thread(
                name=f"Feedback from {ctx.author.name}",  # Thread name will be the user's name
                message=message,  # Use the message sent by `ctx.send()`
                reason="Creating a feedback thread"
            )

            # Send a confirmation message inside the thread
            await thread.send(f"Feedback submitted by {ctx.author.mention}!")  # Optional message in the thread
        else:
            print("Feedback channel not found.")


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))
