import discord
import asyncio
import traceback
from discord.ext import commands, tasks
from data.constants import INTRO_MUSIC, BOT_LOG
import datetime

class MessageCleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clean_old_messages.start()

    def cog_unload(self):
        if self.clean_old_messages.is_running():
            self.clean_old_messages.cancel()
        
    def cog_load(self):
        if not self.clean_old_messages.is_running():
            self.clean_old_messages.start()

    async def log_to_bot_log(self, message: str, error: Exception = None):
        """Send detailed logs to BOT_LOG channel"""
        try:
            log_channel = self.bot.get_channel(BOT_LOG)
            if log_channel is None:
                print(f"[MessageCleaner] BOT_LOG channel not found: {message}")
                return
            
            timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            if error:
                # Format error with full traceback
                error_details = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                full_message = f"```\n[{timestamp}] MessageCleaner Error\n{message}\n\nTraceback:\n{error_details}\n```"
                
                # Split if too long (Discord 2000 char limit)
                if len(full_message) > 1990:
                    await log_channel.send(f"```\n[{timestamp}] MessageCleaner Error\n{message}\n```")
                    # Send traceback in chunks
                    for i in range(0, len(error_details), 1800):
                        await log_channel.send(f"```\n{error_details[i:i+1800]}\n```")
                else:
                    await log_channel.send(full_message)
            else:
                # Regular info message
                await log_channel.send(f"```\n[{timestamp}] MessageCleaner: {message}\n```")
                
        except Exception as e:
            # Fallback to console if BOT_LOG fails
            print(f"[MessageCleaner] Failed to log to BOT_LOG: {e}")
            print(f"[MessageCleaner] Original message: {message}")
            if error:
                traceback.print_exception(type(error), error, error.__traceback__)

    @staticmethod
    def is_a_normie(message):
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
                await self.log_to_bot_log("⚠️ Channel is None, attempting to re-fetch...")
                self.channel = self.bot.get_channel(INTRO_MUSIC)
                if self.channel is None:
                    await self.log_to_bot_log(f"❌ Failed to get channel {INTRO_MUSIC}")
                    return
            
            # Log task execution
            deleted = await self.channel.purge(bulk=True, check=self.is_a_normie)
            
            if deleted:
                await self.log_to_bot_log(f"✅ Cleaned {len(deleted)} old message(s) from intro-music")
            else:
                # Only log periodically to avoid spam (every 6 hours)
                if self.clean_old_messages.current_loop % 6 == 0:
                    await self.log_to_bot_log("ℹ️ No old messages to clean (periodic check)")
                    
        except discord.errors.Forbidden:
            await self.log_to_bot_log("❌ Missing permissions to delete messages in intro-music")
        except discord.errors.HTTPException as e:
            await self.log_to_bot_log(f"❌ Discord API error during message cleanup", e)
        except Exception as e:
            await self.log_to_bot_log(f"❌ Unexpected error in clean_old_messages task", e)

    @clean_old_messages.error
    async def clean_old_messages_error(self, error):
        """Error handler for the task loop"""
        await self.log_to_bot_log("💥 CRITICAL: clean_old_messages task crashed!", error)
        
        # Attempt to restart the task after a delay
        await asyncio.sleep(60)
        if not self.clean_old_messages.is_running():
            await self.log_to_bot_log("🔄 Attempting to restart clean_old_messages task...")
            try:
                self.clean_old_messages.restart()
                await self.log_to_bot_log("✅ Successfully restarted clean_old_messages task")
            except Exception as e:
                await self.log_to_bot_log("❌ Failed to restart task", e)

    @clean_old_messages.before_loop
    async def before_printer(self):
        try:
            print('[MessageCleaner] Starting up intro-music deleter')
            print('[MessageCleaner] Waiting for bot to be ready...')
            await self.bot.wait_until_ready()
            print('[MessageCleaner] Bot ready, fetching channel...')
            
            self.channel = self.bot.get_channel(INTRO_MUSIC)
            
            if self.channel:
                print(f'[MessageCleaner] Channel found: {self.channel.name}')
                await self.log_to_bot_log(f"🚀 MessageCleaner started - monitoring #{self.channel.name}")
            else:
                print(f'[MessageCleaner] WARNING: Channel {INTRO_MUSIC} not found!')
                await self.log_to_bot_log(f"⚠️ Channel {INTRO_MUSIC} not found during startup")
                
        except Exception as e:
            print(f'[MessageCleaner] Error in before_loop: {e}')
            traceback.print_exc()
            await self.log_to_bot_log("❌ Error during MessageCleaner startup", e)

async def setup(bot):
    await bot.add_cog(MessageCleaner(bot))