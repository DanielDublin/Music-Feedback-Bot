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

    @commands.Cog.listener()
    async def on_ready(self):

        await self.initialize_sqldb()
        await self.threads_manager.on_ready() 
         
    async def initialize_sqldb(self):

            if not self.user_thread:

                data = self.sqlitedatabase.fetch_all_users()

                if data:
                    self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in data}
                    self.threads_manager.user_thread = self.user_thread
                    print(f"user_thread data repopulated from SQLite Database: {len(self.user_thread)} entries.")
                else:
                    print("initialize_sqldb: No data in SQLite Database to repopulate the user_thread dictionary.")

            return self.user_thread


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Only process commands in the feedback channel
        if message.channel.id != FEEDBACK_CHANNEL_ID:
            return
        print(f"Processing message from {message.author.id} in channel {message.channel.id}")
        await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))