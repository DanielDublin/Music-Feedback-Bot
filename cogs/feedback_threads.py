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

        ticket_counter = self.user_thread[ctx.author.id][1]

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
        ticket_counter = self.user_thread[ctx.author.id][1]

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

        try:
            existing_thread = self.bot.get_channel(existing_thread_id)
            if existing_thread is None:
                print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                return

            self.user_thread[ctx.author.id][1] += 1
            ticket_counter = self.user_thread[ctx.author.id][1]

            if ctx.command.name == 'R':
                embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
                embed.title = f"Ticket #{ticket_counter}"
                return embed
            elif ctx.command.name == 'S':
                embed = await self.MFS_embed(ctx, formatted_time, message_link, points)
                embed.title = f"Ticket #{ticket_counter}"  # Update embed with the correct ticket_counter
                return embed
        except Exception as e:
            print(f"An error occurred while fetching/sending to the thread: {e}")
        return

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        mf_variations = ["mfr", "mrf", "MFR", "MRF", "mfs", "mfs", "MFS", "MSF"]

        formatted_time = datetime.now().strftime("%Y-%d-%m %H:%M")
        message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"

        # FIRST IF - HANDLES MFR TO NOTHING
        # SECOND IF - HANDLES MFR TO MFS
        if "MFR" in before.content and "MFR" not in after.content:
            if "MFS" in after.content:
                print("Detected <MFR> to nothing edit!")
                await self.MFR_to_MFS_edit(before, after, formatted_time, message_link)
            else:
                await self.MF_to_nothing(before, after, formatted_time, message_link)
                return


        # # HANDLES MFR TO MFS EDIT
        # # # commandprefix.lower() == "mfr"
        # if any(variation in before.content.lower() for variation in mf_variations):
        #
        #     print("Detected <MFR> to <MFS> edit!")
        #     formatted_time = datetime.now().strftime("%Y-%d-%m %H:%M")
        #     message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"
        #
        #     await self.MFR_to_MFS_edit(before, after, formatted_time, message_link)
        #     return

        # if "MFS" in before.content and "MFR" in after.content:
        #
        # if MFS OR MFR in content and deleted:
        #
        # if mfs or mfr not in content and added in:

        # HANDLE LOGIC FOR IF 0 POINTS

    # checks if existing thread exists
    async def check_existing_thread_edit(self, after: discord.Message):
        # Check if existing thread
        if after.author.id in self.user_thread:
            existing_thread = self.bot.get_channel(self.user_thread[after.author.id][0])
            return existing_thread
        # add logic for new thread?
        elif after.author.id not in self.user_thread:
            print("creating thread")

        return None, 1

    async def MFR_to_MFS_edit(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread = await self.check_existing_thread_edit(after)
        self.user_thread[after.author.id][1] += 1
        ticket_counter = self.user_thread[after.author.id][1]

        # Access TimerCog to check for double points
        base_timer_cog = self.bot.get_cog("TimerCog")
        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return

        # HANDLES MFR TO MFS EDIT (Deduct points)
        if "MFR" in before.content and "MFS" in after.content:
            print("entering MFR")
            if "Double Points" in base_timer_cog.timer_handler.active_timer:
                points_deducted = 3
            else:
                points_deducted = 2

            # Deduct points
            await db.reduce_points(str(after.author.id), points_deducted)

            # Update points after deduction
            updated_points = await db.fetch_points(str(after.author.id))

            embed_title = "<MFR edited to <MFS"
            embed_description = f"Used **{points_deducted}** points and now has **{updated_points}** MF points."

        # HANDLES MFS TO MFR EDIT (Add points)
        elif "MFS" in before.content and "MFR" in after.content:
            print("Processing MFS to MFR edit: Adding points.")
            if "Double Points" in base_timer_cog.timer_handler.active_timer:
                points_added = 3
            else:
                points_added = 2

            # Add points
            await db.add_points(str(after.author.id), points_added)

            # Update points after addition
            updated_points = await db.fetch_points(str(after.author.id))

            # Create the embed
            embed_title = "<MFR edited to <MFS>"
            embed_description = f"Used **{points_added}** points and now has **{updated_points}** MF points."

        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        await existing_thread.send(embed=embed)

    async def MF_to_nothing(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread = await self.check_existing_thread_edit(after)
        self.user_thread[after.author.id][1] += 1
        ticket_counter = self.user_thread[after.author.id][1]

        # Access TimerCog to check for double points
        base_timer_cog = self.bot.get_cog("TimerCog")
        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return

        # HANDLES MFR to NOTHING (Deduct points)
        if "MFR" in before.content and "MFR" not in after.content:
            print("entering MFR deleted")
            if "Double Points" in base_timer_cog.timer_handler.active_timer:
                points_deducted = 3
            else:
                points_deducted = 2

            # Deduct points
            await db.reduce_points(str(after.author.id), points_deducted)

            # Update points after deduction
            updated_points = await db.fetch_points(str(after.author.id))

            embed_title = "<MFR removed from message"
            embed_description = f"Used **{points_deducted}** points and now has **{updated_points}** MF points."


        # HANDLES MFS TO MFR EDIT (Add points)
        # elif "MFS" in before.content and "MFR" in after.content:
        #     print("Processing MFS to MFR edit: Adding points.")
        #     if "Double Points" in base_timer_cog.timer_handler.active_timer:
        #         points_added = 3
        #     else:
        #         points_added = 2
        #
        #     # Add points
        #     await db.add_points(str(after.author.id), points_added)
        #
        #     # Update points after addition
        #     updated_points = await db.fetch_points(str(after.author.id))
        #
        #     embed_description = f"Gained **{points_added}** points and now has **{updated_points}** MF points."
        #     embed_title = "<MFS edited to <MFR"

        # Create the embed
        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        await existing_thread.send(embed=embed)

    # embed when edits made
    async def edit_embed(self, embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link):
        embed = discord.Embed(
            title=f"Ticket #{ticket_counter}",
            description=f"{formatted_time}",
            color=discord.Color.yellow()
        )
        embed.add_field(name=embed_title, value=embed_description, inline=True)
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        embed.add_field(name="Message Link", value=message_link, inline=False)
        embed.set_footer(text="Some Footer Text")
        return embed


async def setup(bot):
    await bot.add_cog(FeedbackThreads(bot))


#         """
#         Handle misspellings, capitalizations, switches, additions.
#         ------was working on getting the ticket to send - the points deduct well
#         add message in feedback channel that lets member know of points change on edit
#         include excerpt of before and after
#           fix that each edit causes the ticket counter to increase no matter if its mfr or not
#         """