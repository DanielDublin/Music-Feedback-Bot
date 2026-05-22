import discord
import asyncio
import logging
from discord.ext import commands, tasks
from data.constants import FINISHED_MUSIC

logger = logging.getLogger(__name__)


class FinishedMusicMessage(commands.Cog):

    MESSAGE_TEXT = "**Deleted song?** If your name is green, you have the Groupies role and have 5-minute access to this channel! Stay active in the server for a few days and quickly rank up for full access."

    def __init__(self, client):
        self.client = client
        self.stored_message_id = None
        self.stored_channel_id = FINISHED_MUSIC

    async def cog_load(self):
        """Called when the cog is loaded - starts the background task."""
        self.delete_and_repost_cycle.start()

    async def cog_unload(self):
        """Called when the cog is unloaded - stops the background task."""
        self.delete_and_repost_cycle.cancel()

    @tasks.loop(hours=24, reconnect=True)
    async def delete_and_repost_cycle(self):
        """Delete and repost the message every 24 hours."""
        
        # 1. Force the ID to be an integer
        channel = self.client.get_channel(int(self.stored_channel_id))
        
        # 2. Check if the channel actually exists first
        if not channel:
            logger.error(f"Channel with ID {self.stored_channel_id} not found. Check permissions and ID!")
            return

        # 3. Try to delete the old message ONLY if we have an ID stored
        if self.stored_message_id:
            try:
                old_message = await channel.fetch_message(self.stored_message_id)
                await old_message.delete()
            except discord.NotFound:
                logger.warning("Message not found, may have been manually deleted.")
            except discord.HTTPException as e:
                logger.error(f"Error deleting message: {e}", exc_info=True)
        
        # 4. ALWAYS send the new message, regardless of whether an old one was deleted
        try:
            new_message = await channel.send(self.MESSAGE_TEXT)
            self.stored_message_id = new_message.id  # Save the new ID for the next cycle
        except discord.HTTPException as e:
            logger.error(f"Error sending new message: {e}", exc_info=True)

    @delete_and_repost_cycle.error
    async def delete_and_repost_cycle_error(self, error):
        logger.error(f"[FinishedMusicMessage] Task crashed: {error!r}", exc_info=True)
        # Back off before restarting so a persistent failure can't tight-loop.
        await asyncio.sleep(300)
        if not self.delete_and_repost_cycle.is_running():
            self.delete_and_repost_cycle.restart()

    @delete_and_repost_cycle.before_loop
    async def before_cycle(self):
        """Wait for the bot to be ready, then sweep the channel clean.

        Deleting every existing copy of MESSAGE_TEXT on startup makes the
        channel self-healing: a message orphaned by an ill-timed crash
        (posted but never tracked) is reclaimed here. The loop's immediate
        first iteration then reposts, so exactly one copy ends up present.

        The whole body is catch-all guarded: a before_loop exception is NOT
        routed to the .error handler, so an unhandled error here would kill
        the loop for good. Swallowing it lets the loop start regardless.
        """
        try:
            await self.client.wait_until_ready()
            self.stored_message_id = None

            channel = self.client.get_channel(int(self.stored_channel_id))
            if not channel:
                logger.error("[FinishedMusicMessage] Finished Music channel not found during startup sweep.")
                return

            # The channel holds well under 50 messages, so one unpaginated
            # history scan finds every stale copy the bot left behind.
            swept = 0
            async for message in channel.history(limit=50):
                if message.author.id == self.client.user.id and message.content == self.MESSAGE_TEXT:
                    try:
                        await message.delete()
                        swept += 1
                    except discord.HTTPException as e:
                        logger.warning(f"[FinishedMusicMessage] Could not delete stale message {message.id}: {e}")
            if swept:
                logger.info(f"[FinishedMusicMessage] Startup sweep removed {swept} stale message(s).")
        except Exception:
            logger.error("[FinishedMusicMessage] Startup sweep failed; loop will start anyway", exc_info=True)

async def setup(bot):
    await bot.add_cog(FinishedMusicMessage(bot))