import discord
from discord.ext import commands
import database.db as db


FEEDBACK_CHANNEL_ID = 1103427357781528597
SERVER_OWNER_ID = 1103427357781528597

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    #note: need to add functions in db of fetch_points, fetch_rank, reduce_points, add_points, fetch_top_users

    #MF points - Shows how many points the current user has 
    @commands.command(aliases = [" balance", "balance", " points"])             
    async def points(self, ctx :discord.Message, user :discord.Member = None): 
        
        # Gathering data
        if user is None:
            user = ctx.author
            
        guild = ctx.guild
        points = await db.fetch_points(user.id)
        rank = await db.fetch_rank(user.id)
        pfp = user.avatar_url            
        
        embed = discord.Embed(color = 0x7e016f)
        embed.set_author(name = f"Music Feedback: {user}", icon_url = guild.icon_url) 
        embed.set_thumbnail(url = pfp)
        embed.add_field(name = "__MF Points__", value = f"You have **{points}** MF point(s).", inline = False)
        embed.add_field(name = "__MF Rank__", value = f"Your MF Rank is **#{rank}** out of **{guild.member_count}**.", inline = False)
        await ctx.channel.send(embed = embed)
            


    #MF leaderboard
    @commands.command(aliases = ["leaderboard"] )  
    async def top(self, ctx : discord.Member):
     
        top_users = await db.fetch_top_users()   
        guild = ctx.guild
        names = ''
      
        for user_id, user_data in top_users.items():
            rank = user_data["rank"]
            points = user_data["points"]
            names += f"{rank} - <@{user_id}> | **{points}** MF point(s)\n"

            if rank == 1:    
                user = discord.utils.get(guild.members, id = int(user_id))
                avatar = user.avatar_url                 

        embed = discord.Embed(color = 0x7e016f)
        embed.set_author(name = "Top Music Feedbackers", icon_url = guild.icon_url)         
        embed.add_field(name = "Members", value = names, inline = False)
        embed.set_thumbnail(url = avatar)
        await ctx.channe.send(embed = embed)            


    #Add points 
    @commands.command(name = "R")       
    async def MFR_command(self, ctx : discord.Message):
        global FEEDBACK_CHANNEL_ID
        
        await db.add_points(ctx.author.id, 1)
        mention = ctx.author.mention
        points = await db.fetch_points(ctx.author.id)
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        
        embed = discord.Embed(color = 0x7e016f)
        embed.add_field(name = "Feedback Notice", value = f"{mention} has **given feedback** and now has **{points}** MF point(s).", inline = False)
        
        await ctx.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).", delete_after = 4) 
        await channel.send(embed = embed)  # Logs channel


    #Use points        
    @commands.command(name = "S")       
    async def MFs_command(self, ctx : discord.Message):
        global FEEDBACK_CHANNEL_ID, SERVER_OWNER_ID
        
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        points = await db.fetch_points(ctx.author.id)
        mention = ctx.author.mention
        
        if points: # user have points, reduce them and send message + log
            points -= 1
            await db.reduce_points(ctx.author.id, 1)
            await ctx.channel.send(f"{mention} have used 1 MF point. You now have **{points}** MF point(s).", delete_after = 4)
            
            embed = discord.Embed(color = 0x7e016f)
            embed.add_field(name = "Feedback Notice", value = f"{mention} has **submitted** a work for feedback and now has **{points}** MF point(s).", inline = False)
            await channel.send(embed = embed)   


        else: # User doesn't have points
            await ctx.channel.send(f"{mention}, you do not have any MF points. Please give feedback first.", delete_after = 5)  
            await ctx.delete()
            await channel.send(f"<@{SERVER_OWNER_ID}>:") 
            
            embed = discord.Embed(color = 0x7e016f)
            embed.add_field(name = "**ALERT**", value = f"{mention} tried sending a track for feedback with **0** MF points.", inline = False) 
            await channel.send(embed = embed)
        
                
   
async def setup(bot):
    await bot.add_cog(General(bot))