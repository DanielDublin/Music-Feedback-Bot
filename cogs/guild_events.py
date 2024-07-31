import discord
from discord.ext import commands
from data.constants import MFL_INFO, SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_XMAS_ID

pfp_url = ""

class Guild_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = [] # initiate array for queue
        
    def guild_only(ctx):
        return ctx.guild is not None

    @commands.check(guild_only)
    @commands.command(help = "Use to submit entries to events.", brief = "(link, file, text)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def submit(self, ctx):

        allowed_channels_list = [
            MFL_INFO,
            SUBMISSIONS_CHANNEL_XMAS_ID,
            SUBMISSIONS_CHANNEL_ID,
            GENERAL_CHAT_CHANNEL_ID
        ]

        # add author to the queue
        self.queue.append(ctx.author.mention)

        if not ctx.channel.id in allowed_channels_list:
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

    # queue command
    @commands.command(help="Displays the queue of submissions.")
    @commands.check(guild_only)
    async def queue(self, ctx):
        # handle if queue empty
        if not self.queue:
            await ctx.send("The queue is empty.")
            return

        # embed for queue display
        embed = discord.Embed(color=0x7e016f)
        embed.title = "Current submissions:"
        # initiate queue
        queue_message = ""
        # number each member
        for index, item in enumerate(self.queue, start = 1):
            queue_message += f"{index}. {item}\n"
        embed.add_field(name="Submissions", value=queue_message, inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=pfp_url)

        await ctx.send(embed=embed)

    # only allow members with Event Host role to run clearq command
    @commands.command(help="Displays the queue of submissions.")
    @commands.check(guild_only)
    async def clearq(self, ctx):
        event_host = discord.utils.get(ctx.guild.roles, name="Event Host")
        if event_host in ctx.author.roles:
            self.queue.clear()
            await ctx.send("The queue has been cleared.")

async def setup(bot):
    await bot.add_cog(Guild_events(bot))
