import discord
from discord.ext import commands
import database.db as db
import modules.soundcloud_promotion_checker as SCP_checker
import modules.youtube_promotion_checker as YT_checker
from datetime import datetime



FEEDBACK_CHANNEL_ID = 1103427357781528597 #749443325530079314
SERVER_OWNER_ID = 167329255502512128 #412733389196623879
WARNING_CHANNEL =  1103427357781528597 #920730664029020180  #msb_log_channel channel
MODERATORS_ROLE_ID = 915720537660084244 #732377221905252374


class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author.bot:
            return
        
        content = ctx.message.content
        if ctx.content.lower().startswith(".warn") and ctx.author.guild_permissions.kick_members:
            
            mentions = ctx.mentions
            if mentions is None:
                return        
            
            target_user = mentions[0]
            warnings = await db.add_warning_to_user(str(target_user.id))
             
            if warnings >= 3:
                warning_log_channel = self.bot.get_channel(WARNING_CHANNEL)
                 
               
                pfp = target_user.avatar.url            
                embed = discord.Embed(color = 0x7e016f)
                embed.set_author(name = f"Music Feedback: {target_user.name}", icon_url = ctx.guild.icon.url) 
                embed.set_thumbnail(url = pfp)
                embed.add_field(name = "__MF Warnings__", value = f"User has **{warnings}** warnings.", inline = False)
                embed.add_field(name="Use ``.warnings (user id)`` to see infractions:", value=f"{target_user.mention} | {target_user.id}", inline=False)
                embed.timestamp = datetime.now()
                await warning_log_channel.send(embed = embed) 
                await warning_log_channel.send(f"<@&{MODERATORS_ROLE_ID}>")
                
        elif 'soundcloud.com' in content and not ctx.author.guild_permissions.kick_members:
            is_promoting = await SCP_checker.check_soundcloud(ctx.message)

        elif ('youtube.com' in content or 'youtu.be') and not ctx.author.guild_permissions.kick_members:
            is_promoting = await YT_checker.check_youtube(ctx.message)
            await ctx.message.channel.send(f"{ctx.message.author.name} is promoting their song on YouTube.")



                 
                
             

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        await db.add_user(str(member.id))
    

    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(self, member): 
        await db.reset_points(str(member.id))
        
    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        await db.remove_user(str(member.id))
    
    
   
async def setup(bot):
    await bot.add_cog(User_listener(bot))