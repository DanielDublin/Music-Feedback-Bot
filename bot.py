import discord
import os
import asyncio
import database.db as db
from discord.ext import commands
from discord import Interaction, app_commands
import exception_handler
from dotenv import load_dotenv
from data.constants import BOT_DEV_ID, FEEDBACK_CHANNEL_ID, SERVER_ID, INTRO_MUSIC
from cogs.feedback_threads.modules.ctx_class import ContextLike


IS_READY = 0

load_dotenv()
token = os.environ.get('DISCORD_TEST_TOKEN')

# Initialize the bot
intents = discord.Intents.default()
intents.members = True
intents.typing = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix=["<MF", "<Mf", "<mF", "<mf"], intents=intents, case_insensitive=True, strip_after_prefix=True,
                   owner_id=BOT_DEV_ID)
bot.remove_command('help')

@bot.tree.command(name="sync", description="Force sync commands", guild=discord.Object(id=732355624259813531))
async def sync(interaction: discord.Interaction):
    await bot.tree.sync(guild=discord.Object(id=732355624259813531))
    await interaction.response.send_message("Commands synced", ephemeral=True)


# Define the on_ready event
@bot.event
async def on_ready():
    global IS_READY
    global bot

    if not IS_READY:

        print(f'Logged in as {bot.user.name} ({bot.user.id})')
        
        await db.init_database()  # Initialize the database when the bot starts

        feedback_cog = bot.get_cog("FeedbackThreads")
        if feedback_cog:
            try:
                await feedback_cog.initialize_sqldb()
                print("FeedbackThreads database initialized")
            except Exception as e:
                print(f"FeedbackThreads database initialization failed: {e}")

            try:
                await feedback_cog.threads_manager.on_ready()
                print("FeedbackThreads threads manager initialized")
            except Exception as e:
                print(f"FeedbackThreads threads manager initialization failed: {e}")
        else:
            print("FeedbackThreads Cog not found")


        # await bot.tree.sync(guild=discord.Object(id=732355624259813531)) # for debug

        # tree = bot.tree
        # print("Registered commands:")
        # for command in tree.get_commands():
        #     print(f"- {command.name}: {command.description}")

        await bot.tree.sync() 

        print('Sync-ed slash commands')

 
        general_chat = bot.get_channel(FEEDBACK_CHANNEL_ID)
        creator_user = await bot.fetch_user(BOT_DEV_ID)
        await creator_user.send("Music Feedback is now live")
        IS_READY += 1


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
    'cogs.member_cards.member_class',
    'cogs.recent_feedback.embeds'
    # Add more cogs as needed
]

# Load slash command cogs
slash_extensions = [
    # 'cogs.slash_commands.timer_cogs.timer',
    'cogs.slash_commands.admin',
    'cogs.slash_commands.rank_commands',
    'cogs.slash_commands.threads',
    'cogs.slash_commands.get_member_card'
    # Add more slash command cogs as needed
]

# Define an exception handler
@bot.event
async def on_command_error(ctx, error):
    await exception_handler.handle_exception(ctx, error)  # Call the exception handling function
    
@bot.tree.error
async def on_app_command_error(interaction, error):
    await interaction.channel.send(str(error))


async def load_extensions():
    global initial_extensions, slash_extensions
    
    for extension in initial_extensions:
        await bot.load_extension(extension)

    for extension in slash_extensions:
        await bot.load_extension(extension)


# Run the bot using asyncio.run() to set up the event loop
async def main():
    global bot
    try:
        await load_extensions()  # Initializing the cogs
    except KeyboardInterrupt:
        pass  # Handle Ctrl+C gracefully

    # Create a task that will run the database weekly maintenance task
    task = asyncio.create_task(db.schedule_weekly_task())

    # Start the bot
    await bot.start(str(token))

    # Wait for the database weekly maintenance task to finish
    await task


if __name__ == "__main__":
    asyncio.run(main())
