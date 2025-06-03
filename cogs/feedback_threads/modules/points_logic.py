import database.db as db
from .embeds import Embeds
import discord
from data.constants import ADMINS_ROLE_ID

class PointsLogic:
    def __init__(self, bot, user_thread):
        self.bot = bot
        self.user_thread = user_thread
        self.embeds = Embeds(bot, user_thread)

    async def send_embed_new_thread(self, ctx, thread):
        try:
            if ctx is None:
                print("Error in send_embed_new_thread: ctx is None")
                raise ValueError("Context (ctx) is required but is None")

            ticket_counter = self.user_thread.get(ctx.author.id, [None, 0])[1]
            embed = await self.embeds.mfs_with_zero_points(ctx, ticket_counter, thread)
            await thread.send(f"<@&{ADMINS_ROLE_ID}>")
            await thread.send(embed=embed)
        except Exception as e:
            print(f"Error in send_embed_new_thread: {e}")
            if ctx:
                await ctx.send(f"An error occurred: {str(e)}")
            else:
                print("Cannot send error message: ctx is None")

    async def send_embed_existing_thread(self, ctx, user_id=None, ticket_counter=None, thread=None, called_from_zero=False):

        user_id = ctx.author.id  # Use ctx, not self.ctx
        ticket_counter = ticket_counter

        if ctx.command.name == "R":
            await self.handle_mfr_submissions(ctx, thread, ticket_counter)

        elif ctx.command.name == "S":

            if called_from_zero:
                await self.handle_zero_points_submission(ctx, thread, ticket_counter)
            
            elif not called_from_zero:
                await self.handle_mfs_submissions(ctx, thread, ticket_counter)

    async def handle_mfr_submissions(self, ctx, thread, ticket_counter):

        print(f"mfr: ctx={ctx}, thread={thread}, ticket_counter={ticket_counter}")

        

        if thread is None:
            print("Error: thread is None")
            if ctx:
                await ctx.send("An internal error occurred: thread not found.")
            return
        
        embed = await self.embeds.mfr(ctx, ticket_counter, thread)
        await thread.send(embed=embed)
            
    async def handle_mfs_submissions(self, ctx, thread, ticket_counter):
        embed = await self.embeds.mfs(ctx, ticket_counter, thread)
        await thread.send(embed=embed)
  

    async def handle_zero_points_submission(self, ctx, thread, ticket_counter):
        try:
            print(f"handle_zero_points_submission: ctx={ctx}, thread={thread}, ticket_counter={ticket_counter}")
            if ctx is None:
                print("Error in handle_zero_points_submission: ctx is None")
                raise ValueError("Context (ctx) is required but is None")

            embed = await self.embeds.mfs_with_zero_points(ctx, ticket_counter, thread)
            print("after mfs_with_zero_points")
            await thread.send(f"<@&{ADMINS_ROLE_ID}>")
            await thread.send(embed=embed)
        except Exception as e:
            print(f"Error in handle_zero_points_submission: {e}")
            if ctx:
                await ctx.send(f"An error occurred: {str(e)}")
            else:
                print("Cannot send error message: ctx is None")

