import discord
from discord.ext import commands
import database.db as db



FEEDBACK_CHANNEL_ID = 749443325530079314
SERVER_OWNER_ID = 412733389196623879
WARNING_CHANNEL = 920730664029020180  #msb_log_channel channel

class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(ctx : discord.Message, target_user :discord.Member):
        global users_dict
        
        if ctx.content.startswith(".warn") and ctx.author.guild_permissions.kick_members:
             warnings = await add_warning_to_user(str(target_user.id))
             
             if warnings >= 3:
                 
                 
                
             

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