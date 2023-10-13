import discord
import os
import asyncio
import database.db as db
from discord.ext import commands
from discord import app_commands
import exception_handler
from dotenv import load_dotenv


BOT_DEV_ID = 167329255502512128
FEEDBACK_CHANNEL_ID = 1103427357781528597

load_dotenv()
token = os.environ.get('DISCORD_TOKEN')



# Initialize the bot
intents = discord.Intents.default()
intents.members = True
intents.typing = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents= intents, case_insensitive=True, strip_after_prefix = True, owner_id = BOT_DEV_ID)

# Define the on_ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await db.init_database()  # Initialize the database when the bot starts
    await bot.tree.sync(guild=discord.Object(id=763835373414776903))
    general_chat = bot.get_channel(FEEDBACK_CHANNEL_ID)
    await general_chat.send("Music Feedback is online.") 
    
    

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
async def main():
  global bot
  try:
    await load_extensions() # Initializing the cogs
  except KeyboardInterrupt:
    pass # Handle Ctrl+C gracefully

  # Create a task that will run the database weekly maintenance task
  task = asyncio.create_task(db.schedule_weekly_task())

  # Start the bot
  await bot.start(token)

  # Wait for the database weekly maintenance task to finish
  await task



if __name__ == "__main__":
  asyncio.run(main())