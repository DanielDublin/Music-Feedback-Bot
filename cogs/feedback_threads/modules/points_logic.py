import discord
import database.db as db
from .embeds import Embeds
from .helpers import DiscordHelpers
from data.constants import ADMINS_ROLE_ID, FEEDBACK_CHANNEL_ID

class PointsLogic:
    def __init__(self, bot, user_thread):
        self.bot = bot
        self.pfp_url =""
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

    async def MFS_to_MFR_edit(self, before: discord.Message, after: discord.Message, thread, ticket_counter):

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        shortened_before_content = await self.helpers.shorten_message(before.content, 1000)
        shortened_after_content = await self.helpers.shorten_message(after.content, 1000)
        
        user_id = str(after.author.id)
        points_to_add = 2
    
        await self.helpers.add_points_for_edits(user_id, points_to_add)
        total_points = int(await db.fetch_points(str(user_id)))

        # send information to user in the original channel
        await after.channel.send( 
            f"{after.author.mention} edited their message from `<MFS` to `<MFR` and gained **{points_to_add}** MF Points. You now have **{total_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

        # send ticket
        embed = await self.embeds.MFS_to_MFR_embed(
        original_message=shortened_before_content,
        shortened_message=shortened_after_content,
        ctx=after.channel, 
        thread=thread,
        ticket_counter=ticket_counter,
        points_added=points_to_add,
        total_points=total_points
        )
        await thread.send(embed=embed)

        # send log
        log_embed = discord.Embed(color=0x7e016f)
        log_embed.add_field(
            name=f"Feedback Edit - {self.helpers.get_formatted_time()}",
            value=(
                f"<@{user_id}> has **edited** their message from `<MFS` to `<MFR`. "
                f"They gained **{points_to_add}** points and now have **{total_points}** MF points.\n\n"
                f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url}) - Edited Message: {after.jump_url}"
            ),
            inline=False
        )
        log_embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await channel.send(embed=log_embed) 

    async def MFR_to_MFS_edit(self, before: discord.Message, after: discord.Message, thread, ticket_counter):

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        shortened_before_content = await self.helpers.shorten_message(before.content, 1000)
        shortened_after_content = await self.helpers.shorten_message(after.content, 1000)
        
        user_id = str(after.author.id)
        points_to_remove = 2
    
        await self.helpers.remove_points_for_edits(user_id, points_to_remove)
        total_points = int(await db.fetch_points(str(user_id)))


        # if the user has greater than the points that need to be removed, it's a valid edit
        if total_points > points_to_remove:

            # send information to user in the original channel
            await after.channel.send( 
                f"{after.author.mention} edited their message from `<MFR` to `<MFS` and used **{points_to_remove}** MF Points. You now have **{total_points}** MF Points."
                f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

            # send ticket
            embed = await self.embeds.MFR_to_MFS_embed(
            original_message=shortened_before_content,
            shortened_message=shortened_after_content,
            ctx=after.channel, 
            thread=thread,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
            )
            await thread.send(embed=embed)

            # send log
            log_embed = discord.Embed(color=0x7e016f)
            log_embed.add_field(
                name=f"Feedback Edit - {self.helpers.get_formatted_time()}",
                value=(
                    f"<@{user_id}> has **edited** their message from `<MFR` to `<MFS`. "
                    f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url}) - Edited Message: {after.jump_url}"
                ),
                inline=False
            )
            log_embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=log_embed) 
        
        # otherwise, they don't have the points to use
        else:

            # delete the post
            await after.delete()

            # reset the points
            await db.reset_points(user_id)
            total_points = int(await db.fetch_points(str(user_id)))

            # send information to user
            await after.channel.send( 
                f"{after.author.mention}, this system is 1-for-1 and you do not have enough MF Points available to use. Give feedback first."
                f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>." )
            
            # send ticket
            embed = await self.embeds.MFR_to_MFS_with_no_points_embed(
            original_message=shortened_before_content,
            shortened_message=shortened_after_content,
            ctx=after.channel, 
            thread=thread,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
            )
            await thread.send(embed=embed)

            # send the log
            log_embed = discord.Embed(color=0x7e016f)
            log_embed.add_field(
                name=f"Feedback Edit - {self.helpers.get_formatted_time()}",
                value=(
                    f"<@{user_id}> has **edited** their message from `<MFR` to `<MFS` without enough points. "
                    f"They tried to use **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
                ),
                inline=False
            )
            log_embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=log_embed)




