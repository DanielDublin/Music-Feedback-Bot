import discord
from discord.ext import commands
from data.constants import FEEDBACK_CHANNEL_ID, ADMINS_ROLE_ID, THREADS_CHANNEL
from datetime import datetime
import database.db as db
from database.feedback_threads_db import SQLiteDatabase
import asyncio
import sqlite3

class FeedbackThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sqlitedatabase = SQLiteDatabase()
        self.user_thread = {}  # Nested {user: [thread_id, ticket_counter]}

    async def initialize_sqldb(self):
        """
        Database is initialized in the __init__ method of the SQLiteDatabase class. The actual table is created in
        feedback_threads_db.py.
        If the user_thread dictionary is empty, it will check the database for existing users and populate the dictionary.
        """
        if not self.user_thread:
            self.sqlitedatabase.cursor.execute("SELECT user_id, thread_id, ticket_counter FROM users")
            data = self.sqlitedatabase.cursor.fetchall()

            if data:
                self.user_thread = {user_id: [thread_id, ticket_counter] for user_id, thread_id, ticket_counter in
                                    data}
                print("user_thread data repopulated from SQLite Database:", len(self.user_thread))
            else:
                print("No data in SQLite Database to repopulate the user_thread dictionary.")

    async def create_feedback_thread(self, ctx, mfr_points, points):
        """
        Access an existing feedback thread or create a new one for the user. If the user already has a thread, it will
        be unarchived and updated with the new message.
        If the user does not have a thread, a new one will be created and the user will be added to the database. The new
        thread will then be archived.

        :param ctx: The context of the command
        :param mfr_points: The points added/substracted based on Double Points hour
        :param points: The points associated with the user
        :return: None
        """
        await self.bot.wait_until_ready()

        thread_channel = self.bot.get_channel(THREADS_CHANNEL)
        channel_id = ctx.message.channel.id
        message_id = ctx.message.id
        guild_id = ctx.guild.id
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%d-%m %H:%M")

        # Check if a thread exists for a user
        if ctx.author.id in self.user_thread:

            thread_id = self.user_thread[ctx.author.id][0]
            existing_thread = await self.bot.fetch_channel(thread_id)

            # Need to unarchive before sending another message to the thread if it exists
            if existing_thread.archived:
                await existing_thread.edit(archived=False)

            embed = await self.existing_thread(ctx, formatted_time, message_link, mfr_points, points)

            if embed:
                await existing_thread.send(embed=embed)
                await asyncio.sleep(5)
                await existing_thread.edit(archived=True)
            return

        # If no thread exists, create a new one
        new_thread = await self.new_thread(ctx, formatted_time, message_link, thread_channel, mfr_points, points)

        await asyncio.sleep(5)
        await new_thread.edit(archived=True)

    async def update_ticket_counter(self, user_id, thread_id=None):
        """
        Update the ticket counter for a user in the database and optionally set the thread ID.
        :param user_id: The ID of the user.
        :param thread_id: (Optional) The ID of the thread to associate with the user.
        :return: The updated ticket counter.
        """

        print("in update")
        if user_id not in self.user_thread:
            self.user_thread[user_id] = [thread_id, 0]
        elif thread_id is not None:
            self.user_thread[user_id][0] = thread_id

        if self.user_thread[user_id][1] is None:
            self.user_thread[user_id][1] = 0

        self.user_thread[user_id][1] += 1
        ticket_counter = self.user_thread[user_id][1]

        self.sqlitedatabase.cursor.execute('''
            UPDATE users
            SET thread_id = ?,
                ticket_counter = ?
            WHERE user_id = ?
        ''', (self.user_thread[user_id][0], ticket_counter, user_id))

        await self.commit_changes()

        return ticket_counter

    async def add_user_to_db(self, user_id, thread_id, ticket_counter):
        """
        Check if user exists in DB, if not, add them.

        :param user_id: The ID of the user to check
        :param thread_id: The ID of the thread associated with the user
        :param ticket_counter: The ticket counter for the user
        :return: None
        """
        self.sqlitedatabase.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_check = self.sqlitedatabase.cursor.fetchone()

        if not user_check:
            self.sqlitedatabase.cursor.execute(
                "INSERT INTO users (user_id, thread_id, ticket_counter) VALUES (?, ?, ?)",
                (user_id, thread_id, ticket_counter)
            )
            await self.commit_changes()

            self.sqlitedatabase.cursor.execute("SELECT * FROM users")
            rows = self.sqlitedatabase.cursor.fetchall()
            for row in rows:
                print(row)
                break

    async def MFR_embed(self, ctx, formatted_time, message_link, mfr_points, points, ticket_counter):

        print(f"before: {self.user_thread}")
        if ctx.author.id in self.user_thread:
            print(self.user_thread[ctx.author.id])
            if self.user_thread[ctx.author.id][1] is None:
                print(self.user_thread[ctx.author.id][1])
                ticket_counter = await self.update_ticket_counter(ctx.author.id)
                print(self.user_thread[ctx.author.id][1])
            print(f"after: {self.user_thread}")

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

    async def MFS_embed(self, ctx, formatted_time, message_link, ticket_counter):

        if ticket_counter is None:
            ticket_counter = await self.update_ticket_counter(ctx.author.id)

        points = int(await db.fetch_points(str(ctx.author.id)))

        embed = discord.Embed(
            title=f"Ticket #{ticket_counter}",
            description=f"{formatted_time}",
            color=discord.Color.red()
        )

        embed.add_field(name="<MFS", value=f"Used **1** point and now has **{points}** MF points.", inline=True)

        embed.add_field(name=f"{message_link}", value="", inline=False)
        embed.set_footer(text="Some Footer Text")
        return embed

    async def new_thread(self, ctx, formatted_time, message_link, thread_channel, mfr_points=None, points=None, ticket_counter=None):
        """
        Create a new thread for a user that uses <MFR or <MFS. The user information is added to the database and dictionary.
        If the command is MFR, the MFR embed is sent to the thread. If the command is MFS, the MFS embed is sent to the thread.

        :param ctx: The context of the command
        :param formatted_time: The formatted time of the message
        :param message_link: The link to the message created for the thread to be made from
        :param thread_channel: The channel where the thread will be created
        :param mfr_points: The points added/substracted based on Double Points hour
        :param points: The points associated with the user
        :return:
        """
        message = await thread_channel.send(f"<@{ctx.author.id}> | {ctx.author.name} | {ctx.author.id}")

        try:

            thread = await thread_channel.create_thread(
                name=f"{ctx.author.name} - {ctx.author.id}",
                message=message,
                reason="Creating a feedback log thread",
                auto_archive_duration=60  # Auto-archive after 1 hour of inactivity
            )

        except Exception as e:
            print(f"Error while creating new thread: {e}")
            return None

        await self.add_user_to_db(ctx.author.id, thread.id, ticket_counter)
        self.user_thread[ctx.author.id] = [thread.id, ticket_counter]

        # Determine the correct embed based on the command
        embed = None

        if ctx.command.name == 'R':
            embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points, ticket_counter)
        elif ctx.command.name == 'S':
            if points != 0:
                embed = await self.MFS_embed(ctx, formatted_time, message_link, ticket_counter)
            else:
                pass

        if embed:
            await thread.send(embed=embed)

        return thread

    async def existing_thread(self, ctx, formatted_time, message_link, mfr_points, points):
        try:
            existing_thread_id = self.user_thread[ctx.author.id][0]
            existing_thread = self.bot.get_channel(existing_thread_id)

            if existing_thread is None:
                print(f"Thread with ID {existing_thread_id} does not exist or is not accessible.")
                return
        except KeyError:
            print(f"No thread found for user {ctx.author.id}.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        # Check if the thread is archived
        if existing_thread.archived:
            await existing_thread.edit(archived=False)

        ticket_counter = await self.update_ticket_counter(ctx.author.id)

        if ctx.command.name == 'R':
            embed = await self.MFR_embed(ctx, formatted_time, message_link, mfr_points, points, ticket_counter)
            embed.title = f"Ticket #{ticket_counter}"
            return embed
        # handles any time points arent 1 or 0 (see general MFS logic)
        elif ctx.command.name == 'S':
            points = int(await db.fetch_points(str(ctx.author.id)))
            print(f"points in S {points}")
            if points >= 1:
                ticket_counter = self.user_thread[ctx.author.id][1]
                embed = await self.MFS_embed(ctx, formatted_time, message_link, ticket_counter)
                embed.title = f"Ticket #{ticket_counter}"
                return embed

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

        # Check for nothing to MFR
        if "MFR" not in before.content.upper() and "MFR" in after.content.upper():
            await self.nothing_to_MFR(before, after, formatted_time, message_link)
            return

        # Check for nothing to MFS
        if "MFS" not in before.content.upper() and "MFS" in after.content.upper():
            print("Detected <MFS> to <MFR> edit!")
            await self.nothing_to_MFS(before, after, formatted_time, message_link)
            return

    # checks if existing thread exists
    async def check_existing_thread_edit(self, after: discord.Message):
        # Check if existing thread exists for the user
        if after.author.id in self.user_thread:

            existing_thread = await self.bot.fetch_channel(self.user_thread[after.author.id][0])

            if existing_thread.archived:
                await existing_thread.edit(archived=False)

            # Increment the ticket counter for the user
            ticket_counter = await self.update_ticket_counter(after.author.id)

            # Access TimerCog to check for double points
            base_timer_cog = self.bot.get_cog("TimerCog")
            if base_timer_cog is None:
                print("BaseTimer cog not found.")
                return existing_thread, ticket_counter, None

            return existing_thread, ticket_counter, base_timer_cog

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
                self.delete_channel_message_after_fail_edit(channel_message),
                # send deleted message to user
                general_cog.send_messages_to_user(after)
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

            embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                             message_link)

            # sends message to channel + handles deletion, sends ticket to thread
            await asyncio.gather(
                self.thread_archive(existing_thread, embed),
                self.delete_channel_message_after_fail_edit(channel_message)
            )
            await asyncio.sleep(15)
            await channel_message.delete()

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

    async def nothing_to_MFR(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

        # HANDLES MFR to NOTHING (Deduct points)
        if "MFR" in after.content.upper() and "MFR" not in before.content.upper():
            print("entering MFR added")
            if "Double Points" in base_timer_cog.timer_handler.active_timer:
                points_added = 2
            else:
                points_added = 1

            # Deduct points
            await db.add_points(str(after.author.id), points_added)

            # Update points after deduction
            updated_points = await db.fetch_points(str(after.author.id))

            embed_title = "<MFR added to message"
            embed_description = f"Gained **{points_added}** points and now has **{updated_points}** MF points."

        # Create the embed
        embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
                                      message_link)
        if existing_thread.archived:
            await existing_thread.edit(archived=False)
        await existing_thread.send(embed=embed)
        await asyncio.sleep(5)
        await existing_thread.edit(archived=True)

        channel_message = await after.channel.send(
            f"{after.author.mention} added <MFR to their message and gained **{points_added}** MF Points. You now have **{updated_points}** MF Points."
            f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")
        await asyncio.sleep(15)
        await channel_message.delete()

    async def nothing_to_MFS(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
        # Get the existing thread and ticket_counter
        print("nothing to MFS")
        if after.author.id in self.user_thread:
            existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)
        else:
            new_thread = await self.check_existing_thread_edit(after, formatted_time, message_link,
                                                                               after.channel)
            existing_thread = new_thread

        base_timer_cog = self.bot.get_cog("TimerCog")
        general_cog = self.bot.get_cog("General")
        if base_timer_cog is None:
            print("BaseTimer cog not found.")
            return

        if general_cog is None:
            print("General cog not found.")
            return

        # HANDLES NOTHING TO MFS (Deduct points)
        if "MFS" in after.content.upper() and "MFS" not in before.content.upper():
            print("entering MFS added")
            points_deducted = 1

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

                # thread
                embed_title = "<MFS added to message with no points"
                embed_description = f"Not enough available points to use **{points_deducted}** MF points, and now has **{updated_points}** MF points."
                embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after,
                                              ticket_counter,
                                              message_link)

                # send message to user
                channel_message = await after.channel.send(
                    f"{after.author.mention} edited their message to include <MFS but didn't have enough MF Points. You now have **{updated_points}** MF Points."
                    f"\n\nYour submission has been DMed to you. For more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

            # if edit doesn't cause <0 points
            else:
                # thread
                embed_title = "<MFS added to message"
                embed_description = f"Used **{points_deducted}** points and now has **{updated_points}** MF points."
                embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after,
                                              ticket_counter,
                                              message_link)

                # send message to user
                channel_message = await after.channel.send(
                    f"{after.author.mention} edited their message to include <MFS and used **{points_deducted}** MF Points. You now have **{updated_points}** MF Points."
                    f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

            # sends message to channel + handles deletion, sends ticket to thread
            await asyncio.gather(
                self.thread_archive(existing_thread, embed),
                self.delete_channel_message_after_fail_edit(channel_message),
                # send deleted message to user
                general_cog.send_messages_to_user(after)
            )

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



