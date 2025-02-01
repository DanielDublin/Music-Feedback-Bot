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
        print(f"Channel: {thread_channel}")  # Debugging: Check if channel is found
        

        if thread_channel:
            print(f"Attempting to create thread in channel {thread_channel.id}")
            # Create a new thread with the user's feedback message as the starting message
            thread = await thread_channel.create_text_thread(
                name=f"Feedback from {ctx.author.name}",  # Thread name will be the user's name
                message=ctx.message,  # Reference the message that triggered the thread
                reason="Creating a feedback thread"
            )
            await thread.send(f"Feedback submitted by {ctx.author.mention}!")  # Optional message in the thread
        else:
            print("Feedback channel not found.")

async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))
