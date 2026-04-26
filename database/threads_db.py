import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    def __init__(self):
        # Build path relative to this script so it always finds the same file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Place it in the same 'data' folder as MF_DB.db
        db_path = os.path.join(current_dir, "data", "feedback_threads.sqlite")
        
        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            self.create_table()
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}", exc_info=True)
            raise

    def create_table(self):
        """
        Creates the 'users' table in the SQLite database if it does not already exist.
        The table includes:
        - user_id: Integer, primary key.
        - thread_id: Integer, representing the thread identifier.
        - ticket_counter: Integer, for counting tickets.

        Commits changes.
        """

        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    thread_id INTEGER,
                    ticket_counter INTEGER
                )
            ''')
            self.connection.commit()
            logger.info("SQLite database created or already exists")

        except sqlite3.Error as e:
            logger.error(f"Error creating table: {e}", exc_info=True)

    def fetch_all_users(self):
        """
        Queries and returns all users in the 'users' table.
        """
        try:
            self.cursor.execute("SELECT user_id, thread_id, ticket_counter FROM users") # It's good practice to select specific columns
            rows = self.cursor.fetchall()

            return rows 

        except sqlite3.Error as e:
            logger.error(f"Error querying users: {e}", exc_info=True)
            return []


    def insert_user(self, user_id: int, thread_id: int, ticket_counter: int = 1):
        """
        Inserts a new user with a user_id, thread_id, and ticket_counter.
        
        Args:
            user_id (int): The Discord user's ID.
            thread_id (int): Thread identifier.
            ticket_counter (int): Number of tickets, defaults to 0.
        
        Returns:
            int: The user_id of the newly inserted user.
        """

        try:
            self.cursor.execute('''
                INSERT INTO users (user_id, thread_id, ticket_counter)
                VALUES (?, ?, ?)
            ''', (user_id, thread_id, ticket_counter))
            self.connection.commit()
            user_id = self.cursor.lastrowid

            return user_id
        
        except sqlite3.Error as e:
            logger.error(f"Error inserting user: {e}", exc_info=True)
            return None

    def update_ticket_counter(self, user_id, ticket_counter):
        """
        Updates the ticket_counter for a specific user.
        
        Args:
            user_id (int): The ID of the user to update.
            ticket_counter (int): New ticket counter value that increments by 1.
        """
        try:
            self.cursor.execute('''
                UPDATE users 
                SET ticket_counter = ticket_counter + 1 
                WHERE user_id = ?
            ''', (user_id,))
            self.connection.commit()

        except sqlite3.Error as e:
            logger.error(f"Error updating ticket_counter: {e}", exc_info=True)

    def delete_user(self, user_id):
        """
        Deletes a user from the 'users' table.
        
        Args:
            user_id (int): The ID of the user to delete.
        """
        try:
            self.cursor.execute('''
                DELETE FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            self.connection.commit()

        except sqlite3.Error as e:
            logger.error(f"Error deleting user: {e}", exc_info=True)


    def close_connection(self):
        """
        Closes the database connection.
        """

        try:
            self.connection.close()
            logger.info("Database connection closed")

        except sqlite3.Error as e:
            logger.error(f"Error closing connection: {e}", exc_info=True)

    def __del__(self):
        """
        Destructor to ensure the database connection is closed when the object is deleted.
        """
        self.close_connection()

