import discord
import logging
from discord.ext import commands
from data.constants import MFL_INFO, SUBMISSIONS_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MOD_SUBMISSION_LOGGER_CHANNEL_ID, SUBMISSIONS_CHANNEL_XMAS_ID
from modules.cooldowns import admin_bypass_cooldown

logger = logging.getLogger(__name__)

class Guild_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = [] # initiate array for queue
        
    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(help = "Use to submit entries to events.", brief = "(link, file, text)")
    @admin_bypass_cooldown(1, 5)
    async def submit(self, ctx):

        allowed_channels_list = [
            MFL_INFO,
            SUBMISSIONS_CHANNEL_XMAS_ID,
            SUBMISSIONS_CHANNEL_ID,
            GENERAL_CHAT_CHANNEL_ID
        ]

        if not ctx.channel.id in allowed_channels_list:
            await ctx.channel.send(
                    f"{ctx.author.mention}, please use the correct channel to post your submission.", delete_after=60)
            await ctx.message.delete()
            return

        self.queue.append(ctx.author.mention)
        
        file = None
        

        if len(ctx.message.attachments):  # Checks if the correct channels were used to be sent a file
            file = await ctx.message.attachments[0].to_file()

        await ctx.message.delete()

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name=":ballot_box_with_check:  Success!",
                        value=f"{ctx.author.mention}, your submission has been received.", inline=False)
        pfp_url = await self.bot.get_owner_pfp_url()
        embed.set_footer(text=f"Made by FlamingCore", icon_url=pfp_url)
        await ctx.channel.send(embed=embed)
        channel = self.bot.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        if not channel:
            logger.error("MOD_SUBMISSION_LOGGER_CHANNEL_ID %s not found", MOD_SUBMISSION_LOGGER_CHANNEL_ID)
            return
        await channel.send(
            f"-----------\n**Sent from:** <#{ctx.channel.id}>\n**Submitted by:**"
            f" <@!{ctx.author.id}>\n {ctx.message.content}",
            file=file)

    # queue command
    @commands.command(help="Displays the queue of submissions.")
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
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())

        await ctx.send(embed=embed)

    # only allow members with Event Host role to run clearq command
    @commands.command(help="Displays the queue of submissions.")
    async def clearq(self, ctx):
        event_host = discord.utils.get(ctx.guild.roles, name="Event Host")
        if event_host in ctx.author.roles:
            self.queue.clear()
            await ctx.send("The queue has been cleared.")

async def setup(bot):
    await bot.add_cog(Guild_events(bot))
