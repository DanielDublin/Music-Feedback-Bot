import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from data.constants import THREADS_CHANNEL

class DiscordHelpers:
    def __init__(self, bot, points_logic_instance=None):
        self.bot = bot
        self._points_logic = points_logic_instance

    async def unarchive_thread(self, existing_thread):
        if existing_thread.archived:
            await existing_thread.edit(archived=False)

    async def archive_thread(self, existing_thread):
        if not existing_thread.archived:
            await asyncio.sleep(5)
            await existing_thread.edit(archived=True)

    def get_message_link(self, ctx):
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    def get_formatted_time(self):
        eastern = ZoneInfo("America/New_York")
        current_time = datetime.now(eastern)
        return current_time.strftime("%B %d, %Y %H:%M")

    async def load_feedback_cog(self, ctx):
        from .points_logic import PointsLogic
        feedback_cog = self.bot.get_cog("FeedbackThreads")
        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")
            return
        
        if ctx.author.id in feedback_cog.user_thread:
            user_thread = feedback_cog.user_thread
            points_logic = PointsLogic(self.bot, user_thread, ctx)

            user_id = str(ctx.author.id)
            print(user_id)

            ticket_counter = user_thread[ctx.author.id][1]
            thread_id = user_thread[ctx.author.id][0]

            thread = await self.bot.fetch_channel(thread_id)
            print(thread)
        else:
            pass

        return thread, ticket_counter, points_logic, user_id
    
    async def load_threads_cog(self, ctx):
    # Get the FeedbackThreads cog instance
        feedback_cog = self.bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")

        # Access the shared user_thread dict and ThreadsManager instance
        user_thread = feedback_cog.user_thread
        sqlitedatabase = await feedback_cog.initialize_sqldb()

        return feedback_cog, user_thread, sqlitedatabase

