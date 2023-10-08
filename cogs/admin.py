import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

     #add to db.py reset_points            
                                    
    #Mod give points     
    @commands.command(name = "add", aliases = [" add"])
    @commands.has_permissions(administrator = True)
    async def add(self, ctx :discord.Message, user :discord.Member, points :int = 1):
        
        await db.add_points(user.id, points)
        current_points = await db.fetch_points(user.id)
        myEmbed = discord.Embed(color = 0x7e016f)
        myEmbed.add_field(name = "Music Feedback", value = f"You have given {user.mention} 1 MF point. They now have **{points}** MF point(s).", inline = False)
        await ctx.send(embed = myEmbed)                       

      

    #Mod remove points 
    @commands.command(name = "remove", aliases = [" remove"])
    @commands.has_permissions(administrator = True)
    async def remove(self, ctx :discord.Message, user :discord.Member, points :int = 1):
        current_points = await db.fetch_points(user.id)
        
        if current_points-points:
            await db.reduce_points(user.id, points)       
            embed = discord.Embed(color = 0x7e016f)
            embed.add_field(name = "Music Feedback", value = f"You have taken {points} MF point from {user.mention}. They now have **{current_points - points}** MF point(s).", inline = False)
            await ctx.channel.send(embed = embed) 
                
        else:    
            embed = discord.Embed(color = 0x7e016f)
            embed.add_field(name = "Music Feedback", value = f"Can't remove points, This member already has **{current_points}** MF points.", inline = False)
            await ctx.channel.send(embed = embed)   
                  
        

    #Mod clear points        
    @commands.command(name = "clear", aliases = [" clear"])
    @commands.has_permissions(administrator = True)
    async def clear(self, ctx :discord.Message, user: discord.Member):
    
        await db.reset_points(user.id)   
        myEmbed = discord.Embed(color = 0x7e016f)
        myEmbed.add_field(name = "Music Feedback", value = f"{user.mention} has lost all their MF points. They now have **0** MF points.", inline = False)
        await ctx.channel.send(embed = myEmbed)             

        
     
    #Mod balance        WHY U NO PERMS?!
    @commands.command(name = "balance", aliases = [" balance"])
    @commands.has_permissions()
    async def balance(self, ctx :discord.Message, user: discord.Member):
    
        points = await db.fetch_points(user.id)
        embed = discord.Embed(color = 0x7e016f)
        embed.add_field(name = "Music Feedback", value = f"{user.mention} has **{points}** MF point(s).", inline = False)
        await ctx.channel.send(embed = embed)             
       
        


async def setup(bot):
    await bot.add_cog(Admin(bot))
