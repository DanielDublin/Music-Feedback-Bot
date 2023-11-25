import discord
import asyncio
from discord.ext import commands
from data.constants import INTRO_MUSIC
import datetime


async def clean_old_messages(bot):
   
    print('starting up intro-music deleter')

    channel = bot.get_channel(INTRO_MUSIC)
    if channel is None:
        return
    

    while True:    
        now = discord.utils.utcnow()
        async for message in channel.history(limit=None, oldest_first=True):
            if message.author.guild_permissions.administrator:
                continue         
        
            time_passed = now - message.created_at
            if time_passed >= datetime.timedelta(days=1):
                try:
                    await message.delete()
                except Exception as e:
                    print(str(e))
            else:
                break
        
        await asyncio.sleep(60*60) # 1 hour
             

