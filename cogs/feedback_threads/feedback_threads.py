import discord
from discord.ext import commands

# Assuming these paths are correct
from database.threads_db import SQLiteDatabase # Or from database.db import SQLiteDatabase
from .modules.threads_manager import ThreadsManager
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlitedatabase = SQLiteDatabase()
        self.user_thread = {}  # {user_id: [thread_id, ticket_counter]}
        self.threads_manager = ThreadsManager(bot, self.sqlitedatabase, self.user_thread)
         
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

async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))