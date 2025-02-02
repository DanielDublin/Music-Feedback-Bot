import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from datetime import datetime
import traceback

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_thread = {}

    async def create_feedback_thread(self, ctx):
        await self.bot.wait_until_ready()

        # need to change to not be hardcoded
        thread_channel = self.bot.get_channel(1103427357781528597)

        # build the full link for the message link used in reference in thread
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        log_id = 0

        # Construct the message link
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        # formatted time for inside thread
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%d-%m %H:%M")

        # check if the mentioned user has a stored thread
        if ctx.author.id in self.user_thread:
            # Access the thread ID stored for the user
            existing_thread_id = self.user_thread[ctx.author.id]
            print(f"Existing thread ID: {existing_thread_id}")

            try:
                # Ensure the thread ID is an integer (it should be, but we check it here)
                existing_thread = self.bot.get_channel(int(existing_thread_id))
                if existing_thread is None:
                    print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                    return

                # Send a message to the existing thread
                await existing_thread.send("You already have a feedback thread!")
                print("Message sent to the existing thread")

            except Exception as e:
                print(f"An error occurred while fetching/sending to the thread: {e}")
            return

        # else if not, make the thread
        message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

        # Create the thread from the newly sent message
        thread = await thread_channel.create_thread(
            name=f"Feedback from {ctx.author.name}",
            message=message,
            reason="Creating a feedback thread"
        )
        # add the thread_id to the user - correctly returns MFR user + thread id
        self.user_thread[ctx.author.id] = thread.id
        print(self.user_thread)

        if ctx.command.name == 'R':
            # Send a confirmation message inside the thread
            await thread.send(f"{log_id} ```{formatted_time}: Used <MFR -```{message_link}")
            log_id += 1

async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))