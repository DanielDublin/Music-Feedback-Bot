# import unittest
# from unittest.mock import MagicMock, patch
# from cogs.feedback_threads import FeedbackThreads
# import sqlite3
# from tests.mock_user_data import *
# import asyncio
#
# class TestSQLiteDb(unittest.IsolatedAsyncioTestCase):
#     async def asyncSetUp(self):
#         # Create an in-memory SQLite database
#         self.connection = sqlite3.connect(':memory:')
#         self.cursor = self.connection.cursor()
#
#         # Create the mock users table
#         self.cursor.execute('''
#             CREATE TABLE users (
#                 user_id INTEGER PRIMARY KEY,
#                 thread_id INTEGER,
#                 ticket_counter INTEGER
#             )
#         ''')
#
#         self.connection.commit()
#
#     async def asyncTearDown(self):
#         # Clear all data
#         self.cursor.execute("DELETE FROM users")
#         self.connection.commit()
#
#
#         # Close connection
#         self.cursor.close()
#         self.connection.close()
#
#     @patch('cogs.feedback_threads.SQLiteDatabase')
#     async def test_initialize_sqldb_with_mock_data(self, mock_sqlite_db):
#         # Mock user data
#         self.cursor.executemany('''
#             INSERT INTO users (user_id, thread_id, ticket_counter)
#             VALUES (?, ?, ?)
#         ''', MOCK_USERS_DATA)
#
#         # Mock the SQLiteDatabase instance to use the in-memory database
#         mock_sqlite_db_instance = MagicMock()
#         mock_sqlite_db_instance.cursor = self.cursor
#         mock_sqlite_db.return_value = mock_sqlite_db_instance
#
#         # Create an instance of the bot and feedback threads
#         bot = MagicMock()
#         feedback_threads = FeedbackThreads(bot)
#         feedback_threads.sqlitedatabase = mock_sqlite_db_instance
#         feedback_threads.user_thread = {}
#
#         # Check the state of user_thread before initialization
#         print("user_thread items before:", len(feedback_threads.user_thread))
#
#         # Call the method to initialize the SQLite DB (this should populate user_thread)
#         await feedback_threads.initialize_sqldb()
#
#         # Check the state of user_thread after initialization
#         print("user_thread items after:", len(feedback_threads.user_thread))
#
#         # Use the expected dictionary we created from MOCK_USERS_DATA
#         self.maxDiff = None  # Show the full diff if they don't match
#
#         self.assertEqual(feedback_threads.user_thread, EXPECTED_USER_THREAD)
#
#
#     @patch('cogs.feedback_threads.SQLiteDatabase')
#     async def test_initialize_sqldb_with_empty_data(self, mock_sqlite_db):
#         # Mock empty user data
#         self.cursor.executemany('''
#             INSERT INTO users (user_id, thread_id, ticket_counter)
#             VALUES (?, ?, ?)
#         ''', EMPTY_USERS_DATA)
#
#         # Mock the SQLiteDatabase instance to use the in-memory database
#         mock_sqlite_db_instance = MagicMock()
#         mock_sqlite_db_instance.cursor = self.cursor
#         mock_sqlite_db.return_value = mock_sqlite_db_instance
#
#         # Create an instance of the bot and feedback threads
#         bot = MagicMock()
#         feedback_threads = FeedbackThreads(bot)
#         feedback_threads.sqlitedatabase = mock_sqlite_db_instance
#         feedback_threads.user_thread = {}
#
#         # Check the state of user_thread before initialization
#         print("user_thread items before:", len(feedback_threads.user_thread))
#
#         # Call the method to initialize the SQLite DB (this should populate user_thread)
#         await feedback_threads.initialize_sqldb()
#
#         # Check the state of user_thread after initialization
#         print("user_thread items after:", len(feedback_threads.user_thread))
#
#         self.assertEqual(feedback_threads.user_thread, {})  # Ensure user_thread is empty
