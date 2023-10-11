import discord
from discord.ext import commands
import database.db as db


FEEDBACK_CHANNEL_ID = 749443325530079314
SERVER_OWNER_ID = 412733389196623879

class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    #note: need to add functions in db of fetch_points, fetch_rank, reduce_points, add_points, fetch_top_users, add_user, remove_user

    @commands.Cog.listener()
    async def on_ready(self, member : discord.Member):
        global FEEDBACK_CHANNEL_ID
        general_chat = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        await general_chat.send("Music Feedback is online.") 
        

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        await db.add_user(member.id)  
    

    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(member): 
        await db.reset_points(member.id)
        
    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(guild, member):
        await db.remove_user(member.id)
    
    
   
async def setup(bot):
    await bot.add_cog(User_listener(bot))