import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

                 
                                    
    #Mod give points     
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def MFadd(self, ctx :discord.Message, user :discord.Member, points :int = 1):
        
        await db.add_points(user.id, points)
        current_points = await db.fetch_points(user.id)
        myEmbed = discord.Embed(color = 0x7e016f)
        myEmbed.add_field(name = "Music Feedback", value = f"You have given {user.mention} 1 MF point. They now have **{points}** MF point(s).", inline = False)
        await ctx.send(embed = myEmbed)                       

      

    #Mod remove points 
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def MFremove(self, ctx :discord.Message, user :discord.Member, points :int = 1):
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
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def MFclear(self, ctx :discord.Message, user: discord.Member):
    
        with open ("MF Points.json", "r") as f:
            users = json.load(f) 
        
            if str(user.id) in users:
                users[f"{user.id}"]["points"] = 0
                points = users[f"{user.id}"]["points"]
                myEmbed = discord.Embed(color = 0x7e016f)
                myEmbed.add_field(name = "Music Feedback", value = f"{user.mention} has lost all their MF points. They now have **{points}** MF points.", inline = False)
                await ctx.send(embed = myEmbed)             

        with open("MF Points.json", "w") as f:
            json.dump(users, f,indent = 4)  
        
     
    #Mod balance        
    @client.command()
    async def MFbalance(self, ctx :discord.Message, user: discord.Member):
    
        with open ("MF Points.json", "r") as f:
            users = json.load(f) 
        
            if str(user.id) in users:
                points = users[f"{user.id}"]["points"]
                myEmbed = discord.Embed(color = 0x7e016f)
                myEmbed.add_field(name = "Music Feedback", value = f"{user.mention} has **{points}** MF point(s).", inline = False)
                await ctx.send(embed = myEmbed)             
         
        with open("MF Points.json", "w") as f:
            json.dump(users, f,indent = 4)        
        


async def setup(bot):
    await bot.add_cog(Admin(bot))
