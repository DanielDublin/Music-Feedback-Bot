import discord
import database.db as db
from discord.ext import commands
import json

class Owner_Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def migrate(self, ctx: discord.Message):

        await ctx.channel.send("starting migration process")

        # Load the JSON file with nested dictionaries
        with open('MF Points.json', 'r') as json_file:
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
        
        
async def setup(bot):
    await bot.add_cog(Owner_Utilities(bot))