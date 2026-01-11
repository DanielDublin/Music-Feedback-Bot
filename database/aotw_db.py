import sqlite3

class SQLiteDatabase:
    def __init__(self, db_name='aotw_poll.sqlite'):
        """
        Initialize the SQLite database connection and cursor.
        
        Args:
            db_name (str): Name of the SQLite database file - 'aotw_poll.sqlite'.
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
        Creates the 'aotw_poll_data' table in the SQLite database if it does not already exist.
        The table includes:
        - user_id: Integer, primary key.
        - thread_id: Integer, representing the thread identifier.
        - ticket_counter: Integer, for counting tickets.

        Commits changes.
        """

        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS aotw_poll_data (
                    user_id INTEGER PRIMARY KEY,
                    start_date TEXT,
                    end_date TEXT,
                    vote_count INTEGER,
                    submission_link TEXT
                )
            ''')
            self.connection.commit()
            print("SQLite database created or already exists")

        except sqlite3.Error as e:
            print(f"Error creating table: {e}")