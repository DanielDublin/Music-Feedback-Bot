import discord
import asyncio
import logging
from discord.ext import commands, tasks
from data.constants import INTRO_MUSIC
import datetime

logger = logging.getLogger(__name__)

class MessageCleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        self.clean_old_messages.start()

    def cog_unload(self):
        if self.clean_old_messages.is_running():
            self.clean_old_messages.cancel()

    async def cog_load(self):
        if not self.clean_old_messages.is_running():
            self.clean_old_messages.start()

    @staticmethod
    def is_a_normie(message):

        # delete messages immediately for users who have left
        if not isinstance(message.author, discord.Member):
            return True

        if not message.author.guild_permissions.administrator:
            now = discord.utils.utcnow()
            time_passed = now - message.created_at
            if time_passed >= datetime.timedelta(days=1):
                return True

        return False

    @tasks.loop(hours=1, reconnect=True)
    async def clean_old_messages(self):
        try:
            if self.channel is None:
                logger.warning("Channel is None, attempting to re-fetch...")
                self.channel = self.bot.get_channel(INTRO_MUSIC)
                if self.channel is None:
                    logger.error("Failed to get channel %s", INTRO_MUSIC)
                    return

            deleted = await self.channel.purge(bulk=True, check=self.is_a_normie)

            if deleted:
                logger.info("Cleaned %d old message(s) from intro-music", len(deleted))
            else:
                if self.clean_old_messages.current_loop % 6 == 0:
                    logger.info("No old messages to clean (periodic check)")

        except discord.errors.Forbidden:
            logger.error("Missing permissions to delete messages in intro-music")
        except discord.errors.HTTPException:
            logger.error("Discord API error during message cleanup", exc_info=True)
        except Exception:
            logger.error("Unexpected error in clean_old_messages task", exc_info=True)

    @clean_old_messages.error
    async def clean_old_messages_error(self, error):
        """Error handler for the task loop"""
        logger.error("clean_old_messages task crashed", exc_info=error)

        await asyncio.sleep(60)
        if not self.clean_old_messages.is_running():
            logger.info("Attempting to restart clean_old_messages task...")
            try:
                self.clean_old_messages.restart()
                logger.info("Successfully restarted clean_old_messages task")
            except Exception:
                logger.error("Failed to restart task", exc_info=True)

    @clean_old_messages.before_loop
    async def before_printer(self):
        try:
            logger.info('[MessageCleaner] Starting up intro-music deleter')
            logger.info('[MessageCleaner] Waiting for bot to be ready...')
            await self.bot.wait_until_ready()
            logger.info('[MessageCleaner] Bot ready, fetching channel...')

            self.channel = self.bot.get_channel(INTRO_MUSIC)

            if self.channel:
                logger.info('[MessageCleaner] Channel found: %s', self.channel.name)
                logger.info("MessageCleaner started — monitoring #%s", self.channel.name)
            else:
                logger.warning('[MessageCleaner] WARNING: Channel %s not found!', INTRO_MUSIC)
                logger.warning("Channel %s not found during startup", INTRO_MUSIC)

        except Exception:
            logger.error('[MessageCleaner] Error in before_loop', exc_info=True)

async def setup(bot):
    await bot.add_cog(MessageCleaner(bot))
