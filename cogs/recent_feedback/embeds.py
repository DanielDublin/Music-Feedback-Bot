import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from .tracker import Tracker

class FeedbackChannelEmbeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_sticky_embed = None

    @commands.Cog.listener()
    async def on_message(self, message):
        feedback_channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        if message.channel != feedback_channel or message.author.bot:
            return

        try:
            tracker_cog = self.bot.get_cog("Tracker")
            if not tracker_cog:
                print("Tracker cog not found")
                return
        except Exception as e:
            print(f"Tracker cog not found: {e}")
            return

        try:
            requests = await tracker_cog.pull_db_feedback()
        except Exception as e:
            print(f"Error pulling feedback requests: {e}")
            return

        print("Fetched requests:", requests)

        if self.old_sticky_embed:
            try:
                await self.old_sticky_embed.delete()
            except discord.errors.NotFound:
                pass  # Ignore if the old embed was already deleted

        embed = discord.Embed(
            title="Recent Feedback Requests",
            description="""
            __YOU MUST GIVE FEEDBACK FIRST__\n
            Use `<MFR` to give feedback.\n
            Use `<MFS` to submit your song for feedback.\n
            Use #⁠feedback-discussion for conversation.
            """,
            color=discord.Color.green()
        )

        if requests:
            for req in requests:
                embed.add_field(
                    name=f"[{req['user_name']}]({req['message_link']}) (ID: {req['message_id']})",
                    value=f"Points Requested: {req['points_requested']} | Points Remaining: {req['points_remaining']}",
                    inline=False
                )
        else:
            embed.add_field(
                name="No Requests",
                value="No open feedback requests found.",
                inline=False
            )

        self.old_sticky_embed = await feedback_channel.send(embed=embed)
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(FeedbackChannelEmbeds(bot))