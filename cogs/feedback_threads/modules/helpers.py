import asyncio
from datetime import datetime
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

    def generate_message_link(self, ctx):
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    def get_formatted_time(self):
        current_time = datetime.now()
        return current_time.strftime("%Y-%d-%m %H:%M")

    async def load_feedback_cog(self, ctx):
        from .points_logic import PointsLogic
        feedback_cog = self.bot.get_cog("FeedbackThreads")
        if not feedback_cog:
            await ctx.send("Feedback cog not loaded.")
            return

        user_thread = feedback_cog.user_thread
        points_logic = PointsLogic(self.bot, user_thread, ctx)

        user_id = str(ctx.author.id)
        print(user_id)

        try:
            ticket_counter = user_thread[ctx.author.id][1]
            thread_id = user_thread[ctx.author.id][0]
        except KeyError:
            await ctx.send("You do not have a thread.")
            return

        thread = await self.bot.fetch_channel(thread_id)
        print(thread)

        return thread, ticket_counter, points_logic, user_id
