import discord
import database.db as db
from discord.ext import commands
from database.threads_db import SQLiteDatabase # Or from database.db import SQLiteDatabase
from .modules.threads_manager import ThreadsManager
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL, FEEDBACK_CATEGORY_ID
from .modules.points_logic import PointsLogic
from .modules.helpers import DiscordHelpers 
from .modules.embeds import Embeds 
from ..general import General

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlitedatabase = SQLiteDatabase()
        self.user_thread = {}  # {user_id: [thread_id, ticket_counter]}
        self.threads_manager = ThreadsManager(bot, self.sqlitedatabase, self.user_thread)

        self.points_logic = PointsLogic(bot, self.user_thread) # Initialize PointsLogic here
        self.discord_helpers = DiscordHelpers(bot) # Initialize DiscordHelpers here
        self.general = bot.get_cog('General')
         
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

        if before.channel.id == FEEDBACK_CHANNEL_ID:

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

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        
        if message.channel.category_id == FEEDBACK_CATEGORY_ID:

            message_content_normalized = message.content.strip().lower()

            user_id = message.author.id
            thread_info = self.user_thread.get(user_id)
            thread_id, ticket_counter = thread_info
            thread = await self.bot.fetch_channel(thread_id)

            # if mfr is in content that was deleted, take away the points
            if "<mfr" in message_content_normalized:

                await self.points_logic.MFR_delete(message, thread, ticket_counter)

            #else if mfs is in content deleted, send message that the user needs more points/contact mods if a mistake
            elif "<mfs" in message_content_normalized:

                # check if the message id is due to manual deletion of the else statement in MFS
                if message.id in self.general.deleted_messages:
                    # if it is, this means that the message was manually deleted and to not throw this embed; delete the id
                    self.general.deleted_messages.discard(message.id)
                    return
                
                else:
                    await self.points_logic.MFS_delete(message, thread, ticket_counter)
                



async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))