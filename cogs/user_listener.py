import discord
from discord.ext import commands
import database.db as db


FEEDBACK_CHANNEL_ID = 749443325530079314
SERVER_OWNER_ID = 412733389196623879

class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    #note: need to add functions in db of fetch_points, fetch_rank, reduce_points, add_points, fetch_top_users

    #MF points - Shows how many points the current user has 
    @commands.command()             
    async def points(self, ctx :discord.Message): 
        
 
                
   
async def setup(bot):
    await bot.add_cog(User_listener(bot))