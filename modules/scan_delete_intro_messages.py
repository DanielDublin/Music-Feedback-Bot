import discord
import asyncio
from discord.ext import commands, tasks
from data.constants import INTRO_MUSIC
import datetime

class MessageCleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clean_old_messages.start()

    def cog_unload(self):
        self.clean_old_messages.cancel()
        
    def cog_load(self):
        self.clean_old_messages.start()

    @staticmethod
    def is_a_normie(message):
        if not message.author.guild_permissions.administrator:
            now = discord.utils.utcnow()
            time_passed = now - message.created_at
            if time_passed >= datetime.timedelta(days=1):
                return True
        return False
    

    @tasks.loop(hours=1)  # Runs every hour
    async def clean_old_messages(self):
        if self.channel is not None:
            await self.channel.purge(bulk=True, check=self.is_a_normie)

    @clean_old_messages.before_loop
    async def before_printer(self):
        print('starting up intro-music deleter')
        print('waiting for the bot to be ready')
        await self.bot.wait_until_ready()
        print('ready')
        self.channel = self.bot.get_channel(INTRO_MUSIC)
        

async def setup(bot):
    await bot.add_cog(MessageCleaner(bot))