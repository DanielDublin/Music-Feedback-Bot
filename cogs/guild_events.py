import discord
from discord.ext import commands
from data.constants import SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_XMAS_ID

pfp_url = ""

class Guild_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def guild_only(ctx):
        return ctx.guild is not None

    @commands.check(guild_only)
    @commands.command(help = "Use to submit entries to events.", brief = "(link, file, text)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def submit(self, ctx):

        allowed_channels_list = [SUBMISSIONS_CHANNEL_XMAS_ID, SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID]
        
        if ctx.channel.id in allowed_channels_list:
            await ctx.channel.send(
                    f"{ctx.author.mention}, please use the correct channel to post your submission.", delete_after=60) 
            await ctx.message.delete()
            return
        
        file = None
        

        if len(ctx.message.attachments):  # Checks if the correct channels were used to be sent a file
            file = await ctx.message.attachments[0].to_file()

        await ctx.message.delete()

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name=":ballot_box_with_check:  Success!",
                        value=f"{ctx.author.mention}, your submission has been received.", inline=False)
        global pfp_url
        creator_user = await self.bot.fetch_user(self.bot.owner_id)
        pfp_url = creator_user.avatar.url
        
        embed.set_footer(text=f"Made by FlamingCore", icon_url=pfp_url)
        await ctx.channel.send(embed=embed)
        channel = self.bot.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        await channel.send(
            f"-----------\n**Sent from:** <#{ctx.channel.id}>\n**Submitted by:**"
            f" <@!{ctx.author.id}>\n {ctx.message.content}",
            file=file)


async def setup(bot):
    await bot.add_cog(Guild_events(bot))
