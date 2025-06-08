import discord
from datetime import datetime
import asyncio
from .helpers import DiscordHelpers
from .points_logic import PointsLogic
from .embeds import Embeds
from data.constants import THREADS_CHANNEL

class ThreadsManager:
    def __init__(self, bot, sqlitedatabase, user_thread):
        self.bot = bot
        self.sqlitedatabase = sqlitedatabase
        self.user_thread = user_thread
        self.points_logic = PointsLogic(bot, user_thread)
        self.threads_channel = None
        self.helpers = DiscordHelpers(bot)
        self.embeds = Embeds(bot, user_thread)

    async def on_ready(self):

        await self.bot.wait_until_ready()
        self.threads_channel = self.bot.get_channel(THREADS_CHANNEL)

        if not self.threads_channel:
            print(f"Error: THREADS_CHANNEL with ID {THREADS_CHANNEL} not found.")

    async def check_if_feedback_thread(self, ctx, called_from_zero=False):
            
        if ctx.author.id in self.user_thread:

            await ctx.send(f"User {ctx.author.id} already has a feedback thread.")

            await self.existing_thread(ctx, called_from_zero)

            await ctx.send(f"User {ctx.author.id} has a feedback thread. DONE")
            
        else:

            await ctx.send(f"User {ctx.author.id} does not have a feedback thread.")

            await self.create_new_thread(ctx, called_from_zero)
            await ctx.send(f"User {ctx.author.id} created a feedback thread.")

    async def create_new_thread(self, ctx, called_from_zero=False):

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

        # get the ticket counter
        ticket_counter = self.user_thread[ctx.author.id][1]

        # send embed
        await self.points_logic.send_embed_new_thread(
            ctx=ctx, 
            thread=thread, 
            ticket_counter=ticket_counter, 
            called_from_zero=called_from_zero
        )

        # archive the thread
        await self.helpers.archive_thread(thread)

        # return for archive use
        return thread

    async def existing_thread(self, ctx, called_from_zero=False):

        # increase ticket counter in dictionary
        self.user_thread[ctx.author.id][1] += 1

        # update database
        self.sqlitedatabase.update_ticket_counter(ctx.author.id, self.user_thread[ctx.author.id][1])

        # get the thread and ticket_counter from the dictionary
        thread_id = self.user_thread[ctx.author.id][0]
        await ctx.send(f"thread_id: {thread_id} in existing_thread") # print(thread_id)
        existing_thread = await self.bot.fetch_channel(thread_id)
        await ctx.send(f"existing_thread: {existing_thread} in existing_thread") # print(existing_thread)

        ticket_counter = self.user_thread[ctx.author.id][1]
        await ctx.send(f"ticket_counter: {ticket_counter} in existing_thread") # print(ticket_counter)

        # unarchive the thread 
        await self.helpers.unarchive_thread(existing_thread)
        await ctx.send("unarchived")

        # send embed
        await self.points_logic.send_embed_existing_thread(
            ctx=ctx,
            user_id=ctx.author.id,
            ticket_counter=ticket_counter,
            thread=existing_thread,
            called_from_zero=called_from_zero
        )
        await ctx.send("sent embed")

        # rearchive
        await self.helpers.archive_thread(existing_thread)

        # return for archive use
        return existing_thread

async def setup(bot):
    await bot.add_cog(ThreadsManager(bot))
        
        
        
                