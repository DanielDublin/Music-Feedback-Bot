import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from datetime import datetime
import traceback

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_thread = {}

        """
        need to add a check that scans the channel for author id in case bot crashes. user_threads are lost
        """

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
            embed = await self.existing_thread(ctx, formatted_time, message_link)
            existing_thread = self.bot.get_channel(int(self.user_thread[ctx.author.id]))
            await existing_thread.send(embed=embed)
            return

        # else create new thread
        await self.new_thread(ctx, formatted_time, message_link, thread_channel)

        if ctx.command.name == 'R':
            embed = await self.MFR_embed(formatted_time, message_link)
            # Get the newly created thread to send the embed
            new_thread = self.bot.get_channel(int(self.user_thread[ctx.author.id]))
            await new_thread.send(embed=embed)

    async def MFR_embed(self,formatted_time, message_link):
        embed = discord.Embed(
            title="Ticket #",
            description=f"{formatted_time}",
            color=discord.Color.green()
        )

        # Add a field to the embed
        embed.add_field(name="<MFR used", value=f"{message_link}",
                        inline=True)

        embed.set_footer(text="Some Footer Text")
        return embed

    async def new_thread(self, ctx, thread_channel):
        # make the thread
        message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

        # Create the new thread from the above message
        thread = await thread_channel.create_thread(
            name=f"Feedback from {ctx.author.name}",
            message=message,
            reason="Creating a feedback thread"
        )
        # add the thread_id to the user - correctly returns MFR user + thread id
        self.user_thread[ctx.author.id] = thread.id
        print(self.user_thread)

    async def existing_thread(self, ctx, formatted_time, message_link):
        # Access the thread ID stored for the user
        existing_thread_id = self.user_thread[ctx.author.id]

        try:
            # Ensure the thread ID is an integer (it should be, but we check it here)
            existing_thread = self.bot.get_channel(int(existing_thread_id))
            if existing_thread is None:
                print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                return

            # Send a message to the existing thread
            embed = await self.MFR_embed(formatted_time, message_link)
            return embed

        except Exception as e:
            print(f"An error occurred while fetching/sending to the thread: {e}")
        return

    async def log_id(self):
        # need to access



async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))