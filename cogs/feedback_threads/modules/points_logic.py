import asyncio
import discord
import logging
from .embeds import Embeds
from .helpers import DiscordHelpers
from data.constants import ADMINS_ROLE_ID, AUDIO_FEEDBACK, FEEDBACK_CHANNEL_ID, FEEDBACK_ACCESS_CHANNEL_ID
from ml_model.ml_model_loader import quality_qualifies_for_bonus

logger = logging.getLogger(__name__)

class PointsLogic:
    def __init__(self, bot, user_thread):
        self.bot = bot
        self.user_thread = user_thread
        self.embeds = Embeds(bot, user_thread)
        self.helpers = DiscordHelpers(bot)
        # Per-user locks guard read-then-write point sequences (edits, deletes)
        # so concurrent events for the same user can't race the DB into a
        # negative or stale balance.
        self._user_locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        lock = self._user_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._user_locks[user_id] = lock
        return lock

    async def send_embed_new_thread(self, ctx, thread, ticket_counter, called_from_zero=False):

        if ctx.command is None:
            return

        user_id = ctx.author.id
        ticket_counter = ticket_counter

        if ctx.command.name == "R":
            await self.handle_mfr_submissions(ctx, thread, ticket_counter)

        elif ctx.command.name == "S":

            if called_from_zero:
                await self.handle_zero_points_submission(ctx.message, thread, ticket_counter)
            
            elif not called_from_zero:
                await self.handle_mfs_submissions(ctx, thread, ticket_counter)

    async def send_embed_existing_thread(self, ctx, user_id=None, ticket_counter=None, thread=None, called_from_zero=False):

        if ctx.command is None:
            return

        user_id = ctx.author.id
        ticket_counter = ticket_counter

        if ctx.command.name == "R":
            await self.handle_mfr_submissions(ctx, thread, ticket_counter)

        elif ctx.command.name == "S":

            if called_from_zero:
                await self.handle_zero_points_submission(ctx.message, thread, ticket_counter)
            
            elif not called_from_zero:
                await self.handle_mfs_submissions(ctx, thread, ticket_counter)

    async def handle_mfr_submissions(self, ctx, thread, ticket_counter):
        embed = await self.embeds.mfr(ctx, ticket_counter)
        try:
            await thread.send(embed=embed)
        except Exception:
            logger.error("Error sending MFR embed to thread %s", thread.id, exc_info=True)

    async def handle_mfs_submissions(self, ctx, thread, ticket_counter):
        embed = await self.embeds.mfs(ctx, ticket_counter)
        try:
            await thread.send(embed=embed)
        except Exception:
            logger.error("Error sending MFS embed to thread %s", thread.id, exc_info=True)

    async def handle_zero_points_submission(self, message: discord.Message, thread, ticket_counter: int):

        deleted_content = self.helpers.shorten_message(message.content, 1000)

        try:
            embed = await self.embeds.mfs_with_zero_points(message, ticket_counter, deleted_content)
        except Exception:
            logger.error("Error creating mfs_with_zero_points embed", exc_info=True)
            return
        await thread.send(f"<@&{ADMINS_ROLE_ID}>")
        await thread.send(embed=embed)

    async def MFS_to_MFR_edit(self, before: discord.Message, after: discord.Message, thread, ticket_counter):

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        shortened_before_content = self.helpers.shorten_message(before.content, 1000)
        shortened_after_content = self.helpers.shorten_message(after.content, 1000)
        
        user_id = str(after.author.id)
        points_to_add = 2
    
        await self.bot.db.add_points(user_id, points_to_add)
        total_points = int(await self.bot.db.fetch_points(str(user_id)))

        # send information to user in the original channel
        await after.channel.send( 
            f"{after.author.mention} edited their message from `<MFS` to `<MFR` and gained **{points_to_add}** MF Points. You now have **{total_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_ACCESS_CHANNEL_ID}>.")

        # send ticket
        embed = await self.embeds.MFS_to_MFR_embed(
        original_message=shortened_before_content,
        shortened_message=shortened_after_content,
        ticket_counter=ticket_counter,
        points_added=points_to_add,
        total_points=total_points
        )
        try:
            await thread.send(embed=embed)
        except Exception:
            logger.error("Error sending MFS_to_MFR embed to thread %s", thread.id, exc_info=True)

        # send log
        log_embed = discord.Embed(color=0x7e016f)
        log_embed.add_field(
            name=f"Feedback Edit - {self.helpers.get_formatted_time()}",
            value=(
                f"<@{user_id}> has **edited** their message from `<MFS` to `<MFR`. "
                f"They gained **{points_to_add}** points and now have **{total_points}** MF points.\n\n"
                f"🔗 [Edited Feedback]({after.jump_url})\n"
                f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
            ),
            inline=False
        )
        log_embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        try:
            await channel.send(embed=log_embed)
        except Exception:
            logger.error("Error sending MFS_to_MFR log to channel", exc_info=True)

    async def MFR_to_MFS_edit(self, before: discord.Message, after: discord.Message, thread, ticket_counter):

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        shortened_before_content = self.helpers.shorten_message(before.content, 1000)
        shortened_after_content = self.helpers.shorten_message(after.content, 1000)

        user_id = str(after.author.id)
        points_to_remove = 2

        async with self._lock_for(user_id):
            points_available = int(await self.bot.db.fetch_points(str(user_id)))

            if points_available >= points_to_remove:
                await self.bot.db.reduce_points(user_id, points_to_remove)
                total_points = int(await self.bot.db.fetch_points(str(user_id)))
                enough_points = True
            else:
                await self.bot.db.reset_points(user_id)
                total_points = int(await self.bot.db.fetch_points(str(user_id)))
                enough_points = False

        if enough_points:

            # send information to user in the original channel
            await after.channel.send(
                f"{after.author.mention} edited their message from `<MFR` to `<MFS` and used **{points_to_remove}** MF Points. You now have **{total_points}** MF Points."
                f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_ACCESS_CHANNEL_ID}>.")

            # send ticket
            embed = await self.embeds.MFR_to_MFS_embed(
            original_message=shortened_before_content,
            shortened_message=shortened_after_content,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
            )
            try:
                await thread.send(embed=embed)
            except Exception:
                logger.error("Error sending MFR_to_MFS embed to thread %s", thread.id, exc_info=True)

            # send log
            log_embed = discord.Embed(color=0x7e016f)
            log_embed.add_field(
                name=f"Feedback Edit - {self.helpers.get_formatted_time()}",
                value=(
                    f"<@{user_id}> has **edited** their message from `<MFR` to `<MFS`. "
                    f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                    f"🔗 [Edited Feedback]({after.jump_url})\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
                ),
                inline=False
            )
            log_embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            try:
                await channel.send(embed=log_embed)
            except Exception:
                logger.error("Error sending MFR_to_MFS log to channel", exc_info=True)

        # otherwise, they don't have the points to use
        else:

            # delete the post
            await after.delete()

            # send information to user
            await after.channel.send(
                f"{after.author.mention}, this system is 1-for-1 and you do not have enough MF Points available to use. Give feedback first."
                f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_ACCESS_CHANNEL_ID}>." )

            # send ticket
            embed = await self.embeds.MFR_to_MFS_with_no_points_embed(
            original_message=shortened_before_content,
            shortened_message=shortened_after_content,
            ticket_counter=ticket_counter,
            points_removed=points_to_remove,
            total_points=total_points
            )
            try:
                await thread.send(embed=embed)
            except Exception:
                logger.error("Error sending MFR_to_MFS_no_points embed to thread %s", thread.id, exc_info=True)

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
            log_embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            try:
                await channel.send(embed=log_embed)
            except Exception:
                logger.error("Error sending MFR_to_MFS_no_points log to channel", exc_info=True)

    
    async def MFR_delete(self, message: discord.Message, thread: discord.Thread, ticket_counter: int):
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        if not channel:
            return

        deleted_content = self.helpers.shorten_message(message.content, 1000)
        user_id = str(message.author.id)

        # If message was posted during a Prime Time window and content is cached,
        # check whether it qualified for double points. Mirrors the MFR bonus
        # rule in general.py: ML quality check in audio channel, 300-char in
        # lyric channel, 300-char fallback when ML is unavailable.
        prime_time_cog = self.bot.get_cog("PrimeTime")
        if prime_time_cog and message.content and prime_time_cog.was_during_prime_time(message.created_at):
            feedback_text = message.content
            if feedback_text.upper().startswith("<MFR"):
                feedback_text = feedback_text[4:].lstrip()
            qualifies = None
            if message.channel.id == AUDIO_FEEDBACK:
                qualifies = await quality_qualifies_for_bonus(feedback_text)
            if qualifies is None:
                qualifies = len(feedback_text) >= 300
            points_to_remove = 2 if qualifies else 1
        else:
            points_to_remove = 1

        async with self._lock_for(user_id):
            points_available = await self.bot.db.fetch_points(user_id)
            await self.bot.db.reduce_points(user_id, points_to_remove)
            total_points = await self.bot.db.fetch_points(user_id)

        if points_available > 0:

            delete_notice = await message.channel.send(
                f"{message.author.mention} deleted their feedback and lost **{points_to_remove}** MF Points. You now have **{total_points}** MF Points.\n\n"
                f"You will need to repost the feedback or give feedback again to regain the point. Visit <#{FEEDBACK_ACCESS_CHANNEL_ID}> for more information."
            )
            await delete_notice.delete(delay=60)

            embed = await self.embeds.MFR_to_delete_embed(
                deleted_content=deleted_content,
                ticket_counter=ticket_counter,
                points_removed=points_to_remove,
                total_points=total_points
            )
            try:
                await thread.send(embed=embed)
            except Exception:
                logger.error("Error sending thread embed", exc_info=True)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(
                name=f"Feedback Deletion - {self.helpers.get_formatted_time()}",
                value=(
                    f"<@{user_id}> has **deleted** their feedback containing `<MFR`. "
                    f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
                ),
                inline=False
            )
            embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            await channel.send(embed=embed)

        elif points_available == 0:

            await self.bot.db.reset_points(user_id)
            total_points = int(await self.bot.db.fetch_points(str(user_id)))

            await channel.send(f"<@&{ADMINS_ROLE_ID}>")

            await message.channel.send(
                f"{message.author.mention} deleted their feedback but didn't have **{points_to_remove}** MF Points to use. You may have submitted a song since giving feedback.\n\n"
                f"You will need to repost the feedback or give feedback again to regain the point. Visit <#{FEEDBACK_ACCESS_CHANNEL_ID}> for more information."
            )

            embed = await self.embeds.MFR_to_delete_embed_with_no_points(
                deleted_content=deleted_content,
                ticket_counter=ticket_counter,
                points_removed=points_to_remove,
                total_points=total_points
            )
            await thread.send(embed=embed)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(
                name=f"Feedback Deletion - {self.helpers.get_formatted_time()}",
                value=(
                    f"<@{user_id}> has **deleted** their feedback containing `<MFR` without enough points. "
                    f"They used **{points_to_remove}** points and now have **{total_points}** MF points.\n\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
                ),
                inline=False
            )
            embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            await channel.send(embed=embed)

    async def MFS_delete(self, message: discord.Message, thread: discord.Thread, ticket_counter: int):
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        if not channel:
            return

        deleted_content = self.helpers.shorten_message(message.content, 1000)

        user_id = str(message.author.id)
        # don't need to remove any points since <MFS handled that; no points given in return
        total_points = await self.bot.db.fetch_points(user_id)

        delete_notice = await message.channel.send(
            f"{message.author.mention} deleted their submission.\n\n"
            f"You will need to give feedback again or contact Moderators to restore your point."
            )
        
        await delete_notice.delete(delay=60)
        
        embed = await self.embeds.MFS_to_delete_embed(
        deleted_content=deleted_content,
        ticket_counter=ticket_counter,
        total_points=total_points
        )
        try:
            await thread.send(embed=embed)
        except Exception:
            logger.error("Error sending MFS_delete embed to thread %s", thread.id, exc_info=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(
            name=f"Feedback Deletion - {self.helpers.get_formatted_time()}",
            value=(
                f"<@{user_id}> has **deleted** their feedback containing `<MFS`."
                f"They can either resubmit feedback or contact Mods.\n\n"
                f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
            ),
            inline=False
        )
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        try:
            await channel.send(embed=embed)
        except Exception:
            logger.error("Error sending MFS_delete log to channel", exc_info=True)













