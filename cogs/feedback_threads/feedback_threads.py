import discord
from discord.ext import commands

# Assuming these paths are correct
from database.threads_db import SQLiteDatabase # Or from database.db import SQLiteDatabase
from .modules.threads_manager import ThreadsManager
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL
from .modules.points_logic import PointsLogic
from .modules.helpers import DiscordHelpers 
from .modules.embeds import Embeds 

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlitedatabase = SQLiteDatabase()
        self.user_thread = {}  # {user_id: [thread_id, ticket_counter]}
        self.threads_manager = ThreadsManager(bot, self.sqlitedatabase, self.user_thread)

        self.points_logic = PointsLogic(bot, self.user_thread) # Initialize PointsLogic here
        self.discord_helpers = DiscordHelpers(bot) # Initialize DiscordHelpers here


         
    async def initialize_sqldb(self):

            if not self.user_thread:

                data = self.sqlitedatabase.fetch_all_users()

                if data:
                    self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in data}
                    self.threads_manager.user_thread = self.user_thread
                    print(f"user_thread repopulated from SQLite Database: {len(self.user_thread)} entries")
                else:
                    print("initialize_sqldb: No data in SQLite Database to repopulate the user_thread dictionary")

            return self.user_thread
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        
        before_content_normalized = before.content.strip().lower()
        after_content_normalized = after.content.strip().lower()

        if before.channel.id == FEEDBACK_CHANNEL_ID:

            # MFS to MFR
            if before_content_normalized == "<mfs" and after_content_normalized == "<mfr": 

                user_id = after.author.id
                print(f"Processing MFS to MFR edit for user {user_id}")
                
                thread_info = self.user_thread.get(user_id)
                print(f"Thread info for user {user_id}: {thread_info}")

                if not thread_info:
                    print(f"No thread info found for user {user_id}. Cannot process MFS to MFR edit.")
                    # Optionally, you might want to send a message to the user or log this
                    return

                thread_id, ticket_counter = thread_info
                print(f"Thread ID: {thread_id}, Ticket Counter: {ticket_counter}")
                
                # Fetch the actual thread object
                thread = await self.bot.fetch_channel(thread_id)
                print(f"Thread object: {thread}")

                # Now call MFS_to_MFR_edit with the correct arguments
                try:
                    await self.points_logic.MFS_to_MFR_edit(after, thread, ticket_counter)
                except Exception as e:
                    print(f"Error processing MFS to MFR edit for user {user_id}: {e}")


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))