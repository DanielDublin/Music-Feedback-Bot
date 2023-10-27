import discord
from discord.ext import commands
from data.constants import SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MOD_SUBMISSION_LOGGER_CHANNEL_ID


class Guild_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @commands.command(help = "Use to submit entries to events.\n``<MF Submit text/file``")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def submit(self, ctx):

        file = None

        if len(ctx.message.attachments):  # Checks if the correct channels were used to be sent a file
            if ctx.channel.id == SUBMISSIONS_CHANNEL_ID or ctx.channel.id == GENERAL_CHAT_CHANNEL_ID:
                file = await ctx.message.attachments[0].to_file()

        await ctx.message.delete()

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name=":ballot_box_with_check:  Success!",
                        value=f"{ctx.author.mention}, your submission has been received.", inline=False)
        await ctx.channel.send(embed=embed)
        channel = self.bot.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        await channel.send(
            f"-----------\n**Sent from:** <#{ctx.channel.id}>\n**Submitted by:**"
            f" <@!{ctx.author.id}>\n {ctx.message.content}",
            file=file)


async def setup(bot):
    await bot.add_cog(Guild_events(bot))
