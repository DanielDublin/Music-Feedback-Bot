import discord
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from database.db import *
import exception_handler
from dotenv import load_dotenv



load_dotenv()

token = os.environ.get('DISCORD_TOKEN')

# Initialize the bot

intents = discord.Intents.default()
intents.members = True
intents.typing = True
intents.presences = True
bot = commands.Bot(command_prefix='<MFR', intents= intents)

# Define the on_ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await init_database()  # Initialize the database when the bot starts
    await bot.tree.sync(guild=discord.Object(id=763835373414776903))

# Load extensions (cogs)
initial_extensions = [
    'cogs.music'
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
    exception_handler.handle_exception(ctx, error)  # Call the exception handling function


async def load_extensions():
    for extension in initial_extensions:
        await bot.load_extension(extension)

    for extension in slash_extensions:
        await bot.load_extension(extension)



# Run the bot using asyncio.run() to set up the event loop
if __name__ == '__main__':
      # Create an event loop
    loop = asyncio.get_event_loop()

    # Use the event loop's run_until_complete to execute the coroutine
    try:
        loop.run_until_complete(load_extensions())
    except KeyboardInterrupt:
        pass  # Handle Ctrl+C gracefully

    bot.run(token)



