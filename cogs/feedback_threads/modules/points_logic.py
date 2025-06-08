import discord
import database.db as db
from .embeds import Embeds
from .helpers import DiscordHelpers
from data.constants import ADMINS_ROLE_ID, FEEDBACK_CHANNEL_ID

class PointsLogic:
    def __init__(self, bot, user_thread):
        self.bot = bot
        self.user_thread = user_thread
        self.embeds = Embeds(bot, user_thread)
        self.helpers = DiscordHelpers(bot)

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

    async def MFS_to_MFR_edit(self, message: discord.Message, thread, ticket_counter):

        points_to_add = 2
        user_id = message.author.id

        updated_points = await self.helpers.add_points_for_edits(user_id, points_to_add)

        # Send information to user in the original channel
        feedback_channel_message = await message.channel.send( # Use message.channel instead of 'after'
            f"{message.author.mention} edited their message from `<MFS` to `<MFR` and gained **{points_to_add}** MF Points. You now have **{updated_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

        # Send embed to the thread
        # Correct call to MFS_to_MFR_embed, passing correct arguments
        embed = await self.embeds.MFS_to_MFR_embed(message, thread, ticket_counter, points_to_add, updated_points)
        await thread.send(embed=embed)


