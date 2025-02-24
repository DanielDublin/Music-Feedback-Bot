import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL
from datetime import datetime
import database.db as db
from database.feedback_threads_db import SQLiteDatabase
import asyncio

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlitedatabase = SQLiteDatabase()
        self.user_thread = {}  # Nested {user: [thread_id, ticket_counter]}

    async def initialize_sqldb(self):
        # check if dict is empty
        # if it is, need to check if there are entries in db (if not, then the bot is entirely new)
        # this only runs if a command is user -- maybe it call on bot restart?
        if not self.user_thread:
            # select all data in the db (0 if there is none)
            self.sqlitedatabase.cursor.execute("SELECT user_id, thread_id, ticket_counter FROM users")
            data = self.sqlitedatabase.cursor.fetchall()
            print("Trying to repopulate user thread data...")

            # if data is in db, repopulate the dict
            # data returns as tuple (user id, thread id, ticket counter)
            if data:
                self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in
                                    data}
                print("Threads repopulated from db:", self.user_thread)
            else:
                print("No data in SQLite Database")


    async def create_feedback_thread(self, ctx, mfr_points, points):

        await self.bot.wait_until_ready()


        thread_channel = self.bot.get_channel(THREADS_CHANNEL)
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%d-%m %H:%M")

        # Check if a thread exists
        if ctx.author.id in self.user_thread:
            print(f"existing:{self.user_thread}")
            thread_id = self.user_thread[ctx.author.id][0]  # get stored thread ID
            existing_thread = await self.bot.fetch_channel(thread_id)  # fetch thread by ID

            # UNARCHIVE BEFORE SENDING ANOTHER MESSAGE TO THREAD
            if existing_thread.archived:
                await existing_thread.edit(archived=False)
                # call existing thread logic
            embed = await self.existing_thread(ctx, formatted_time, message_link, mfr_points, points)
            if embed:
                await existing_thread.send(embed=embed)
                await asyncio.sleep(5)
                await existing_thread.edit(archived=True)
            return

        # If no thread exists, create a new one
        new_thread = await self.new_thread(ctx, formatted_time, message_link, thread_channel, mfr_points, points)

        # Store the thread ID so future messages update the correct thread
        self.user_thread[ctx.author.id] = [new_thread.id, 1]  # Reset ticket counter for new thread

        await asyncio.sleep(5)
        await new_thread.edit(archived=True)

    async def MFR_embed(self, ctx, formatted_time, message_link, mfr_points, points):
        print("IN MFR_EMBED")

        ticket_counter = self.user_thread[ctx.author.id][1]

        # MFR points logic for double points
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

    async def MFS_embed(self, ctx, formatted_time, message_link):
        print("INT MFS")
        points = int(await db.fetch_points(str(ctx.author.id)))
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

    async def new_thread(self, ctx, formatted_time, message_link, thread_channel, mfr_points=None, points=None):

        try:
            # Send a starter message
            message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

            # Create the thread
            thread = await thread_channel.create_thread(
                name=f"{ctx.author.name} - {ctx.author.id}",
                message=message,
                reason="Creating a feedback log thread",
                auto_archive_duration=60  # Auto-archive after 1 hour of inactivity
            )

            # Add the thread_id and ticket_counter to the user dict
            self.user_thread[ctx.author.id] = [thread.id, 1]  # Initialize ticket counter

            # add member to db
            self.sqlitedatabase.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (ctx.message.author.id,))

            user_check = self.sqlitedatabase.cursor.fetchone()

            if not user_check:
                self.sqlitedatabase.cursor.execute(
                    "INSERT INTO users (user_id, thread_id, ticket_counter) VALUES (?, ?, ?)",
                    (ctx.author.id, thread.id, self.user_thread[ctx.author.id][1])
                )

                # Commit the transaction to save the changes
                await self.commit_changes()

                # Retrieve and print the data from the users table
                self.sqlitedatabase.cursor.execute("SELECT * FROM users")
                rows = self.sqlitedatabase.cursor.fetchall()

                # Print the rows
                for row in rows:
                    print(row)
                    break

            # Determine the correct embed based on the command
            embed = None

            if ctx.command.name == 'R':
                embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
            elif ctx.command.name == 'S':
                print(f"points in S {points}")
                if points > 1:
                    embed = await self.MFS_embed(ctx, formatted_time, message_link)

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

        # update ticket number in db
        self.sqlitedatabase.cursor.execute('''
            UPDATE users 
            SET ticket_counter = ? 
            WHERE user_id = ?
        ''', (ticket_counter, ctx.author.id))

        await self.commit_changes()

        if ctx.command.name == 'R':
            embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points)
            embed.title = f"Ticket #{ticket_counter}"
            return embed
        # handles any time points arent 1 or 0 (see general MFS logic)
        elif ctx.command.name == 'S':
            points = int(await db.fetch_points(str(ctx.author.id)))
            print(f"points in S {points}")
            if points >= 1:
                print("sending MFS points even though 0")
                embed = await self.MFS_embed(ctx, formatted_time, message_link)
                embed.title = f"Ticket #{ticket_counter}"
                return embed

        # Check if points are greater than 0 for 'S' command
        # elif ctx.command.name == 'S' and current_points > 0:
        #     print(current_points)
        #     print("entering mfs")
        #     embed = await self.MFS_embed(ctx, formatted_time, message_link, points)
        #     print("embed sent")
        #     embed.title = f"Ticket #{ticket_counter}"
        #     return embed

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        mf_variations = ["mfr", "mrf", "MFR", "MRF", "mfs", "mfs", "MFS", "MSF"]

        formatted_time = datetime.now().strftime("%Y-%d-%m %H:%M")
        message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"

        # FIRST IF - HANDLES MFR TO NOTHING
        # SECOND IF - HANDLES MFR TO MFS
        if "MFR" in before.content.upper() and "MFR" not in after.content.upper():
            print("Detected <MFR> to nothing edit!")
            if "MFS" in after.content.upper():
                print("Detected <MFR> to <MFS> edit!")
                await self.MFR_to_MFS_edit(before, after, formatted_time, message_link)
            else:
                await self.MFR_to_nothing(before, after, formatted_time, message_link)
            return

        # Check for MFS to MFR edit
        if "MFS" in before.content.upper() and "MFS" not in after.content.upper():
            if "MFR" in after.content.upper():
                print("Detected <MFS> to <MFR> edit!")
                await self.MFS_to_MFR_edit(before, after, formatted_time, message_link)
                return
            else:
                await self.MFS_to_nothing(before, after, formatted_time, message_link)

    # checks if existing thread exists
    async def check_existing_thread_edit(self, after: discord.Message):
        # Check if existing thread exists for the user
        if after.author.id in self.user_thread:

            existing_thread = await self.bot.fetch_channel(self.user_thread[after.author.id][0])

            if existing_thread.archived:
                await existing_thread.edit(archived=False)

            # Increment the ticket counter for the user
            self.user_thread[after.author.id][1] += 1
            ticket_counter = self.user_thread[after.author.id][1]
            # update ticket count in db
            self.sqlitedatabase.cursor.execute('''
                UPDATE users 
                SET ticket_counter = ? 
                WHERE user_id = ?
            ''', (ticket_counter, after.author.id))

            await self.commit_changes()

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
        general_cog = self.bot.get_cog("General")
        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return

        if general_cog is None:
            print("General cog not found.")
            return

        # HANDLES MFR TO MFS EDIT (Deduct points)
        if "MFR" in before.content.upper() and "MFS" in after.content.upper():
            print("entering MFR")
            if "Double Points" in base_timer_cog.timer_handler.active_timer:
                points_deducted = 3
            else:
                points_deducted = 2

            # avoid negative points
            updated_points = await db.fetch_points(str(after.author.id))

            # Deduct points
            await db.reduce_points(str(after.author.id), points_deducted)

            # Update points after deduction
            updated_points = await db.fetch_points(str(after.author.id))
            if updated_points < 0:
                await db.reset_points(str(after.author.id))
                updated_points = 0

                # delete member message (submission)
                await after.delete()
                # tag admins in thread
                await existing_thread.send(f"<@&{ADMINS_ROLE_ID}>")
                # send deleted message to user
                await general_cog.send_messages_to_user(after)

                # thread
                embed_title = "<MFR edited to <MFS with no points"
                embed_description = f"Not enough available points to use **{points_deducted}** MF points, and now has **{updated_points}** MF points."
                embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after,
                                              ticket_counter,
                                              message_link)

                # send message to user
                channel_message = await after.channel.send(
                    f"{after.author.mention} edited their message from <MFR to <MFS but didn't have enough MF Points. You now have **{updated_points}** MF Points."
                    f"\n\nYour submission has been DMed to you. For more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

            # if edit doesn't cause <0 points
            else:
                # thread
                embed_title = "<MFR edited to <MFS"
                embed_description = f"Used **{points_deducted}** points and now has **{updated_points}** MF points."
                embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after,
                                              ticket_counter,
                                              message_link)

                # send message to user
                channel_message = await after.channel.send(
                    f"{after.author.mention} edited their message from <MFR to <MFS and used **{points_deducted}** MF Points. You now have **{updated_points}** MF Points."
                    f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

            # sends message to channel + handles deletion, sends ticket to thread
            await asyncio.gather(
                self.thread_archive(existing_thread, embed),
                self.delete_channel_message_after_fail_edit(channel_message)
            )

    async def MFS_to_MFR_edit(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        if "MFS" in before.content.upper() and "MFR" in after.content.upper():
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

        # send information to user
        channel_message = await after.channel.send(
            f"{after.author.mention} edited their message from <MFS to <MFR and gained **{points_added}** MF Points. You now have **{updated_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")
        await asyncio.sleep(15)
        await channel_message.delete()

        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                         message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await asyncio.sleep(5)
        await existing_thread.edit(archived=True)


    async def MFR_to_nothing(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        # HANDLES MFR to NOTHING (Deduct points)
        if "MFR" in before.content.upper() and "MFR" not in after.content.upper():
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
        await asyncio.sleep(5)
        await existing_thread.edit(archived=True)

        channel_message = await after.channel.send(
            f"{after.author.mention} removed <MFR from their message and lost **{points_deducted}** MF Points. You now have **{updated_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")
        await asyncio.sleep(15)
        await channel_message.delete()

    async def MFS_to_nothing(self, before: discord.Message, after: discord.Message, formatted_time, message_link):

        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        print("shortening")
        try:
            before_content_truncated, after_content_truncated = await self.shorten_before_and_after_messages(before, after)
            print("SUCCESS")
        except Exception as e:
            print(f"Error during shortening: {e}")
            return

        if "MFS" in before_content_truncated and "MFS" not in after_content_truncated:
            points = await db.fetch_points(str(after.author.id))
            print("trying to send ")
            embed_title = "<MFS removed from message"
            embed_description = f"No action taken. Member still lost a point and has **{points}** MF points."


        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before_content_truncated,
                                      after_content_truncated, ticket_counter, message_link)

        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await asyncio.sleep(5)
        await existing_thread.edit(archived=True)

        channel_message = await after.channel.send(
            f"🦗 {after.author.mention} removed <MFS from their post. No points were awarded back."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>."
        )

        await asyncio.sleep(15)
        await channel_message.delete()

    # embed when edits made
    async def edit_embed(self, embed_title, formatted_time, embed_description, before_content_truncated, after_content_truncated, ticket_counter,
                         message_link):
        before_content_truncated, after_content_truncated = await self.shorten_before_and_after_messages(before_content_truncated, after_content_truncated)

        embed = discord.Embed(
            title=f"Ticket #{ticket_counter}",
            description=f"{formatted_time}",
            color=discord.Color.yellow()
        )
        embed.add_field(name=embed_title, value=embed_description, inline=True)
        embed.add_field(name="Before", value=before_content_truncated, inline=False)
        embed.add_field(name="After", value=after_content_truncated, inline=False)
        embed.add_field(name="Message Link", value=message_link, inline=False)
        embed.set_footer(text="Some Footer Text")
        return embed

    # handles if <MFS is used and user has no points - sends embed to thread or makes
    async def handle_zero_points(self, ctx, formatted_time):
        ticket_counter = self.user_thread[ctx.author.id][1]

        # Create the embed
        embed = discord.Embed(
            title=f"Ticket #{ticket_counter}",
            description=f"{formatted_time}",
            color=discord.Color.yellow()
        )
        embed.add_field(name="<MFS", value=f"Used <MFS with no points available", inline=True)
        embed.set_footer(text="Some Footer Text")

        return embed

    async def shorten_before_and_after_messages(self, before, after):
        print("entering shorten)")
        max_length = 500
        if len(before.content) > max_length:
            before_content_truncated = before.content[:max_length] + "..."
        else:
            before_content_truncated = before.content

        if len(after.content) > max_length:
            after_content_truncated = after.content[:max_length] + "..."
        else:
            after_content_truncated = after.content

        print(f"Truncated before message: {before_content_truncated}")
        print(f"Truncated after message: {after_content_truncated}")

        return before_content_truncated, after_content_truncated

    async def commit_changes(self):
        try:
            self.sqlitedatabase.connection.commit()
        except Exception as e:
            print(f"Database commit error: {e}")

    # used to call the dictionary in general cog
    async def get_user_thread(self, user_id):
        if user_id in self.user_thread:
            return self.user_thread[user_id]
        else:
            return None

    async def thread_archive(self, existing_thread, embed):
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await asyncio.sleep(5)
        await existing_thread.edit(archived=True)

    async def delete_channel_message_after_fail_edit(self, channel_message):
        await asyncio.sleep(15)
        await channel_message.delete()



async def setup(bot):
    # Create an instance of FeedbackThreads and initialize the database
    feedback_cog = FeedbackThreads(bot)
    await feedback_cog.initialize_sqldb()  # Initialize DB
    await bot.add_cog(feedback_cog)  # Add the cog to the bot



#         """
#         Handle misspellings, capitalizations, switches, additions.
#         ------was working on getting the ticket to send - the points deduct well
#         add message in feedback channel that lets member know of points change on edit
#         include excerpt of before and after
#           fix that each edit causes the ticket counter to increase no matter if its mfr or not
#         """

"""
fix MFS to MFR
handle trying to remove points when points = 0
handle points going to negative


ticket counter +2 increased when
<MFR to <MF
to <MFR to <MFS
triggering 399 if "MFR" in before.content and "MFR" not in after.content:

edit message is delayed - should be sent before the ticket is 

need to delete the post when "not allowed"


breaks with <mfr edited to <mfs to deleting <mfs

somehow negative points when i lose points due to edit
"""