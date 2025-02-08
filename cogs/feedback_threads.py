import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from datetime import datetime
import database.db as db

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_thread = {}  # Nested user: list[thread_id, ticket_counter]

    async def create_feedback_thread(self, ctx, mfr_points, points):
        await self.bot.wait_until_ready()
        thread_channel = self.bot.get_channel(1103427357781528597)  # Replace with your actual thread channel ID
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%d-%m %H:%M")

        # Check if the mentioned user has a stored thread in the dict
        if ctx.author.id in self.user_thread:
            embed = await self.existing_thread(ctx, formatted_time, message_link, mfr_points, points)
            existing_thread = self.bot.get_channel(self.user_thread[ctx.author.id][0])  # Access thread_id
            await existing_thread.send(embed=embed)
            return

        # If no existing thread, create a new one
        await self.new_thread(ctx, formatted_time, message_link, thread_channel)

        # handles <MFR
        if ctx.command.name == 'R':
            embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
        # handles <MFS
        elif ctx.command.name == 'S':
            embed = await self.MFS_embed(ctx, formatted_time, message_link, points)

        new_thread = self.bot.get_channel(self.user_thread[ctx.author.id][0])  # Access thread_id
        await new_thread.send(embed=embed)

    async def MFR_embed(self, ctx, formatted_time, message_link, mfr_points, points):
        ticket_counter = self.user_thread[ctx.author.id][1]  # Access ticket_counter from the nested array

        # MFR points logic
        if mfr_points == 1:
            embed = discord.Embed(
                title=f"Ticket #{ticket_counter}",
                description=f"{formatted_time}",
                color=discord.Color.green()
            )
            embed.add_field(name="<MFR", value=f"Gained **{mfr_points}** point and now has **{points}** MF points.", inline=True)
            embed.add_field(name=f"{message_link}", value="", inline=False)
            embed.set_footer(text="Some Footer Text")
            return embed
        elif mfr_points == 2:
            embed = discord.Embed(
                title=f"Ticket #{ticket_counter}",
                description=f"{formatted_time}",
                color=discord.Color.purple()
            )
            embed.add_field(name="<MFR during Double Points", value=f"Gained **{mfr_points}** points and now has **{points}** MF points.", inline=True)
            embed.add_field(name=f"{message_link}", value="", inline=False)
            embed.set_footer(text="Some Footer Text")
            return embed

    async def MFS_embed(self, ctx, formatted_time, message_link, points):
        ticket_counter = self.user_thread[ctx.author.id][1]  # Access ticket_counter from the nested array

        embed = discord.Embed(
            title=f"Ticket #{ticket_counter}",
            description=f"{formatted_time}",
            color=discord.Color.red()
        )
        embed.add_field(name="<MFS", value=f"Used **1** point and now has **{points}** MF points.", inline=True)
        embed.add_field(name=f"{message_link}", value="", inline=False)
        embed.set_footer(text="Some Footer Text")
        return embed

    async def new_thread(self, ctx, formatted_time, message_link, thread_channel):
        message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")
        thread = await thread_channel.create_thread(
            name=f"Feedback log for {ctx.author.name}",
            message=message,
            reason="Creating a feedback log thread"
        )
        # Add the thread_id and ticket_counter (initialized to 1) to the user dict
        self.user_thread[ctx.author.id] = [thread.id, 1]  # Ticket counter initialized to 1 for new threads

    async def existing_thread(self, ctx, formatted_time, message_link, mfr_points, points):
        existing_thread_id = self.user_thread[ctx.author.id][0]
        ticket_counter = self.user_thread[ctx.author.id][1]

        try:
            existing_thread = self.bot.get_channel(existing_thread_id)
            if existing_thread is None:
                print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                return

            # increment ticket_counter
            self.user_thread[ctx.author.id][1] += 1

            if ctx.command.name == 'R':
                embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
                embed.title = f"Ticket #{ticket_counter}"
                return embed
            elif ctx.command.name == 'S':
                print("in existing thread, trying to send mfs embed")
                embed = await self.MFS_embed(ctx, formatted_time, message_link, points)
                embed.title = f"Ticket #{ticket_counter}"  # Update embed with the correct ticket_counter
                return embed
        except Exception as e:
            print(f"An error occurred while fetching/sending to the thread: {e}")
        return

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        if before.channel.id != FEEDBACK_CHANNEL_ID:
            return

        # Check if MFR before and MFS after
        ctx = await self.bot.get_context(after)

        # Check if existing thread
        if ctx.author.id in self.user_thread:
            existing_thread = self.bot.get_channel(self.user_thread[ctx.author.id][0])
            if existing_thread:
                self.user_thread[after.author.id][1] += 1
                ticket_counter = self.user_thread[after.author.id][1] # get and increment ticket counter

                # decorate doesn't allow custom parameters
                formatted_time = datetime.now().strftime("%Y-%d-%m %H:%M")
                message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"

                print("checking cog")
                # Access TimerCog to check for double points
                base_timer_cog = self.bot.get_cog("TimerCog")
                print("cog checked")

                # Check if TimerCog is available
                print(f"Base Timer Cog: {base_timer_cog}")
                if base_timer_cog is None:
                    print("BaseTimer cog not found.")
                    return

                # Check if "Double Points" is in active_timer
                if "Double Points" in base_timer_cog.timer_handler.active_timer:
                    points_deducted = 3
                    print("Double Points active, deducting 3 points.")
                else:
                    points_deducted = 2
                    print("No Double Points, deducting 2 points.")

                print("trying to deduct")
                # Deduct points
                try:
                    await db.reduce_points(str(after.author.id), points_deducted)
                except Exception as error:
                    print(f"Error reducing points: {error}")

                # Edit embed to thread
                embed = discord.Embed(
                    title=f"Ticket #{ticket_counter}",
                    description=f"{formatted_time}\nMessage edited.\n[Click to view message]({message_link})",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Before", value=before.content, inline=False)
                embed.add_field(name="After", value=after.content, inline=False)
                embed.set_footer(text="Message edited")

                await existing_thread.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))
