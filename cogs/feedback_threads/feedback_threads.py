import discord
from discord.ext import commands

# Assuming these paths are correct
from database.threads_db import SQLiteDatabase # Or from database.db import SQLiteDatabase
from .modules.threads_manager import ThreadsManager
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL, AUDIO_FEEDBACK, LYRIC_FEEDBACK
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
        
        if before.channel.id == AUDIO_FEEDBACK or before.channel.id == LYRIC_FEEDBACK:

            before_content_normalized = before.content.strip().lower()
            after_content_normalized = after.content.strip().lower()

            user_id = after.author.id
            thread_info = self.user_thread.get(user_id)
            thread_id, ticket_counter = thread_info
            thread = await self.bot.fetch_channel(thread_id)

            # MFS to MFR
            if "<mfs" in before_content_normalized and "<mfr" in after_content_normalized: 

                await self.points_logic.MFS_to_MFR_edit(before, after, thread, ticket_counter)

            # MFR to MFS
            elif "<mfr" in before_content_normalized and "<mfs" in after_content_normalized:

                await self.points_logic.MFR_to_MFS_edit(before, after, thread, ticket_counter)



async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))