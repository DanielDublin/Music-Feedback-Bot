import sqlite3

class SQLiteDatabase:
    def __init__(self, db_name='feedback_threads.sqlite'):
        """
        Initialize the SQLite database connection and cursor.
        
        Args:
            db_name (str): Name of the SQLite database file - 'feedback_threads.sqlite'.
        """

        try:
            self.connection = sqlite3.connect(db_name)
            self.cursor = self.connection.cursor()
            self.create_table()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
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
            print("SQLite database created or already exists")

        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

    def fetch_all_users(self):
        """
        Queries and returns all users in the 'users' table.
        """
        try:
            self.cursor.execute("SELECT user_id, thread_id, ticket_counter FROM users") # It's good practice to select specific columns
            rows = self.cursor.fetchall()

            return rows 

        except sqlite3.Error as e:
            print(f"Error querying users: {e}")
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
            print(f"Error inserting user: {e}")
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
            print(f"Error updating ticket_counter: {e}")

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
            print(f"Error deleting user: {e}")


    def close_connection(self):
        """
        Closes the database connection.
        """

        try:
            self.connection.close()
            print("Database connection closed")

        except sqlite3.Error as e:
            print(f"Error closing connection: {e}")

    def __del__(self):
        """
        Destructor to ensure the database connection is closed when the object is deleted.
        """
        self.close_connection()

