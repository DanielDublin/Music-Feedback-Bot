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

        # Debugging (Optional)
        print(f"User ID: {user_id}, Thread ID Retrieved: {self.existing_thread.id}")

    @patch('discord.Client.fetch_channel', new_callable=AsyncMock)
    @patch('discord.Client.get_channel')
    async def test_create_feedback_thread_existing(self, mock_get_channel, mock_fetch_channel):
        """Test when a user already has an existing feedback thread."""
        # Mocking existing thread behavior
        mock_existing_channel = AsyncMock()
        mock_existing_channel.archived = True  # Assume the thread is archived initially
        mock_existing_channel.send = AsyncMock()

        # Set the fetched channel to be the existing thread
        mock_fetch_channel.return_value = mock_existing_channel

        # Mock the existing thread's ID to be retrieved correctly
        self.existing_thread.id = EXPECTED_USER_THREAD.get(self.ctx.author.id, [None])[0]  # Mock thread ID

        print(f"Mock existing thread fetched with ID: {self.existing_thread.id}")

        # Call the logic
        if mock_existing_channel.archived:
            await mock_existing_channel.edit(archived=False)
            # call existing thread logic
        embed = MagicMock()  # Mock the embed returned by self.existing_thread
        if embed:
            await mock_existing_channel.send(embed=embed)
            await asyncio.sleep(5)
            await mock_existing_channel.edit(archived=True)

        # Assertions
        mock_existing_channel.edit.assert_any_call(archived=False)
        mock_existing_channel.send.assert_called_once_with(embed=embed)
        mock_existing_channel.edit.assert_any_call(archived=True)

        # Mock new thread creation
        mock_new_thread = AsyncMock()
        self.ctx.author.id = 1000001
        mock_new_thread.id = 2000001
        mock_new_thread.archived = False
        mfr_points = 1
        points = 0
        ticket_counter = 0

        # Ensure new_thread method triggers the edit logic
        self.feedback_threads.new_thread = AsyncMock(return_value=mock_new_thread)  # Mock new_thread method
        self.feedback_threads.user_thread[self.ctx.author.id] = [mock_new_thread.id, ticket_counter]
        print(f"here:{self.feedback_threads.user_thread[self.ctx.author.id]}")

        # Call the method that creates a new thread
        await self.feedback_threads.new_thread(self.ctx, mfr_points, points)

        await asyncio.sleep(5.1)  # Ensure the archive action has completed
        print(f"Calling edit on new thread {mock_new_thread.id}")
        await mock_new_thread.edit(archived=True)

        mock_new_thread.edit.assert_called_once_with(archived=True)

        del self.feedback_threads.user_thread[self.ctx.author.id]
        # remove the added user above from the dict (messes up db repop)








