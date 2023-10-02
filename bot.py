import discord
import os
from discord.ext import commands
from discord_slash import SlashCommand
from database import init_database  # Import the database initialization function
import exception_handler

token = os.getenv("DISCORD_TOKEN")

# Initialize the bot
bot = commands.Bot(command_prefix='!')
slash = SlashCommand(bot, sync_commands=True)  # Create a SlashCommand instance

# Define the on_ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await init_database()  # Initialize the database when the bot starts

# Load extensions (cogs)
initial_extensions = [
    'cogs.admin',
    'cogs.general',
    # Add more cogs as needed
]

# Load slash command cogs
slash_extensions = [
    'cogs.slash_commands.hello',  # Replace with your slash command cogs
    # Add more slash command cogs as needed
]

if __name__ == '__main__':
    for extension in initial_extensions:
        bot.load_extension(extension)

    for extension in slash_extensions:
        slash.load_extension(extension)

# Define an exception handler
@bot.event
async def on_command_error(ctx, error):
    exception_handler.handle_exception(ctx, error)  # Call the exception handling function


# Run the bot with your token
bot.run(TOKEN)