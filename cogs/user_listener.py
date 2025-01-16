from re import T
from tarfile import NUL
import discord
import asyncio
from discord.ext import commands
import database.db as db
import modules.promotion_checkers.soundcloud_promotion_checker as SCP_checker
import modules.promotion_checkers.youtube_promotion_checker as YT_checker
import modules.promotion_checkers.spotify_promotion_checker as Spoti_checker
from datetime import datetime, timedelta
from data.constants import WARNING_CHANNEL, MODERATORS_CHANNEL_ID, MODERATORS_ROLE_ID, GENERAL_CHAT_CHANNEL_ID, \
    MUSIC_RECCOMENDATIONS_CHANNEL_ID, MUSIC_CHANNEL_ID, INTRO_MUSIC, DYNO_ID, VLADHOG_ID, QUARANTINE_LOG_CHANNEL_ID, QUARANTINE_ROLE_ID

# dan
promotion_whitelist_id = [358631356248489984]

class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url =""
        self.PRIMUS_COOLDOWN = False
        self.PRIMUS_COOLDOWN_TIME = 10
        self.MUSIC_TRIO_CHANNEL_IDS_LIST = [MUSIC_RECCOMENDATIONS_CHANNEL_ID, MUSIC_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID]

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author.bot and (ctx.author.id != DYNO_ID or (ctx.interaction is not None and ctx.interaction.name != 'warn')):
            if ctx.author.id == VLADHOG_ID:
                await self.handle_vladhog(ctx)
            else:
                return
        
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        if not self.pfp_url :
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            
        content = ctx.content
        
        content_remove_spaces = content.replace(' ', '').lower()
        if  not ctx.author.guild_permissions.kick_members and content_remove_spaces.startswith('>mf'):
            await self.handle_wrong_prefix(ctx)

        if ctx.author.id == DYNO_ID:  # is a warning
            if len(ctx.embeds[0].fields):
                
                await self.handle_warnings(ctx, True)
                
        elif ctx.content.lower().startswith("/warn ") and ctx.author.guild_permissions.kick_members: # warn checker
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
        
        kicks = await db.fetch_kicks(str(member.id))
        if kicks:
            await self.handle_kicked_alert(member, kicks)
            
            


    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        
        audit_log_entry = None
        
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            
            cutoff_time = discord.utils.utcnow() - timedelta(minutes=2)  # Adjust the time window as needed
            if entry.target == member and entry.created_at >= cutoff_time:
                
                # Get all matching kicks, filter the newest one if exists
                try:
                    async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                        audit_log_entry = entry
                        break
                except Exception as e:
                    print(str(e))
            
        if audit_log_entry is not None and audit_log_entry.target == member:
            # User was kicked
            await db.reset_points(str(member.id), True)
            await db.add_kick(str(member.id))
        else:
            await db.reset_points(str(member.id))
                        


    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        await db.remove_user(str(member.id))

    async def convert_mention_to_member(self, ctx, mention_string):
        
        user_id = mention_string
        member = None
        
        try:
            if mention_string.startswith('<@!'):
                user_id = int(mention_string.strip('<@!>'))
            elif mention_string.startswith('<@'):
                user_id = int(mention_string.strip('<@>'))
            else:
                 user_id = int(mention_string)
        except Exception as e:
            return None
       
        guild = ctx.channel.guild  # Assuming you have access to the guild instance

        # Attempt to fetch the member from the guild
     
        member = guild.get_member(user_id)
     
        # If member is None, attempt to fetch the member using fetch_member
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except Exception as e:
                return None
            
        return member        
        
    
    

    async def handle_warnings(self, ctx, is_embed = False):
        
        mentioned_users = None
  
        if is_embed:
            embed = ctx.embeds[0]
            
            for field in embed.fields:
                name = field.name  
                    
                if name.lower() == "user":
                    target = await  self.convert_mention_to_member(ctx, field.value)
                    
                    if target is not None:
                        mentioned_users = [target]
                    break
        else:
            mentioned_users = ctx.mentions
            if not len(mentioned_users):
                words = ctx.content.split()
                target_id = words[1]
                target = await self.convert_mention_to_member(ctx, target_id)
                if target is not None:
                    mentioned_users = [target]
          
                


        if mentioned_users is None or not len(mentioned_users):
            return

        target_user = mentioned_users[0]
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
            

    async def handle_kicked_alert(self, member: discord.Member, kicks: int):
       
        channel = self.bot.get_channel(WARNING_CHANNEL)
        pfp = member.avatar.url
        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name=f"Music Feedback: {member.name}", icon_url=member.guild.icon.url)
        embed.set_thumbnail(url=pfp)
        embed.add_field(name="__Kicked user re-joined__",
                        value=f"{member.mention} | {member.id}"
                                f"\nThis user came back after they were kicked {kicks} times.",
                        inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await channel.send(embed=embed)
    
            

    async def handle_promotion_check(self, ctx):
        
        global promotion_whitelist_id
        if ctx.author.id in promotion_whitelist_id:
            return

        is_promoting = False
        suspicion = "Nothing"
        if 'soundcloud.com' in ctx.content.lower():
            is_promoting = await SCP_checker.check_soundcloud(ctx)
            suspicion = "SoundCloud"
        elif 'youtube.com' in ctx.content.lower() or 'youtu.be' in ctx.content.lower():
            is_promoting = await YT_checker.check_youtube(ctx)
            suspicion = "YouTube"
        elif 'open.spotify'  in ctx.content.lower():
            is_promoting = await Spoti_checker.check_spotify(ctx)
            suspicion = "Spotify"
            
        
        if is_promoting:
            channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

            pfp = ctx.author.avatar.url
            embed = discord.Embed(color=0x7e016f)
            embed.set_author(name=f"Music Feedback: {ctx.author.name}", icon_url=ctx.guild.icon.url)
            embed.set_thumbnail(url=pfp)
            embed.add_field(name="__Possible promotion alert__",
                            value=f"{ctx.author.mention} | {ctx.author.id}"
                                    f" is under suspicion of sending {suspicion} links at {ctx.jump_url}.",
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=embed)
            await channel.send(f"<@&{MODERATORS_ROLE_ID}>")    

    async def handle_wrong_prefix(self, message):
        
        try:
            await message.channel.send(
                f"{message.author.mention} Aw snap,\n Looks like your command input was wrong. Your message was DMed to you for future"
                f" reference.\nPlease use ``<MF help`` for further information.",
                delete_after=60)
            await message.delete()
 
        except Exception as e:
            print(str(e))
            await message.channel.send(f'{message.author.mention}, Looks like your command input was wrong.'
                                    f'\n**ATTENTION**: _We could not DM you with a copy of your message.'
                                    f'\nPlease contact Moderators for help or re-read'
                                    f' ``<MF help`` for more information._',
                                    delete_after=60)
            await message.delete()
            
    async def handle_vladhog(self, ctx: discord.Message):
        
        if ctx.channel.id != QUARANTINE_LOG_CHANNEL_ID or not ctx.embeds:
            return
        
       
        embed = ctx.embeds[0]
        
        if not embed.description or not embed.fields:
            return
        
        user = None;

        try:
            if "and is malicious" in embed.description:
                user_id = embed.fields[1].value
                user = ctx.guild.get_member(int(user_id))
                
                if user is None:
                    user = await self.bot.fetch_user(int(user_id))

                if user.bot:
                    return
                await ctx.channel.send(f"<@&{MODERATORS_ROLE_ID}>")
        except Exception as e:
            print(str(e))
            return
        

        try:
            if user is not None:
                await user.add_roles(ctx.guild.get_role(QUARANTINE_ROLE_ID))
        except Exception as e:
            print(str(e))
            return

async def setup(bot):
    await bot.add_cog(User_listener(bot))
