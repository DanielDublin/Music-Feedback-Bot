import discord
import asyncio
from discord.ext import commands
from data.constants import INTRO_MUSIC
import datetime

def is_a_normie(message):
    
    if  message.author.guild_permissions.administrator:
        now = discord.utils.utcnow()
        time_passed = now - message.created_at
        if time_passed >= datetime.timedelta(days=1):
            return True
       
    return False

async def clean_old_messages(bot):
   
    print('starting up intro-music deleter')

    channel = bot.get_channel(INTRO_MUSIC)
    if channel is None:
        return
    
    while(True):
        await channel.purge(bulk = True, check=is_a_normie)
        await asyncio.sleep(60*60) # 1 hour
             

