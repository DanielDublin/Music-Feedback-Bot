import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from datetime import datetime

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_thread = {}  # Nested dictionary for user:thread_id:log_id

    async def create_feedback_thread(self, ctx):
        await self.bot.wait_until_ready()
        thread_channel = self.bot.get_channel(1103427357781528597)
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%d-%m %H:%M")

        # Check if the mentioned user has a stored thread in the dict
        if ctx.author.id in self.user_thread:
            embed = await self.existing_thread(ctx, formatted_time, message_link)
            existing_thread = self.bot.get_channel(int(self.user_thread[ctx.author.id]['thread_id']))
            await existing_thread.send(embed=embed)
            return

        # If no existing thread, create a new one
        await self.new_thread(ctx, formatted_time, message_link, thread_channel)

        # handles <MFR
        if ctx.command.name == 'R':
            embed = await self.MFR_embed(ctx, formatted_time, message_link)
            new_thread = self.bot.get_channel(int(self.user_thread[ctx.author.id]['thread_id']))
            await new_thread.send(embed=embed)

    async def MFR_embed(self, ctx, formatted_time, message_link):
        log_id = self.user_thread[ctx.author.id]['log_id']
        embed = discord.Embed(
            title=f"Ticket # {log_id}",
            description=f"{formatted_time}",
            color=discord.Color.green()
        )
        embed.add_field(name="<MFR used", value=f"{message_link}", inline=True)
        embed.set_footer(text="Some Footer Text")
        return embed

    async def new_thread(self, ctx, formatted_time, message_link, thread_channel):
        message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")
        thread = await thread_channel.create_thread(
            name=f"Feedback from {ctx.author.name}",
            message=message,
            reason="Creating a feedback thread"
        )
        # Add the thread_id and log_id to the user dict
        self.user_thread[ctx.author.id] = {
            'thread_id': thread.id,
            'log_id': 1  # Initialize log_id to 1 for new threads
        }

    async def existing_thread(self, ctx, formatted_time, message_link):
        existing_thread_id = self.user_thread[ctx.author.id]['thread_id']
        log_id = self.user_thread[ctx.author.id]['log_id']

        try:
            existing_thread = self.bot.get_channel(int(existing_thread_id))
            if existing_thread is None:
                print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                return
            # Increment log_id and send a message to the existing thread
            self.user_thread[ctx.author.id]['log_id'] += 1
            log_id = self.user_thread[ctx.author.id]['log_id']
            embed = await self.MFR_embed(ctx, formatted_time, message_link)
            embed.title = f"Ticket #{log_id}"  # Update embed with the correct log_id
            return embed
        except Exception as e:
            print(f"An error occurred while fetching/sending to the thread: {e}")
        return


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))
