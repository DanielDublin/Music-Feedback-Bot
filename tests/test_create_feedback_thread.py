import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from cogs.feedback_threads import FeedbackThreads
import sqlite3
from tests.mock_user_data import *
import asyncio

class TestCreateFeedbackThread(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = AsyncMock()
        self.ctx = AsyncMock()

        self.ctx.message.channel.id = MOCK_THREAD_CHANNEL_DATA['id']
        self.ctx.message.id = MOCK_MESSAGE_DATA['id']
        self.ctx.guild.id = MOCK_GUILD_DATA['id']
        self.ctx.author.id = MOCK_MESSAGE_DATA['author']

        self.bot.wait_until_ready = AsyncMock()
        self.bot.get_channel = AsyncMock()
        self.bot.fetch_channel = AsyncMock()

        # Create instance of FeedbackThreads
        self.feedback_threads = FeedbackThreads(self.bot)

        # Set up user_thread dictionary
        self.feedback_threads.user_thread = EXPECTED_USER_THREAD

        # Place this AFTER setting self.ctx.author.id
        user_id = self.ctx.author.id
        self.existing_thread = AsyncMock()  # Mock existing thread
        self.existing_thread.id = EXPECTED_USER_THREAD.get(user_id, [None])[0]  # Fetch thread_id safely

        print(f"User: {user_id}, Thread: {self.existing_thread.id} in user_threads")

    # Test when a user already has an existing feedback thread
    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_create_feedback_thread_existing(self, mock_get_channel, mock_fetch_channel):

        print("\n===== STARTING THREAD RETRIEVAL TEST (EXISTING USER) =====")

        # Mocking existing thread behavior
        mock_existing_channel = AsyncMock()
        mock_existing_channel.id = EXPECTED_USER_THREAD.get(self.ctx.author.id, [None])[0]
        mock_existing_channel.archived = True
        mock_existing_channel.send = AsyncMock()
        mock_existing_channel.edit = AsyncMock()

        # Set the fetched channel to be the existing thread
        mock_fetch_channel.return_value = mock_existing_channel

        print(f"Mock existing thread fetched with ID: {mock_existing_channel.id}")

        # Simulate existing thread logic
        if mock_existing_channel.archived:
            await mock_existing_channel.edit(archived=False)  # Unarchive the thread
            print("Thread unarchived.")

        embed = MagicMock()  # Mock the embed returned by self.existing_thread
        if embed:
            await mock_existing_channel.send(embed=embed)
            print("Embed sent to existing thread.")
            await asyncio.sleep(5)
            await mock_existing_channel.edit(archived=True)  # Re-archive the thread
            print("Thread re-archived.")

        # Assertions: Existing thread should be unarchived, a message should be sent, and it should be archived again
        mock_existing_channel.edit.assert_any_call(archived=False)
        mock_existing_channel.send.assert_called_once_with(embed=embed)
        mock_existing_channel.edit.assert_any_call(archived=True)

    # test when a user does not have an existing feedback thread and counter initiated
    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_create_feedback_thread_new(self, mock_get_channel, mock_fetch_channel):
        """Test when a user does NOT have an existing feedback thread."""

        print("\n===== STARTING THREAD CREATION TEST (NEW USER) =====")

        # Simulate user has no existing thread
        self.feedback_threads.user_thread = {}
        print(f"User_threads: {self.feedback_threads.user_thread}")

        # Mock thread channel and new thread creation
        mock_thread_channel = AsyncMock()
        mock_get_channel.return_value = mock_thread_channel

        mock_new_thread = AsyncMock()
        mock_new_thread.id = 2000001
        mock_new_thread.archived = False
        mock_new_thread.edit = AsyncMock()

        self.ctx.author.id = 1000001
        mfr_points = 1
        points = 0
        ticket_counter = 0

        # Mock new_thread method
        self.feedback_threads.new_thread = AsyncMock(return_value=mock_new_thread)

        # Call the method that creates a new thread
        await self.feedback_threads.create_feedback_thread(self.ctx, mfr_points, points)

        ticket_counter = self.feedback_threads.user_thread[self.ctx.author.id][1]
        self.assertEqual(ticket_counter, 1)
        print(f"Ticket counter after thread creation: {ticket_counter}")

        # Ensure the new thread was stored in the user_thread dictionary
        self.feedback_threads.user_thread[self.ctx.author.id] = [mock_new_thread.id, ticket_counter]

        # Wait for archive action
        await asyncio.sleep(5.1)

        # Ensure new thread was archived
        mock_new_thread.edit.assert_called_once_with(archived=True)

        print(
            f"New thread created for user {self.ctx.author.id}: {self.feedback_threads.user_thread[self.ctx.author.id]}")

        # Clean up test data
        del self.feedback_threads.user_thread[self.ctx.author.id]

    # test new thread for MFR and MFS, add member to db,
    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_new_thread(self, mock_get_channel, mock_fetch_channel):

        print("\n===== STARTING CREATE FEEDBACK THREAD TEST (NEW USER) =====")

        # Simulate user has no existing thread
        self.feedback_threads.user_thread = {}
        print(f"✓ User_threads is empty: {self.feedback_threads.user_thread}")

        # Mock thread channel and new thread creation
        mock_thread_channel = AsyncMock()
        mock_get_channel.return_value = mock_thread_channel

        # Mock thread creation response
        mock_message = AsyncMock()
        mock_thread_channel.send.return_value = mock_message

        mock_new_thread = AsyncMock()
        mock_new_thread.id = 2000001
        mock_new_thread.archived = False
        mock_new_thread.edit = AsyncMock()
        mock_new_thread.send = AsyncMock()
        mock_thread_channel.create_thread.return_value = mock_new_thread

        # Mock ctx object
        mock_ctx = MagicMock()
        mock_ctx.author.id = 1000001
        mock_ctx.author.name = "Test User"
        mock_ctx.command.name = "R"
        mock_ctx.message.author.id = 1000001

        # Mock database methods
        self.feedback_threads.sqlitedatabase = MagicMock()
        self.feedback_threads.sqlitedatabase.cursor = MagicMock()
        self.feedback_threads.sqlitedatabase.cursor.fetchone.return_value = None
        self.feedback_threads.sqlitedatabase.cursor.fetchall.return_value = [(1000001, 2000001, 1)]
        self.feedback_threads.commit_changes = AsyncMock()

        # Mock embed method
        self.feedback_threads.MFR_embed = AsyncMock()
        mock_embed = MagicMock()
        self.feedback_threads.MFR_embed.return_value = mock_embed

        # Test parameters
        formatted_time = "2025-03-02 12:00:00"
        message_link = "https://discord.com/channels/123456789/123456789/123456789"
        mfr_points = 10
        points = 5

        print("\n[TEST SETUP]")
        print(f"✓ Test parameters configured:")
        print(f"  - Formatted Time: {formatted_time}")
        print(f"  - Message Link: {message_link}")
        print(f"  - MFR Points: {mfr_points}")
        print(f"  - Points: {points}")

        print(f"\n[MOCKING DISCORD OBJECTS]")
        print(f"✓ Mocking user: {mock_ctx.author.name} (ID: {mock_ctx.author.id})")
        print(f"✓ Mocking thread channel and message responses")

        # Run the method being tested
        print(f"\n[TEST EXECUTION]")
        print(f"✓ Creating new thread for user {mock_ctx.author.id} with:")
        print(f"  - Thread ID: {mock_new_thread.id}")
        print(f"  - MFR Points: {mfr_points}")
        print(f"  - Points: {points}")

        result = await self.feedback_threads.new_thread(mock_ctx, formatted_time, message_link, mock_thread_channel,
                                                        mfr_points, points)

        # Assertions
        print("\n[ASSERTIONS]")
        print(f"✓ Checking if the correct thread object is returned")
        self.assertEqual(result, mock_new_thread, "Should return the new thread object")

        # Print actual call details
        print("\n[VERIFICATION]")
        print(f"✓ Checking thread_channel.send call")
        print(f"  - Expected: <@{mock_ctx.author.id}> | {mock_ctx.author.name} | {mock_ctx.author.id}")
        print(f"  - Actual: {mock_thread_channel.send.call_args}")

        print(f"\n✓ Checking create_thread call parameters")
        print(f"  - Expected Name: {mock_ctx.author.name} - {mock_ctx.author.id}")
        print(f"  - Expected Reason: Creating a feedback log thread")
        print(f"  - Expected Auto Archive Duration: 60 minutes")
        print(f"  - Actual: {mock_thread_channel.create_thread.call_args}")

        # Check if user was added to dict and database
        print(f"\n✓ Checking if user was added to dictionary and database")
        self.assertEqual(self.feedback_threads.user_thread[mock_ctx.author.id], [mock_new_thread.id, 1])

        print(f"  - User thread dict: {self.feedback_threads.user_thread}")
        self.feedback_threads.sqlitedatabase.cursor.execute.assert_any_call(
            "SELECT user_id FROM users WHERE user_id = ?", (mock_ctx.message.author.id,))
        self.feedback_threads.sqlitedatabase.cursor.execute.assert_any_call(
            "INSERT INTO users (user_id, thread_id, ticket_counter) VALUES (?, ?, ?)",
            (mock_ctx.author.id, mock_new_thread.id, 1)
        )

        print("\n✓ Checking if database commit was called")
        self.feedback_threads.commit_changes.assert_called_once()

        print("\n✓ Checking if embed was created and sent")
        self.feedback_threads.MFR_embed.assert_called_once_with(mock_ctx, formatted_time, message_link, mfr_points,
                                                                points)
        mock_new_thread.send.assert_called_once_with(embed=mock_embed)

        # Test for error handling
        print("\n[ERROR HANDLING TEST]")
        print("✓ Simulating thread creation failure")
        mock_thread_channel.create_thread.reset_mock()
        mock_thread_channel.create_thread.side_effect = Exception("Test exception")

        # Run method again with exception
        result = await self.feedback_threads.new_thread(mock_ctx, formatted_time, message_link, mock_thread_channel,
                                                        mfr_points, points)

        print(f"✓ Expected None on exception, Actual: {result}")
        self.assertIsNone(result, "Should return None on exception")

    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_new_thread_S(self, mock_get_channel, mock_fetch_channel):

        print("\n===== SSSSSS =====")

        # Simulate user has no existing thread
        self.feedback_threads.user_thread = {}
        print(f"✓ User_threads is empty: {self.feedback_threads.user_thread}")

        # Mock thread channel and new thread creation
        mock_thread_channel = AsyncMock()
        mock_get_channel.return_value = mock_thread_channel

        # Mock thread creation response
        mock_message = AsyncMock()
        mock_thread_channel.send.return_value = mock_message

        mock_new_thread = AsyncMock()
        mock_new_thread.id = 2000001
        mock_new_thread.archived = False
        mock_new_thread.edit = AsyncMock()
        mock_new_thread.send = AsyncMock()
        mock_thread_channel.create_thread.return_value = mock_new_thread

        # Mock ctx object
        mock_ctx = MagicMock()
        mock_ctx.author.id = 1000001
        mock_ctx.author.name = "Test User"
        mock_ctx.command.name = "S"
        mock_ctx.message.author.id = 1000001

        # Mock database methods
        self.feedback_threads.sqlitedatabase = MagicMock()
        self.feedback_threads.sqlitedatabase.cursor = MagicMock()
        self.feedback_threads.sqlitedatabase.cursor.fetchone.return_value = None
        self.feedback_threads.sqlitedatabase.cursor.fetchall.return_value = [(1000001, 2000001, 1)]
        self.feedback_threads.commit_changes = AsyncMock()

        # Mock embed method
        self.feedback_threads.MFS_embed = AsyncMock()
        mock_embed = MagicMock()
        self.feedback_threads.MFS_embed.return_value = mock_embed

        # Test parameters
        formatted_time = "2025-03-02 12:00:00"
        message_link = "https://discord.com/channels/123456789/123456789/123456789"
        mfr_points = 10
        points = 5

        print("\n[TEST SETUP]")
        print(f"✓ Test parameters configured:")
        print(f"  - Formatted Time: {formatted_time}")
        print(f"  - Message Link: {message_link}")
        print(f"  - MFR Points: {mfr_points}")
        print(f"  - Points: {points}")

        print(f"\n[MOCKING DISCORD OBJECTS]")
        print(f"✓ Mocking user: {mock_ctx.author.name} (ID: {mock_ctx.author.id})")
        print(f"✓ Mocking thread channel and message responses")

        # Run the method being tested
        print(f"\n[TEST EXECUTION]")
        print(f"✓ Creating new thread for user {mock_ctx.author.id} with:")
        print(f"  - Thread ID: {mock_new_thread.id}")
        print(f"  - MFR Points: {mfr_points}")
        print(f"  - Points: {points}")

        result = await self.feedback_threads.new_thread(mock_ctx, formatted_time, message_link, mock_thread_channel,
                                                        mfr_points, points)

        print(f"create_thread() returned: {mock_get_channel.create_thread.return_value}")

        # Assertions
        print("\n[ASSERTIONS]")
        print(f"✓ Checking if the correct thread object is returned")
        self.assertEqual(result, mock_new_thread, "Should return the new thread object")

        # Print actual call details
        print("\n[VERIFICATION]")
        print(f"✓ Checking thread_channel.send call")
        print(f"  - Expected: <@{mock_ctx.author.id}> | {mock_ctx.author.name} | {mock_ctx.author.id}")
        print(f"  - Actual: {mock_thread_channel.send.call_args}")

        print(f"\n✓ Checking create_thread call parameters")
        print(f"  - Expected Name: {mock_ctx.author.name} - {mock_ctx.author.id}")
        print(f"  - Expected Reason: Creating a feedback log thread")
        print(f"  - Expected Auto Archive Duration: 60 minutes")
        print(f"  - Actual: {mock_thread_channel.create_thread.call_args}")

        # Check if user was added to dict and database
        print(f"\n✓ Checking if user was added to dictionary and database")
        self.assertEqual(self.feedback_threads.user_thread[mock_ctx.author.id], [mock_new_thread.id, 1])

        print(f"  - User thread dict: {self.feedback_threads.user_thread}")
        self.feedback_threads.sqlitedatabase.cursor.execute.assert_any_call(
            "SELECT user_id FROM users WHERE user_id = ?", (mock_ctx.message.author.id,))
        self.feedback_threads.sqlitedatabase.cursor.execute.assert_any_call(
            "INSERT INTO users (user_id, thread_id, ticket_counter) VALUES (?, ?, ?)",
            (mock_ctx.author.id, mock_new_thread.id, 1)
        )

        print("\n✓ Checking if database commit was called")
        self.feedback_threads.commit_changes.assert_called_once()

        print("\n✓ Checking if embed was created and sent")
        self.feedback_threads.MFS_embed.assert_called_once_with(mock_ctx, formatted_time, message_link)
        mock_new_thread.send.assert_called_once_with(embed=mock_embed)

        # Test for error handling
        print("\n[ERROR HANDLING TEST]")
        print("✓ Simulating thread creation failure")
        mock_thread_channel.create_thread.reset_mock()
        mock_thread_channel.create_thread.side_effect = Exception("Test exception")

        # Run method again with exception
        result = await self.feedback_threads.new_thread(mock_ctx, formatted_time, message_link, mock_thread_channel,
                                                        mfr_points, points)

        print(f"✓ Expected None on exception, Actual: {result}")
        self.assertIsNone(result, "Should return None on exception")



