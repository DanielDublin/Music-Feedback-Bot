from re import A
import discord
import asyncio
from discord.ext import commands
from data.constants import INTRO_MUSIC
import datetime


async def clean_old_messages(channel):
   
    print('starting to go over intro-music')
    
    now = discord.utils.utcnow()
    async for message in channel.history(limit=None, oldest_first=True):
        if message.author.guild_permissions.administrator:
            continue         
        
        time_passed = now - message.created_at
        if time_passed > datetime.timedelta(days=1):
            try:
                await message.delete()
            except Exception as e:
                print(str(e))
        else:
            remaining_time = datetime.timedelta(days=1) - time_passed
            asyncio.create_task(delayed_delete(message, remaining_time.total_seconds()))
             


async def delayed_delete(message, remaining_time):
    try:
        await asyncio.sleep(remaining_time)
        await message.delete()
    except Exception as e:
        print(str(e))
