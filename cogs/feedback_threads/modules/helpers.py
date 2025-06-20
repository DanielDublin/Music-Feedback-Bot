import asyncio
import discord
import database.db as db
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

    async def load_feedback_cog(self, ctx=None, user_id=None):
        from .points_logic import PointsLogic

        feedback_cog = self.bot.get_cog("FeedbackThreads")
        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")
            return
        
        if ctx.author.id in feedback_cog.user_thread:
            user_thread = feedback_cog.user_thread
            points_logic = PointsLogic(self.bot, user_thread)

            user_id = str(ctx.author.id)

            ticket_counter = user_thread[ctx.author.id][1]
            thread_id = user_thread[ctx.author.id][0]

            thread = await self.bot.fetch_channel(thread_id)
        else:
            pass

        return thread, ticket_counter, points_logic, user_id
    
    async def load_threads_cog(self, ctx):

        # Get the FeedbackThreads cog instance
        feedback_cog = self.bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")
            return None, None, None  # <-- Return here to avoid AttributeError

        # Access the shared user_thread dict and ThreadsManager instance
        user_thread = feedback_cog.user_thread
        sqlitedatabase = await feedback_cog.initialize_sqldb()

        return feedback_cog, user_thread, sqlitedatabase

    
    async def get_thread_id_no_ctx(bot, user_id: int):

        feedback_cog = bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            print("Feedback cog not loaded.")
            return None

        user_thread = feedback_cog.user_thread
        print(user_thread)

        thread_info = user_thread.get(user_id)
        if thread_info:
            thread_id = thread_info[0]  # first item is the thread ID
            return thread_id
        else:
            print(f"No thread found for user ID: {user_id}")
            return None 
        
    async def delete_user_from_user_thread(bot, user_id: int):
        feedback_cog = bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            print("Feedback cog not loaded.")
            return

        user_thread = feedback_cog.user_thread

        if user_id in user_thread:
            user_thread.pop(user_id)


    async def delete_user_from_db(bot, user_id: int):

        feedback_cog = bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            print("Feedback cog not loaded.")
            return

        feedback_cog.sqlitedatabase.delete_user(user_id)

    async def add_points_for_edits(self, user_id: int, points_to_add: int):

        await db.add_points(user_id, points_to_add)

        return
    
    async def remove_points_for_edits(self, user_id: int, points_to_remove: int):

        await db.reduce_points(user_id, points_to_remove)

        return
    
    async def shorten_message(self, content: str, max_length: int):
        if len(content) > max_length:
            return content[:max_length - 3] + "..."
        
        return content



    
