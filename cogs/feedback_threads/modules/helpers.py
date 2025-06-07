import asyncio
import discord
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
        from .points_logic import PointsLogic # Local import to avoid circular dependency
        feedback_cog = self.bot.get_cog("FeedbackThreads")
        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")
            return None, None, None, None # Ensure all return values are None if cog missing
        
        user_thread = feedback_cog.user_thread
        thread = None # Initialize thread to None for safety
        ticket_counter = None
        points_logic = None
        user_id = None

        if ctx.author.id in user_thread:
            user_id = str(ctx.author.id)
            print(f"DEBUG: User ID: {user_id}") # Better debug printing
            
            ticket_counter = user_thread[ctx.author.id][1]
            thread_id = user_thread[ctx.author.id][0]
            print(f"DEBUG: Attempting to fetch thread with ID: {thread_id}")

            try:
                thread = await self.bot.fetch_channel(thread_id)
                print(f"DEBUG: Successfully fetched thread: {thread.name} ({thread.id})")
                
                # --- ADD UNARCHIVE LOGIC HERE ---
                if thread.archived:
                    print(f"DEBUG: Thread {thread.name} ({thread.id}) is archived. Attempting to unarchive...")
                    await self.unarchive_thread(thread) # Use self.unarchive_thread
                    await ctx.send(f"DEBUG: Unarchived thread {thread.name} ({thread.id}).")
                # --- END UNARCHIVE LOGIC ---

            except discord.NotFound: # Specifically catch 404 errors for channels
                await ctx.send(f"APP\nMusic Feedback\nAn error occurred: 404 Not Found (error code: 10003): Unknown Channel for user {ctx.author.mention} (ID: {thread_id}).")
                print(f"ERROR: Unknown Channel for user {ctx.author.id}, thread ID {thread_id}. It may have been deleted or inaccessible.")
                # You might want to also remove this invalid thread ID from your database/cache here
                # Example: await feedback_cog.sqlitedatabase.delete_user_thread(user_id)
                # Example: del user_thread[ctx.author.id]
                return None, None, None, None # Crucial: return None if thread not found

            except Exception as e:
                # Catch other potential errors during fetch_channel
                await ctx.send(f"APP\nMusic Feedback\nAn error occurred: {str(e)} in load_feedback_cog while fetching thread.")
                print(f"ERROR: Unexpected error fetching thread for {ctx.author.id}: {e}")
                return None, None, None, None # Return None on other errors
            
            # If we reached here, 'thread' should be assigned, so it's safe to create PointsLogic
            points_logic = PointsLogic(self.bot, user_thread) # PointsLogic depends on thread existing for some reason? Check this.
                                                              # If it *needs* a valid thread object, it should be inside the try/except that fetches thread.

        else:
            # This block means the user has no thread stored.
            # In this case, 'thread' remains None, which is correct.
            print(f"DEBUG: User {ctx.author.name} ({ctx.author.id}) does not have an existing feedback thread in cache.")
            # If no thread, you should probably initiate thread creation flow if that's intended
            # Or simply return None values as no thread is available.
            return None, None, None, None
            
        return thread, ticket_counter, points_logic, user_id # thread can still be None if not found or error
    
    async def load_threads_cog(self, ctx):
    # Get the FeedbackThreads cog instance
        feedback_cog = self.bot.get_cog("FeedbackThreads")

        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")

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


    
