import discord
import os
import asyncio
import logging
from database.db import Database
from discord.ext import commands
from discord import Interaction, app_commands
import exception_handler
from dotenv import load_dotenv
from data.constants import BOT_DEV_ID, FEEDBACK_CHANNEL_ID, SERVER_ID, INTRO_MUSIC
from cogs.feedback_threads.modules.ctx_class import ContextLike
from utils.bot_logger import DiscordChannelHandler

logger = logging.getLogger(__name__)


IS_READY = False

load_dotenv()
token = os.environ.get('DISCORD_TOKEN')
server_id = os.environ.get('SERVER_ID')

# Initialize the bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True  # required for on_audit_log_entry_create

class MFBot(commands.Bot):
    _owner_pfp_url: str = ""

    async def get_owner_pfp_url(self) -> str:
        if not self._owner_pfp_url:
            user = await self.fetch_user(self.owner_id)
            self._owner_pfp_url = user.avatar.url
        return self._owner_pfp_url


bot = MFBot(
    command_prefix=["<MF", "<Mf", "<mF", "<mf"],
    intents=intents,
    case_insensitive=True,
    strip_after_prefix=True,
    owner_id=BOT_DEV_ID,
)
bot.remove_command('help')

@bot.tree.command(name="sync", description="Force sync commands", guild=discord.Object(id=SERVER_ID))
async def sync(interaction: discord.Interaction):
    await bot.tree.sync()
    await bot.tree.sync(guild=discord.Object(id=SERVER_ID))
    await interaction.response.send_message("Commands synced", ephemeral=True)


# Define the on_ready event
@bot.event
async def on_ready():
    global IS_READY

    if not IS_READY:

        logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')

        feedback_cog = bot.get_cog("FeedbackThreads")
        if feedback_cog:
            try:
                await feedback_cog.threads_manager.on_ready()
                logger.info("FeedbackThreads threads manager initialized")
            except Exception as e:
                logger.error(f"FeedbackThreads threads manager initialization failed: {e}", exc_info=True)
        else:
            logger.warning("FeedbackThreads Cog not found")


        # await bot.tree.sync(guild=discord.Object(id=732355624259813531)) # for debug

        # tree = bot.tree
        # print("Registered commands:")
        # for command in tree.get_commands():
        #     print(f"- {command.name}: {command.description}")

        await bot.tree.sync()
        await bot.tree.sync(guild=discord.Object(id=SERVER_ID))

        logger.info('Sync-ed slash commands')

 
        creator_user = await bot.fetch_user(BOT_DEV_ID)
        await creator_user.send("Music Feedback is now live")
        IS_READY = True


# Load extensions (cogs)
initial_extensions = [

    'cogs.general',
    'cogs.user_listener',
    'cogs.guild_events',
    'cogs.music',
    'cogs.owner_utilities',
    'cogs.help_command',
    'modules.scan_delete_intro_messages',
    'cogs.feedback_threads.feedback_threads',
    'ml_model.feedback_monitor',
    'cogs.finished_music_message',
    'cogs.captcha_counter'
    # Add more cogs as needed
]

# Load slash command cogs
slash_extensions = [
    'cogs.slash_commands.timer',
    'cogs.slash_commands.admin',
    'cogs.slash_commands.rank_commands',
    'cogs.slash_commands.threads',
    'cogs.slash_commands.get_member_card',
    'cogs.slash_commands.aotw_event',
    'cogs.slash_commands.prime_time'
    # Add more slash command cogs as needed
]

# Define an exception handler
@bot.event
async def on_command_error(ctx, error):
    await exception_handler.handle_exception(ctx, error)  # Call the exception handling function
    
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        msg = f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
    elif isinstance(error, app_commands.MissingPermissions):
        msg = "You don't have permission to use this command."
    elif isinstance(error, app_commands.CheckFailure):
        msg = "You don't meet the requirements for this command."
    else:
        logger.error(f"Unhandled app command error: {error}")
        msg = "An unexpected error occurred."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass  # best-effort; don't crash the error handler itself


async def load_extensions():
    global initial_extensions, slash_extensions
    
    for extension in initial_extensions:
        await bot.load_extension(extension)

    for extension in slash_extensions:
        await bot.load_extension(extension)


# Run the bot using asyncio.run() to set up the event loop
async def main():
    _handler = logging.StreamHandler()
    _handler.setFormatter(_ColoredFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logging.basicConfig(level=logging.INFO, handlers=[_handler])
    discord_handler = DiscordChannelHandler(bot, level=logging.WARNING)
    discord_handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(name)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logging.getLogger().addHandler(discord_handler)
    bot.db = Database()
    try:
        await bot.db.init_database()
    except Exception as e:
        logger.critical(f"FATAL: db.init_database() failed: {e}", exc_info=True)

    try:
        await load_extensions()  # Initializing the cogs
    except KeyboardInterrupt:
        pass  # Handle Ctrl+C gracefully

    # Create a task that will run the database weekly maintenance task
    task = asyncio.create_task(bot.db.schedule_weekly_task())

    # Start the bot
    await bot.start(str(token))

    # Wait for the database weekly maintenance task to finish
    await task


class _ColoredFormatter(logging.Formatter):
    _COLORS = {
        logging.INFO:     '\033[94m',   # bright blue — levelname only
        logging.WARNING:  '\033[91m',   # bright red  — levelname only
        logging.ERROR:    '\033[91m',   # bright red  — levelname only
        logging.CRITICAL: '\033[91m',   # bright red  — levelname only
    }
    _RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelno)
        if color:
            original = record.levelname
            record.levelname = f"{color}{original}{self._RESET}"
            result = super().format(record)
            record.levelname = original
            return result
        return super().format(record)


if __name__ == "__main__":
    asyncio.run(main())
