import discord
import asyncio
from discord.ext import commands
import database.db as db
import modules.promotion_checkers.soundcloud_promotion_checker as SCP_checker
import modules.promotion_checkers.youtube_promotion_checker as YT_checker
import modules.promotion_checkers.soundcloud_promotion_checker as Spoti_checker
from datetime import datetime
from data.constants import WARNING_CHANNEL, MODERATORS_CHANNEL_ID, MODERATORS_ROLE_ID, GENERAL_CHAT_CHANNEL_ID, \
    MUSIC_RECCOMENDATIONS_CHANNEL_ID, MUSIC_CHANNEL_ID, INTRO_MUSIC



class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url =""
        self.PRIMUS_COOLDOWN = False
        self.PRIMUS_COOLDOWN_TIME = 10
        self.MUSIC_TRIO_CHANNEL_IDS_LIST = [MUSIC_RECCOMENDATIONS_CHANNEL_ID, MUSIC_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID]

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author.bot:
            return
        
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            

        content = ctx.content
        if ctx.content.lower().startswith(".warn") and ctx.author.guild_permissions.kick_members: # warn checker
           await self.handle_warnings(ctx)

        elif 'soundcloud.com' in content.lower() and not ctx.author.guild_permissions.kick_members: # soundcloud promotion checker
            if ctx.channel.id in self.MUSIC_TRIO_CHANNEL_IDS_LIST:
                await self.handle_promotion_check(ctx)

        elif ('youtube.com' in content.lower() or 'youtu.be' in content.lower())\
                and not ctx.author.guild_permissions.kick_members:  # youtube promotion checker
            if ctx.channel.id in self.MUSIC_TRIO_CHANNEL_IDS_LIST:
                await self.handle_promotion_check(ctx)
                
        elif 'open.spotify' in content.lower() and not ctx.author.guild_permissions.kick_members:  # spotify promotion checker
            if ctx.channel.id in self.MUSIC_TRIO_CHANNEL_IDS_LIST:
                await self.handle_promotion_check(ctx)


        elif ctx.channel.id == INTRO_MUSIC and not ctx.author.guild_permissions.administrator: # Music intro delete 24h
           try:
               await asyncio.sleep(60*60*24) # 24 hours
               await ctx.delete()
           except Exception as e:
               print(str(e))                  
        elif 'primus' in content.lower() and ctx.channel.id == GENERAL_CHAT_CHANNEL_ID: # primus easter egg
            
            if not self.PRIMUS_COOLDOWN:
                self.PRIMUS_COOLDOWN = True
                await ctx.channel.send("🤘 **Primus SUX!** 🤘")
                await asyncio.sleep(self.PRIMUS_COOLDOWN_TIME)
                self.PRIMUS_COOLDOWN = False
                

                

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await db.add_user(str(member.id))

    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await db.reset_points(str(member.id))

    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        await db.remove_user(str(member.id))



    async def handle_warnings(self, ctx):
        mentions = ctx.mentions
        
        if mentions is None:
            return

        target_user = mentions[0]
        warnings = await db.add_warning_to_user(str(target_user.id))

        if warnings >= 3:
            warning_log_channel = self.bot.get_channel(WARNING_CHANNEL)

            pfp = target_user.avatar.url
            embed = discord.Embed(color=0x7e016f)
            embed.set_author(name=f"Music Feedback: {target_user.name}", icon_url=ctx.guild.icon.url)
            embed.set_thumbnail(url=pfp)
            embed.add_field(name="__MF Warnings__", value=f"User has **{warnings}** warnings.", inline=False)
            embed.add_field(name="Use ``.warnings (user id)`` to see infractions:",
                            value=f"{target_user.mention} | {target_user.id}", inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await warning_log_channel.send(embed=embed)
            await warning_log_channel.send(f"<@&{MODERATORS_ROLE_ID}>")
            

    async def handle_promotion_check(self, ctx):
        is_promoting = False
        
        if 'soundcloud.com' in ctx.content.lower():
            is_promoting = await SCP_checker.check_soundcloud(ctx)    
        elif 'youtube.com' in ctx.content.lower() or 'youtu.be' in ctx.content.lower():
            is_promoting = await YT_checker.check_youtube(ctx)
        elif 'open.spotify'  in ctx.content.lower():
            is_promoting = await Spoti_checker.check_spotify(ctx)
            
        
        if is_promoting:
            channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

            pfp = ctx.author.avatar.url
            embed = discord.Embed(color=0x7e016f)
            embed.set_author(name=f"Music Feedback: {ctx.author.name}", icon_url=ctx.guild.icon.url)
            embed.set_thumbnail(url=pfp)
            embed.add_field(name="__Possible promotion alert__",
                            value=f"{ctx.author.mention} | {ctx.author.id}"
                                    f" is under suspicion of sending SoundCloud links at {ctx.jump_url}.",
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=embed)
            await channel.send(f"<@&{MODERATORS_ROLE_ID}>")    


async def setup(bot):
    await bot.add_cog(User_listener(bot))
