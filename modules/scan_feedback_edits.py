import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
import database.db as db

class ScanFeedbackEdits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        """
        Handle misspellings, capitalizations, switches, additions.
        ------was working on getting the ticket to send - the points deduct well
        add message in feedback channel that lets member know of points change on edit
        include excerpt of before and after
        """

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Detect when a message is edited from <MFR to <MFS
        if "MFR" in before.content and "<MFS" in after.content:
            await self.MFR_to_MFS_switch(before, after)

    # handles edited messages from <MFR to <MFS - deducts points
    async def MFR_to_MFS_switch(self, before: discord.Message, after: discord.Message):
        # Get user context from the edited message
        ctx = after.guild.get_member(after.author.id)

        if not ctx:
            print("User not found.")
            return

        # Access TimerCog to check for double points
        base_timer_cog = self.bot.get_cog("TimerCog")
        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return

        # Determine points deduction based on double points or not
        if "Double Points" in base_timer_cog.timer_handler.active_timer:
            points_deducted = 3
        else:
            points_deducted = 2

        # Deduct points
        await db.reduce_points(str(ctx.id), points_deducted)


        # send embed if thread exists
        feedback_channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        embed = discord.Embed(
            title="Points Deduction for Edit",
            description=f"User {ctx.name} edited their feedback message from `<MFR` to `<MFS` and had {points_deducted} MF points deducted.",
            color=discord.Color.red()
        )
        embed.add_field(name="Before Edit", value=before.content, inline=False)
        embed.add_field(name="After Edit", value=after.content, inline=False)
        await feedback_channel.send(embed=embed)

    async def MFR_to_MFS_embed(self, ctx, formatted_time, message_link, points):
        log_id = self.user_thread[ctx.author.id]['log_id']
        base_timer_cog = self.bot.get_cog("TimerCog")

        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return


        if "Double Points" in base_timer_cog.timer_handler.activer:
            points_deducted = 3
        else:
            points_deducted = 2

        embed = discord.Embed(
            title=f"Ticket # {log_id}",
            description=f"{formatted_time}",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Edited <MFR to <MFS", value=f"**{points_deducted}** MF points were deducted.", inline=True)
        embed.add_field(name=f"{message_link}", value="", inline=False)
        embed.set_footer(text="Some Footer Text")
        return embed


async def setup(bot):
    await bot.add_cog(ScanFeedbackEdits(bot))
