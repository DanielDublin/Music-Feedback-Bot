import discord
import logging
from discord.ext import commands

logger = logging.getLogger(__name__)
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
                    logger.info(f"user_thread repopulated from SQLite Database: {len(self.user_thread)} entries")
                else:
                    logger.warning("initialize_sqldb: No data in SQLite Database to repopulate the user_thread dictionary")

            return self.user_thread
    
    async def cog_load(self):
        data = self.sqlitedatabase.fetch_all_users()
        if data:
            self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in data}
            self.threads_manager.user_thread = self.user_thread
            logger.info(f"user_thread loaded from SQLite: {len(self.user_thread)} entries")
        else:
            logger.warning("cog_load: SQLite database is empty")

    async def record_feedback(self, ctx: commands.Context):
        """Called by general.py after a successful <MFR. Returns (thread, ticket_counter) or None."""
        try:
            await self.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
        except Exception:
            logger.error("record_feedback: thread operation failed for %s", ctx.author.id, exc_info=True)
            return None
        thread_info = self.user_thread.get(ctx.author.id)
        if thread_info is None:
            return None
        thread_id, ticket_counter = thread_info
        try:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
        except Exception:
            logger.error("record_feedback: failed to fetch thread %s for %s", thread_id, ctx.author.id, exc_info=True)
            return None
        return thread, ticket_counter

    async def record_spend(self, ctx: commands.Context):
        """Called by general.py after a successful <MFS. Returns (thread, ticket_counter) or None."""
        try:
            await self.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)
        except Exception:
            logger.error("record_spend: thread operation failed for %s", ctx.author.id, exc_info=True)
            return None
        thread_info = self.user_thread.get(ctx.author.id)
        if thread_info is None:
            return None
        thread_id, ticket_counter = thread_info
        try:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
        except Exception:
            logger.error("record_spend: failed to fetch thread %s for %s", thread_id, ctx.author.id, exc_info=True)
            return None
        return thread, ticket_counter

    async def record_admin_adjustment(self, interaction: discord.Interaction, target: discord.Member):
        """Called by admin.py for /mfpoints. Returns thread or None on failure."""
        from cogs.feedback_threads.modules.ctx_class import ContextLike
        target_ctx = ContextLike(interaction=interaction, command=None, custom_author=target)
        try:
            await self.threads_manager.check_if_feedback_thread(target_ctx, called_from_zero=False)
        except Exception:
            logger.error("record_admin_adjustment: thread operation failed for %s", target.id, exc_info=True)
            return None
        thread_info = self.user_thread.get(target.id)
        if thread_info is None:
            return None
        thread_id, _ = thread_info
        try:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
        except Exception:
            logger.error("record_admin_adjustment: failed to fetch thread %s for %s", thread_id, target.id, exc_info=True)
            return None
        return thread

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        try:
            if before.author.bot:
                return

            if before.channel.id == FEEDBACK_CHANNEL_ID:

                before_content_normalized = before.content.strip().lower()
                after_content_normalized = after.content.strip().lower()

                user_id = after.author.id
                thread_info = self.user_thread.get(user_id)
                if thread_info is None:
                    return
                thread_id, ticket_counter = thread_info
                thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
                if thread is None:
                    return

                # MFS to MFR
                if "<mfs" in before_content_normalized and "<mfr" in after_content_normalized:

                    await self.points_logic.MFS_to_MFR_edit(before, after, thread, ticket_counter)

                # MFR to MFS
                elif "<mfr" in before_content_normalized and "<mfs" in after_content_normalized:

                    await self.points_logic.MFR_to_MFS_edit(before, after, thread, ticket_counter)
        except Exception:
            logger.error("on_message_edit failed for message %s", before.id, exc_info=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        try:
            if message.author.bot:
                return

            if message.channel.category_id == FEEDBACK_CATEGORY_ID:

                message_content_normalized = message.content.strip().lower()

                user_id = message.author.id
                thread_info = self.user_thread.get(user_id)
                if thread_info is None:
                    return
                thread_id, ticket_counter = thread_info
                thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
                if thread is None:
                    return

                # if mfr is in content that was deleted, take away the points
                if "<mfr" in message_content_normalized:

                    await self.points_logic.MFR_delete(message, thread, ticket_counter)

                #else if mfs is in content deleted, send message that the user needs more points/contact mods if a mistake
                elif "<mfs" in message_content_normalized:

                    # lazy-load General cog in case it wasn't ready at __init__ time
                    if self.general is None:
                        self.general = self.bot.get_cog('General')

                    # check if the message id is due to manual deletion of the else statement in MFS
                    if self.general is not None and message.id in self.general.feedback.deleted_messages:
                        # if it is, this means that the message was manually deleted and to not throw this embed; delete the id
                        self.general.feedback.deleted_messages.discard(message.id)
                        return

                    else:
                        await self.points_logic.MFS_delete(message, thread, ticket_counter)
        except Exception:
            logger.error("on_message_delete failed for message %s", message.id, exc_info=True)
                



async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))