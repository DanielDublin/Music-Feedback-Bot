import discord
from discord.ext import commands
from database.db import init_database


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    #MF balance              
    async def balance(users, member: discord.Member, message):  
        if message.content.startswith("<MF points") or message.content.startswith("<mf points") or message.content.startswith("<MF Points"):
            guild = client.get_guild(732355624259813531)
            values = {k: v for k, v in sorted(users.items(), key = lambda item: item[1]['points'], reverse = True)}
            names = ''

            for position, user in enumerate(values, start = 1):
                if str(member.id) in user: 
                    if user in values:
                        names += f"{position}"               

            points = users[f"{member.id}"]["points"] 
            author = message.author
            pfp = author.avatar_url            
            myEmbed = discord.Embed(color = 0x7e016f)
            myEmbed.set_author(name = f"Music Feedback: {member}", icon_url = guild.icon_url) 
            myEmbed.set_thumbnail(url = pfp)
            myEmbed.add_field(name = "__MF Points__", value = f"You have **{points}** MF point(s).", inline = False)
            myEmbed.add_field(name = "__MF Rank__", value = f"Your MF Rank is **#{names}** out of **{guild.member_count}**.", inline = False)
            await message.channel.send(embed = myEmbed) 

    #MF leaderboard 
    async def leaderboard(users, member: discord.Member, message):
        if message.content.startswith("<MF top") or message.content.startswith("<mf top"):
            send = message.channel.send
                   
            top_users = {k: v for k, v in sorted(users.items(), key = lambda item: item[1]['points'], reverse = True)}
                
            names = ''
            top_names = ''
        
            for position, user in enumerate(top_users, 0):
                if user in users:            
                    if position < 5:
                        names += f"{position+1} - <@!{user}> | **{top_users[user]['points']}** MF point(s)\n"
 
                    if position == 0: 
                        top_names += f"{user}"
                        guild = client.get_guild(732355624259813531) 
                        user_id = top_names
                        user = discord.utils.get(guild.members, id = int(user_id))
                        avatar = user.avatar_url                 

            guild = client.get_guild(732355624259813531)
            embed = discord.Embed(color = 0x7e016f)
            embed.set_author(name = "Top Music Feedbackers", icon_url = guild.icon_url)         
            embed.add_field(name = "Members", value = names, inline = False)
            embed.set_thumbnail(url = avatar)
            await send(embed = embed)            


        #Add points        
    async def add_points_to_json(users, user, message):
        if message.content.startswith("<MFR") or message.content.startswith("<mfr"):
            users[f"{user.id}"]["points"] += 1
            points = users[f"{user.id}"]["points"]
            mention = message.author.mention
            await message.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).", delete_after = 4) 
            channel = client.get_channel(749443325530079314)
            my_ID = "412733389196623879"
            myEmbed = discord.Embed(color = 0x7e016f)
            myEmbed.add_field(name = "Feedback Notice", value = f"{mention} has **given feedback** and now has **{points}** MF point(s).", inline = False)
            await channel.send(embed = myEmbed)        


    #Use points        
    async def use_points_from_json(users, user, message):     
        if message.content.startswith("<MFS") or message.content.startswith("<mfs"):
            users[f"{user.id}"]["points"] -= 1
            points = users[f"{user.id}"]["points"]
            mention = message.author.mention
            if users[f"{user.id}"]["points"] <= -1:
                await message.channel.send(f"{mention}, you do not have any MF points. Please give feedback first.", delete_after = 5)  
                await message.delete()
                channel = client.get_channel(749443325530079314)
                my_ID = "412733389196623879"
                await channel.send(f"<@{my_ID}>:") 
                myEmbed = discord.Embed(color = 0x7e016f)
                myEmbed.add_field(name = "**ALERT**", value = f"{mention} tried sending a track for feedback with **0** MF points.", inline = False) 
                await channel.send(embed = myEmbed)
                if users[f"{user.id}"]["points"] <= -1:
                    users[f"{user.id}"]["points"] += 1
                
            elif users[f"{user.id}"]["points"] >= 0:
                await message.channel.send(f"{mention} have used 1 MF point. You now have **{points}** MF point(s).", delete_after = 4)
                channel = client.get_channel(749443325530079314)
                my_ID = "412733389196623879"
                myEmbed = discord.Embed(color = 0x7e016f)
                myEmbed.add_field(name = "Feedback Notice", value = f"{mention} has **submitted** a work for feedback and now has **{points}** MF point(s).", inline = False)
                await channel.send(embed = myEmbed)        

                




    @commands.command()
    async def add_points(self, ctx, points: int):
        """Add points to a user."""
        pool = await init_database()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                user_id = ctx.author.id
                await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = await cursor.fetchone()
                if user:
                    new_points = user['points'] + points
                    await cursor.execute("UPDATE users SET points = %s WHERE id = %s", (new_points, user_id))
                else:
                    await cursor.execute("INSERT INTO users (id, name, points) VALUES (%s, %s, %s)", (user_id, ctx.author.display_name, points))

        await ctx.send(f"You now have {new_points} points!")

async def setup(bot):
    await bot.add_cog(General(bot))