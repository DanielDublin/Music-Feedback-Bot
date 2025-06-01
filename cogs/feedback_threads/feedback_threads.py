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
        """
        This method runs once when the bot is fully ready.
        It's the ideal place to:
        1. Initialize the threads_manager's channel.
        2. Repopulate user_thread from the database.
        """
        print("FeedbackThreads cog: Bot is ready. Running on_ready tasks.")
        await self.threads_manager.on_ready() # Call ThreadsManager's on_ready to set its channel

        # Now, initialize the user_thread dictionary from the database
        await self.initialize_sqldb() # Await this call

        print("FeedbackThreads cog: Initialization complete.")


    async def initialize_sqldb(self):
            print(f"initialize_sqldb: self.user_thread (before fetch) = {self.user_thread}")

            if not self.user_thread:
                print("initialize_sqldb: Dictionary is empty, attempting to fetch from DB.")
                try:
                    data = self.sqlitedatabase.fetch_all_users()
                except Exception as e:
                    print(f"initialize_sqldb: Error fetching data from DB: {e}")
                    return
                print(f"initialize_sqldb: Raw data fetched from DB: {data}") # <--- ADD THIS LINE
                if data:
                    self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in data}
                    self.threads_manager.user_thread = self.user_thread
                    print(f"initialize_sqldb: user_thread data repopulated from SQLite Database: {len(self.user_thread)} entries.")
                    print(f"initialize_sqldb: Current user_thread after repopulation: {self.user_thread}") # <--- ADD THIS LINE
                else:
                    print("initialize_sqldb: No data in SQLite Database to repopulate the user_thread dictionary.")
            else:
                print("initialize_sqldb: user_thread already populated. Skipping database fetch.")

            return self.user_thread


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Only process messages in the feedback channel
        if message.channel.id != FEEDBACK_CHANNEL_ID:
            return

        ctx = await self.bot.get_context(message)

        # Only process if the message is a command
        if ctx.command is None:
            return

        # No need to call self.threads_manager.on_ready() here
        # No need for mfr_points or points unless explicitly used later

        try:
            await self.threads_manager.check_if_feedback_thread(ctx)
        except Exception as e:
            print(f"Error while checking if feedback thread: {e}")
            # Consider sending an error message back to the user or logging more details
            return

        await self.bot.process_commands(message) # Crucial to allow other commands to run


async def setup(bot):
    print("Setting up FeedbackThreads cog...")
    await bot.add_cog(FeedbackThreads(bot))
    print("FeedbackThreads cog setup complete.")