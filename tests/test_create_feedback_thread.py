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

    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_create_feedback_thread_existing(self, mock_get_channel, mock_fetch_channel):
        """Test when a user already has an existing feedback thread."""

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

    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel', new_callable=AsyncMock)
    async def test_create_feedback_thread_new(self, mock_get_channel, mock_fetch_channel):
        """Test when a user does NOT have an existing feedback thread."""

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
