import discord
import asyncio
import json
import logging
import os
from discord.ext import commands, tasks
from data.constants import FINISHED_MUSIC

logger = logging.getLogger(__name__)

STORED_MESSAGE_ID_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stored_message_id.json")

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
            self.stored_message_id = new_message.id  # Save the new ID for tomorrow
            self._persist_message_id(self.stored_message_id)
        except discord.HTTPException as e:
            logger.error(f"Error sending new message: {e}", exc_info=True)

    @delete_and_repost_cycle.error
    async def delete_and_repost_cycle_error(self, error):
        logger.error(f"[FinishedMusicMessage] Task crashed: {error!r}")
        if not self.delete_and_repost_cycle.is_running():
            self.delete_and_repost_cycle.restart()

    def _persist_message_id(self, message_id):
        """Write the current stored_message_id to disk so it survives restarts."""
        try:
            with open(STORED_MESSAGE_ID_PATH, "w") as f:
                json.dump({"stored_message_id": message_id}, f)
        except OSError as e:
            logger.error(f"[FinishedMusicMessage] Could not write stored_message_id.json: {e}", exc_info=True)

    @delete_and_repost_cycle.before_loop
    async def before_cycle(self):
        """Wait for bot to be ready, then restore the stored message ID from disk."""
        await self.client.wait_until_ready()

        # Attempt to load a previously persisted message ID
        try:
            with open(STORED_MESSAGE_ID_PATH, "r") as f:
                data = json.load(f)
                persisted_id = data.get("stored_message_id")
        except (OSError, json.JSONDecodeError):
            persisted_id = None

        if persisted_id:
            channel = self.client.get_channel(int(self.stored_channel_id))
            if channel:
                try:
                    await channel.fetch_message(persisted_id)
                    self.stored_message_id = persisted_id
                    logger.info(f"[FinishedMusicMessage] Restored stored_message_id {persisted_id} from disk.")
                except (discord.NotFound, discord.HTTPException):
                    logger.warning("[FinishedMusicMessage] Persisted message no longer exists; will create a new one on next cycle.")
                    self.stored_message_id = None
            else:
                logger.error("[FinishedMusicMessage] Could not find the Finished Music channel during setup.")

async def setup(bot):
    await bot.add_cog(FinishedMusicMessage(bot))