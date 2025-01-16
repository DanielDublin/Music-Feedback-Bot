import discord
import database.db as db
from discord.ext import commands
from data.constants import BOT_DEV_ID, SERVER_ID, CO_DEV_ID
import json
from functools import wraps

class Owner_Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def is_owners():
        def decorator(func):
            @wraps(func)
            async def wrapper(self, ctx, *args, **kwargs):
                if ctx.author.id in {BOT_DEV_ID, CO_DEV_ID}:
                    return await func(self, ctx, *args, **kwargs)
                await ctx.send("You do not have permission to use this command.")
            return wrapper
        return decorator

    @commands.command()
    @commands.is_owner()
    async def migrate(self, ctx: discord.Message):

        await ctx.channel.send("starting migration process")

        # Load the JSON file with nested dictionaries
        with open('MF_Points.json', 'r') as json_file:
            data = json.load(json_file)

        await db.json_migration(data)
        await ctx.channel.send("finished migration process")

    # Mod migrate json
    @commands.command()
    @commands.is_owner()
    async def migrate_warnings(self, ctx: discord.Message):

        await ctx.channel.send("starting warning migration process")
        await db.migrate_warnings()
        await ctx.channel.send("finished warning migration process")
        



    # Mod migrate json
    @commands.command()
    @commands.is_owner()
    async def migrate_warnings_extreme(self, ctx: discord.Message):
        await ctx.channel.send("starting warning migration process")
        with open('output.json', 'r') as json_file:
            json_data = json.load(json_file)

        guild_id = ctx.guild.id

        # Fetch banned user IDs
        guild = ctx.guild
        banned_user_ids = await self.get_banned_user_ids(guild)

        # Prepare Discord user data
        discord_user_data = await self.prepare_discord_user_data(guild, json_data)

        # Update SQL user data
        await db.migrate_warnings_extreme(discord_user_data)
        await ctx.channel.send("finished warning migration process")
        

    @commands.command()
    @is_owners()
    async def say(self, ctx: discord.Message, channel_id: int, *, message: str):
        try:
            target_channel = self.bot.get_channel(channel_id)
            if target_channel:
                await target_channel.send(message)
                await ctx.send(f'Message was sent.')
            else:
                await ctx.send(f"Channel with ID {channel_id} not found.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


    
    @commands.command()
    @is_owners()
    async def crash(self, ctx: discord.Message):
        await ctx.channel.send("Crashing!")
        exit(1)
        

    
    async def get_banned_user_ids(self, guild):
        banned_users = [entry async for entry in guild.bans(limit=None)]
        return banned_users

    async def prepare_discord_user_data(self, guild, json_data):
        banned_user_ids = await self.get_banned_user_ids(guild)

        user_warnings = {}
        for user_id, warnings in json_data.items():
            if user_id in banned_user_ids:
                print(f"User {user_id} is on the ban list. Ignoring.")
            else:
                user_warnings[user_id] = warnings

        return user_warnings
    

async def setup(bot):
    await bot.add_cog(Owner_Utilities(bot))