import sqlite3
import random

class SQLiteDatabase:
    def __init__(self):
        self.connection = sqlite3.connect('feedback_threads.db')
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

    def insert_fake_data(self, num_entries=10):
        # Insert fake data into the users table
        for _ in range(num_entries):
            user_id = random.randint(1, 1000)  # Random user ID between 1 and 1000
            thread_id = random.randint(1, 100)  # Random thread ID between 1 and 100
            ticket_counter = random.randint(1, 10)  # Random ticket counter between 1 and 10

            # Insert the generated values into the users table
            self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, thread_id, ticket_counter)
            VALUES (?, ?, ?)
            ''', (user_id, thread_id, ticket_counter))

        # Commit the changes and print a message
        self.connection.commit()
        print(f"Inserted {num_entries} fake data entries into the users table.")


# Example usage
db = SQLiteDatabase()
db.insert_fake_data()  # Insert 10 fake entries
