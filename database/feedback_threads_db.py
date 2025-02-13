import sqlite3
import random

class SQLiteDatabase:
    def __init__(self):
        self.connection = sqlite3.connect('feedback_threads.sqlite')
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        # Create the users table if it doesn't exist
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,  -- id as the primary key
            thread_id INT,
            ticket_counter INT
        )
        ''')
        self.connection.commit()
        print("SQLite database created if not already")

        # Query and print existing users in the database
        self.cursor.execute("SELECT * FROM users")
        rows = self.cursor.fetchall()
        print("Users in database before drop:")
        for row in rows:
            print(row)

#         # Drop the users table
#         self.cursor.execute("DROP TABLE IF EXISTS users")
#         self.connection.commit()
#
#         # Confirm that the table has been dropped and print tables left
#         self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#         tables = self.cursor.fetchall()
#         print("Remaining tables after drop:", tables)
#
#         # Attempt to query the users table again, will result in an error
#         try:
#             self.cursor.execute("SELECT * FROM users")
#             rows = self.cursor.fetchall()
#             print("Users in database after drop (should be empty):")
#             for row in rows:
#                 print(row)
#         except sqlite3.OperationalError as e:
#             print(f"Error after dropping table: {e}")
#
# # Example usage:
# db = SQLiteDatabase()
