import database.db as db
from .embeds import Embeds
import discord
from data.constants import FEEDBACK_CHANNEL_ID, FEEDBACK_ACCESS_CHANNEL_ID, SERVER_OWNER_ID, FEEDBACK_CATEGORY_ID

class PointsLogic:
    def __init__(self, bot, user_thread, ctx=None):
        self.bot = bot
        self.user_thread = user_thread
        self.ctx = ctx
        self.embeds = Embeds(bot, user_thread)

    async def send_embed(self, user_id=None, ticket_counter=None, thread=None, called_from_zero=False):
        if user_id is None:
            user_id = self.ctx.author.id
            print("user_id is None")

        if ticket_counter is None:
            ticket_counter = self.user_thread.get(self.ctx.author.id, [None, 0])[1]
            print("ticket_counter is None")

        points = await db.fetch_points(str(user_id))

        print(f"{called_from_zero}")

        if called_from_zero:
            print("called_from_zero")
            try:
                await self.handle_zero_points_submission(self.ctx, thread, ticket_counter)
            except Exception as e:
                await self.ctx.send(f"An error occurred: {str(e)}")
            return

    async def handle_zero_points_submission(self, ctx, thread, ticket_counter):
        print("handle_zero_points_submission")
        if thread is None:
            await ctx.send("Thread not specified for zero points submission.")
            return

        mention = ctx.author.mention
        channel = self.bot.get_channel(FEEDBACK_ACCESS_CHANNEL_ID)

        try:
            embed = await self.embeds.mfs_with_zero_points(ctx, ticket_counter, thread)
            await thread.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred when sending embed: {str(e)}")
            return

        try:
            await self.send_messages_to_user(ctx.message)
            await ctx.send(
                f"{mention}, you do not have any MF points."
                f" Please give feedback first.\nYour request was DMed to you for future"
                f" reference.\nPlease re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions.",
                delete_after=60
            )
        except Exception:
            await ctx.send(
                f"{mention}, you do not have any MF points. Please give feedback first.\n"
                f"**ATTENTION**: _We could not DM you with a copy of your submission._\n"
                f"Please contact Moderators or re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}>.",
                delete_after=60
            )

        await ctx.message.delete()

        # Send mod alert
        try:
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(
                name="**ALERT**",
                value=f"{mention} tried sending a track for feedback with **0** MF points.",
                inline=False
            )
            embed.set_footer(text="Made by FlamingCore", icon_url=self.bot.user.avatar.url)
            await channel.send(f"<@{SERVER_OWNER_ID}>:")
            await channel.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Could not send alert embed: {str(e)}")

