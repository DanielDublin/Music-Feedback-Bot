import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from .tracker import Tracker
from .embed_pagination import EmbedPagination
import asyncio

class FeedbackChannelEmbeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_sticky_embed = None

    @commands.Cog.listener()
    async def on_message(self, message):
        feedback_channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        if message.channel != feedback_channel or message.author.bot:
            return

        try:
            tracker_cog = self.bot.get_cog("Tracker")
            if not tracker_cog:
                print("Tracker cog not found")
                return
        except Exception as e:
            print(f"Tracker cog not found: {e}")
            return
        
        # prevent race condition; allows db to update before sending embed
        await asyncio.sleep(0.5)

        try:
            requests = await tracker_cog.pull_db_feedback()
        except Exception as e:
            print(f"Error pulling feedback requests: {e}")
            return

        print("Fetched requests:", requests)

        if self.old_sticky_embed:
            try:
                await self.old_sticky_embed.delete()
            except discord.errors.NotFound:
                pass  # Ignore if the old embed was already deleted


        pagination = EmbedPagination(self.bot, requests, items_per_page=5)
        embed = pagination.create_embed()

        self.old_sticky_embed = await feedback_channel.send(embed=embed, view=pagination)
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(FeedbackChannelEmbeds(bot))