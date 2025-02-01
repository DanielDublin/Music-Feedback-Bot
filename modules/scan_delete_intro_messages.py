import discord
import asyncio
from discord.ext import commands, tasks
from data.constants import INTRO_MUSIC
import datetime
import traceback


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

    @tasks.loop(minutes=2)
    async def clean_old_messages(self):
        try:
            if self.channel is None:
                return

            # Check if the channel is INTRO_MUSIC
            if self.channel.id == INTRO_MUSIC:
                print("In intro channel")
                async for message in self.channel.history(limit=10, oldest_first=True):  # Fetch 10 oldest messages
                    print(f"Checking message: {message.content} from {message.author}")
                    now = discord.utils.utcnow()
                    time_passed = now - message.created_at
                    print(f"Time passed since message: {time_passed} (now: {now}, message time: {message.created_at})")

                    # Only proceed if the message is within the last hour
                    if time_passed > datetime.timedelta(hours=1):
                        print("Message is older than 1 hour, skipping")
                        continue  # Continue to the next message

                    # Only proceed if the message is older than 2 minutes
                    if time_passed < datetime.timedelta(minutes=2):
                        print("Message is younger than 2 minutes, skipping")
                        continue  # Continue to the next message

                    # If message is from an admin, skip it and continue to the next message
                    if message.author.guild_permissions.administrator:
                        print(f"Message from admin {message.author}, continuing to next message")
                        continue  # Continue to the next message

                    # Otherwise, purge messages that are older than 2 minutes and not from an admin
                    print("Purging messages")
                    await self.channel.purge(bulk=True, check=self.should_purge_message)
                    await self.channel.send("✅ **Old messages cleared!**")
                    return  # Exit after purging

        except Exception as e:
            # Log the error in the specified channel
            error_channel = self.bot.get_channel(INTRO_MUSIC)
            if error_channel:
                await error_channel.send(f"🚨 **Error in MessageCleaner:**\n```{traceback.format_exc()}```")

    def should_purge_message(self, message):
        """Check if the message should be purged (older than 2 minutes and from non-admin)."""
        now = discord.utils.utcnow()
        time_passed = now - message.created_at
        print(f"Checking purge for message: {message.content} (Time passed: {time_passed})")
        return time_passed > datetime.timedelta(minutes=2) and not message.author.guild_permissions.administrator

    @clean_old_messages.before_loop
    async def before_clean_old_messages(self):
        print('Starting up intro-music deleter...')
        await self.bot.wait_until_ready()
        self.channel = self.bot.get_channel(INTRO_MUSIC)
        print(f'Channel set to {self.channel.name}')


async def setup(bot):
    await bot.add_cog(MessageCleaner(bot))
