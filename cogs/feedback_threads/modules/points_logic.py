import database.db as db
from .embeds import Embeds
import discord
from data.constants import ADMINS_ROLE_ID

class PointsLogic:
    def __init__(self, bot, user_thread):
        self.bot = bot
        self.user_thread = user_thread
        self.embeds = Embeds(bot, user_thread)

    async def send_embed_new_thread(self, ctx, thread, ticket_counter, called_from_zero=False):

        user_id = ctx.author.id
        ticket_counter = ticket_counter

        if ctx.command.name == "R":
            await self.handle_mfr_submissions(ctx, thread, ticket_counter)

        elif ctx.command.name == "S":

            if called_from_zero:
                await self.handle_zero_points_submission(ctx, thread, ticket_counter)
            
            elif not called_from_zero:
                await self.handle_mfs_submissions(ctx, thread, ticket_counter)

    async def send_embed_existing_thread(self, ctx, user_id=None, ticket_counter=None, thread=None, called_from_zero=False):

        user_id = ctx.author.id
        ticket_counter = ticket_counter

        if ctx.command.name == "R":
            await self.handle_mfr_submissions(ctx, thread, ticket_counter)

        elif ctx.command.name == "S":

            if called_from_zero:
                await self.handle_zero_points_submission(ctx, thread, ticket_counter)
            
            elif not called_from_zero:
                await self.handle_mfs_submissions(ctx, thread, ticket_counter)

    async def handle_mfr_submissions(self, ctx, thread, ticket_counter):
        
        embed = await self.embeds.mfr(ctx, ticket_counter, thread)
        await thread.send(embed=embed)
            
    async def handle_mfs_submissions(self, ctx, thread, ticket_counter):

        embed = await self.embeds.mfs(ctx, ticket_counter, thread)
        await thread.send(embed=embed)

    async def handle_zero_points_submission(self, ctx, thread, ticket_counter):

        embed = await self.embeds.mfs_with_zero_points(ctx, ticket_counter, thread)
        await thread.send(f"<@&{ADMINS_ROLE_ID}>")
        await thread.send(embed=embed)

