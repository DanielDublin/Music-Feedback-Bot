import discord
from discord.ext import commands
import database.db as db


FEEDBACK_CHANNEL_ID = 749443325530079314
SERVER_OWNER_ID = 412733389196623879

class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        await db.add_user(str(member.id))
    

    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(member): 
        await db.reset_points(str(member.id))
        
    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(guild, member):
        await db.remove_user(str(member.id))
    
    
   
async def setup(bot):
    await bot.add_cog(User_listener(bot))