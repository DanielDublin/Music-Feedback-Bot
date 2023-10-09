import discord
import os
import asyncio
import database.db as db
from discord.ext import commands
from discord import app_commands
import exception_handler
from dotenv import load_dotenv



load_dotenv()

token = os.environ.get('DISCORD_TOKEN')

# Initialize the bot

intents = discord.Intents.default()
intents.members = True
intents.typing = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents= intents)

# Define the on_ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await db.init_database()  # Initialize the database when the bot starts
    await bot.tree.sync(guild=discord.Object(id=763835373414776903))

# Load extensions (cogs)
initial_extensions = [
    
    'cogs.general',
    'cogs.user_listener',
    'cogs.guild_events',
    'cogs.music',
    'cogs.admin'
    # Add more cogs as needed
]

# Load slash command cogs
slash_extensions = [
    'cogs.slash_commands.hello'  # Replace with your slash command cogs
    # Add more slash command cogs as needed
]



# Define an exception handler
@bot.event
async def on_command_error(ctx, error):
    await exception_handler.handle_exception(ctx, error)  # Call the exception handling function


async def load_extensions():
    for extension in initial_extensions:
        await bot.load_extension(extension)

    for extension in slash_extensions:
        await bot.load_extension(extension)



# Run the bot using asyncio.run() to set up the event loop
if __name__ == '__main__':
      # Create an event loop
    loop = asyncio.get_event_loop()


    try:
        loop.run_until_complete(load_extensions()) # initializing the cogs
        bot.loop.create_task(db.schedule_weekly_task()) # database weekly maintenance
    except KeyboardInterrupt:
        pass  # Handle Ctrl+C gracefully

    bot.run(token)



