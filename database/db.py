import aiomysql
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

WEEK_TIME_IN_SECONDS = 60*60*24*7

# Your database connection pool (initialize it as needed)
pool = None
 
users_dict = {} # id -> points, rank, warnings

# Initialize the database connection (async)
async def init_database():
    pool = await aiomysql.create_pool(
        host= os.environ.get("DB_HOST"),
        port= int(os.environ.get("PORT")),
        user= os.environ.get("DB_USER"),
        password= os.environ.get("DB_PASSWORD"),
        db= os.environ.get("DB_NAME"),
        autocommit=True,
        charset='utf8mb4',
        cursorclass=aiomysql.DictCursor,
    )
    print("Database connection established.")
    return pool




# Define the weekly task coroutine
async def weekly_task():
    global users_dict
    users_dict = {}
    


# Schedule the weekly task to run every Sunday at a specific time (adjust as needed)
async def schedule_weekly_task():
    while True:
        await asyncio.sleep(WEEK_TIME_IN_SECONDS)
        weekly_task()


# Initialize the database connection pool (you should do this before using the functions)
async def initialize_database_pool():
    global pool
    pool = await aiomysql.create_pool(host='your_host', user='your_user', password='your_password', db='your_database')

# Fetch points for a user
async def fetch_points(user_id: int):
    if user_id in users_dict:
        return users_dict[user_id][0]  # Return points from the dictionary
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch points from the database
                await cursor.execute("SELECT points FROM users WHERE user_id = %s", (str(user_id),))  # Convert to str
                result = await cursor.fetchone()
                if result:
                    points = result[0]
                    users_dict[user_id] = [points, None, None]  # Initialize user in the dictionary
                    return points
                else:
                    return None  # User not found

# Fetch rank for a user
async def fetch_rank(user_id: int):
    if user_id in users_dict and users_dict[user_id][1] is not None:
        return users_dict[user_id][1]  # Return rank from the dictionary
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch rank from the database
                await cursor.execute("""
                    SELECT COUNT(*) + 1
                    FROM users
                    WHERE points > (SELECT points FROM users WHERE user_id = %s)
                """, (str(user_id),))  # Convert to str
                result = await cursor.fetchone()
                if result:
                    rank = result[0]
                    if user_id in users_dict:
                        users_dict[user_id][1] = rank  # Update rank in the dictionary
                    else:
                        users_dict[user_id] = [None, rank, None]  # Initialize user in the dictionary
                    return rank
                else:
                    return None  # User not found

# Fetch the top 5 users with the best point scores
async def fetch_top_users():
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Fetch top users from the database
            await cursor.execute("""
                SELECT user_id, points
                FROM users
                ORDER BY points DESC
                LIMIT 5
            """)
            top_users = await cursor.fetchall()
            top_users_dict = {user[0]: user[1] for user in top_users}
            return top_users_dict

# Reduce points for a user
async def reduce_points(user_id: int, points: int):
    if user_id in users_dict:
        users_dict[user_id][0] -= points  # Reduce points in the dictionary
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Reduce points in the database
                await cursor.execute("UPDATE users SET points = points - %s WHERE user_id = %s", (points, str(user_id)))  # Convert to str
                await conn.commit()
                # Fetch updated user data from the database
                await cursor.execute("SELECT points FROM users WHERE user_id = %s", (str(user_id),))  # Convert to str
                result = await cursor.fetchone()
                if result:
                    updated_points = result[0]
                    users_dict[user_id] = [updated_points, None, None]  # Update user in the dictionary

# Add points for a user
async def add_points(user_id: int, points: int):
    if user_id in users_dict:
        users_dict[user_id][0] += points  # Add points in the dictionary
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add points in the database
                await cursor.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (points, str(user_id)))  # Convert to str
                await conn.commit()
                # Fetch updated user data from the database
                await cursor.execute("SELECT points FROM users WHERE user_id = %s", (str(user_id),))  # Convert to str
                result = await cursor.fetchone()
                if result:
                    updated_points = result[0]
                    users_dict[user_id] = [updated_points, None, None]  # Update user in the dictionary

# Add a user
async def add_user(user_id: int):
    if user_id not in users_dict:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add or replace user in the database (use "REPLACE INTO" or "INSERT INTO ON DUPLICATE KEY UPDATE" depending on your database)
                await cursor.execute("REPLACE INTO users (user_id, points) VALUES (%s, 0)", (str(user_id),))  # Convert to str
                await conn.commit()
                users_dict[user_id] = [0, None, None]  # Add user to the dictionary

# Remove a user
async def remove_user(user_id: int):
    if user_id in users_dict:
        del users_dict[user_id]  # Remove user from the dictionary
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Send SQL query to remove the user from the database
            await cursor.execute("DELETE FROM users WHERE user_id = %s", (str(user_id),))  # Convert to str
            await conn.commit()

# Reset points for a user
async def reset_points(user_id: int):
    if user_id in users_dict:
        users_dict[user_id][0] = 0  # Reset points in the dictionary
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Send SQL query to reset points for the user in the database
            await cursor.execute("UPDATE users SET points = 0 WHERE user_id = %s", (str(user_id),))  # Convert to str
            await conn.commit()
    

async def json_migration(users):
    



    
