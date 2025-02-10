import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID
from datetime import datetime
import database.db as db
import asyncio

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

        # Check if a thread exists
        if ctx.author.id in self.user_thread:
            thread_id = self.user_thread[ctx.author.id][0]  # Get stored thread ID
            try:
                existing_thread = await self.bot.fetch_channel(thread_id)  # Fetch thread by ID
                print(f"Thread fetched successfully: {existing_thread}")

                # Ensure it's unarchived
                if existing_thread.archived:
                    print("Unarchiving thread")
                    await existing_thread.edit(archived=False)
                embed = await self.existing_thread(ctx, formatted_time, message_link, mfr_points, points)
                if embed:
                    await existing_thread.send(embed=embed)
                    await asyncio.sleep(2)
                    await existing_thread.edit(archived=True)
                return

            except discord.NotFound:
                print(f"Thread with ID {thread_id} was not found, creating a new one.")
            except discord.Forbidden:
                print(f"Bot lacks permission to access thread {thread_id}, creating a new one.")
            except discord.HTTPException as e:
                print(f"Error fetching thread: {e}, creating a new one.")

        # If no thread exists, create a new one
        print("Creating a new thread for user")
        new_thread = await self.new_thread(ctx, formatted_time, message_link, thread_channel, mfr_points, points)

        # Store the thread ID so future messages update the correct thread
        self.user_thread[ctx.author.id] = [new_thread.id, 1]  # Reset ticket counter for new thread

        await asyncio.sleep(2)
        await new_thread.edit(archived=True)

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

    import asyncio

    async def new_thread(self, ctx, formatted_time, message_link, thread_channel, mfr_points, points):
        """Creates a new thread, sends the correct embed, and archives it."""

        try:
            # Send a starter message
            message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

            # Create the thread
            thread = await thread_channel.create_thread(
                name=f"Feedback log for {ctx.author.name}",
                message=message,
                reason="Creating a feedback log thread",
                auto_archive_duration=60  # Auto-archive after 1 hour of inactivity
            )

            print(f"Thread {thread.name} created successfully.")

            # Add the thread_id and ticket_counter to the user dict
            self.user_thread[ctx.author.id] = [thread.id, 1]  # Initialize ticket counter

            # Determine the correct embed based on the command
            embed = None
            if ctx.command.name == 'R':
                embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
            elif ctx.command.name == 'S':
                embed = await self.MFS_embed(ctx, formatted_time, message_link, points)

            # Send the embed to the thread if available
            if embed:
                await thread.send(embed=embed)

            return thread  # Return the thread object for further editing

        except Exception as e:
            print(f"Error while creating thread: {e}")
            return None  # If thread creation fails, return None

    async def existing_thread(self, ctx, formatted_time, message_link, mfr_points, points):
        existing_thread_id = self.user_thread[ctx.author.id][0]

        existing_thread = self.bot.get_channel(existing_thread_id)
        if existing_thread is None:
            print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
            return

        # Check if the thread is archived
        if existing_thread.archived:
            await existing_thread.edit(archived=False)

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
        return

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        mf_variations = ["mfr", "mrf", "MFR", "MRF", "mfs", "mfs", "MFS", "MSF"]

        formatted_time = datetime.now().strftime("%Y-%d-%m %H:%M")
        message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"

        # FIRST IF - HANDLES MFR TO NOTHING
        # SECOND IF - HANDLES MFR TO MFS
        if "MFR" in before.content and "MFR" not in after.content:
            print("Detected <MFR> to nothing edit!")
            if "MFS" in after.content:
                print("Detected <MFR> to <MFS> edit!")
                await self.MFR_to_MFS_edit(before, after, formatted_time, message_link)
            else:
                await self.MFR_to_nothing(before, after, formatted_time, message_link)
            return

        # Check for MFS to MFR edit
        if "MFS" in before.content and "MFS" not in after.content:
            if "MFR" in after.content:
                print("Detected <MFS> to <MFR> edit!")
                await self.MFS_to_MFR_edit(before, after, formatted_time, message_link)
                return
            else:
                await self.MFS_to_nothing(before, after, formatted_time, message_link)

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
        # Check if existing thread exists for the user
        if after.author.id in self.user_thread:
            # Retrieve existing thread using the channel ID from the user_thread dictionary
            existing_thread = self.bot.get_channel(self.user_thread[after.author.id][0])

            # Increment the ticket counter for the user
            self.user_thread[after.author.id][1] += 1
            ticket_counter = self.user_thread[after.author.id][1]

            # Access TimerCog to check for double points
            base_timer_cog = self.bot.get_cog("TimerCog")
            if base_timer_cog is None:
                print("BaseTimer cog not found.")
                return existing_thread, ticket_counter, None

            return existing_thread, ticket_counter, base_timer_cog
        else:
            # Create a new thread for this user if no thread exists
            print("Creating new thread for user")
            return None, 1, None  # Returning None for the thread, 1 for ticket_counter, and None for TimerCog

    async def MFR_to_MFS_edit(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

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

        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await existing_thread.edit(archived=True)


    async def MFS_to_MFR_edit(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        if "MFS" in before.content and "MFR" in after.content:
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
            embed_title = "<MFS edited to <MFR"
            embed_description = f"Gained **{points_added}** points and now has **{updated_points}** MF points."

        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await existing_thread.edit(archived=True)


    async def MFR_to_nothing(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

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

        # Create the embed
        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await existing_thread.edit(archived=True)

    async def MFS_to_nothing(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        if "MFS" in before.content and "MFS" not in after.content:
            await after.channel.send("🦗")

            embed_title = "<MFS removed from message"
            embed_description = f"Not action taken"

        # Create the embed
        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                                      message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await existing_thread.edit(archived=True)




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