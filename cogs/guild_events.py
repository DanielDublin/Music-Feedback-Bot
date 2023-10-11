import discord
from discord.ext import commands


SUBMISSIONS_CHANNEL_ID = 1103427357781528597
GENERAL_CHAT_CHANNEL_ID = 1103427357781528597
MOD_SUBMISSION_LOGGER_CHANNEL_ID = 1103427357781528597

class Guild_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    #note: need to add functions in db of fetch_points, fetch_rank, reduce_points, add_points, fetch_top_users

    #MF points - Shows how many points the current user has 
    @commands.command()      
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def submit(self, ctx :discord.Message): 
        
        global SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MOD_SUBMISSION_LOGGER_CHANNEL_ID
        guild = ctx.guild
        file = None

        if ctx.attachments: # Checks if the correct channels were used to be sent a file
            if ctx.channel.id == SUBMISSIONS_CHANNEL_ID or ctx.channel.id == GENERAL_CHAT_CHANNEL_ID:
                file = await ctx.attachments[0].to_file() 
                
        await ctx.delete()
        
        embed = discord.Embed(color = 0x7e016f)
        embed.add_field(name = ":ballot_box_with_check:  Success!", value = "Your submission has been received.", inline = False)                
        await ctx.channel.send(embed = embed)
        channel = self.bot.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        await channel.send(f"-----------\n**Sent from:** <#{ctx.channel.id}>\n**Submitted by:** <@!{ctx.author.id}>\n {ctx.content}", file=file)    
                      
   
async def setup(bot):
    await bot.add_cog(Guild_events(bot))