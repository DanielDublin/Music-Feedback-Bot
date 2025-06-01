import discord
from datetime import datetime
import asyncio
from database.db import fetch_points
from .helpers import DiscordHelpers
from data.constants import THREADS_CHANNEL

class ThreadsManager:
    def __init__(self, bot, sqlitedatabase, user_thread):
        self.bot = bot
        self.sqlitedatabase = sqlitedatabase
        # self.embeds = embeds
        self.user_thread = user_thread
        self.threads_channel = None
        self.helpers = DiscordHelpers(bot)


    async def on_ready(self):

        await self.bot.wait_until_ready()
        self.threads_channel = self.bot.get_channel(THREADS_CHANNEL)

        if not self.threads_channel:
            print(f"Error: THREADS_CHANNEL with ID {THREADS_CHANNEL} not found.")

    async def check_if_feedback_thread(self, ctx):

            # if thread exists for user
            if ctx.author.id in self.user_thread: 
                await self.existing_thread(ctx)
            else:
                await self.create_new_thread(ctx)

    async def create_new_thread(self, ctx):

        # channel to send threads for all members
        message = await self.threads_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

        thread = await self.threads_channel.create_thread(
            name=f"{ctx.author.name} - {ctx.author.id}",
            message=message,
            reason="Creating a feedback log thread",
            auto_archive_duration=60  # Auto-archive after 1 hour of inactivity
        )

        # insert new user into dictionary
        self.user_thread[ctx.author.id] = [thread.id, 1]

        # insert new user into database
        self.sqlitedatabase.insert_user(ctx.author.id, thread.id, 1)

    async def existing_thread(self, ctx):

        # get the thread from the dictionary
        thread_id = self.user_thread[ctx.author.id][0]
        existing_thread = await self.bot.fetch_channel(thread_id)

        # unarchive the thread 
        await self.helpers.unarchive_thread(existing_thread)

        # send embed
        await existing_thread.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

        # rearchive
        await self.helpers.archive_thread(existing_thread)

        return existing_thread

async def setup(bot):
    await bot.add_cog(ThreadsManager(bot))
        
        
        
                