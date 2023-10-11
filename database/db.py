import aiomysql
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
USER_ID = 0
POINTS = 1
WARNINGS = 2
DATABASE_ERROR = -2


WEEK_TIME_IN_SECONDS = 60*60*24*7

# Your database connection pool (initialize it as needed)
pool = None
 
users_dict = {} # id -> points, rank, warnings

# Initialize the database connection (async)
async def init_database():
    global pool
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





# Define the weekly task coroutine
def weekly_task():
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

async def update_dict_from_db(user_id):
    global pool, users_dict, POINTS, WARNINGS
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            
            # Fetch all the data about the user from DB
            await cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id)))  # Convert to str
            result = await cursor.fetchone()
            
            if result is not None: # Addding only points and warnings, not Rank to reduce queries
                users_dict[user_id]["Points"] = result[POINTS]
                users_dict[user_id]["Warnings"] = result[WARNINGS]
            else:
                await add_user(user_id)  # User is absent from DB
            
                
async def fetch_rank_from_db(user_id):
    global pool
    
    async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch rank from the database
                await cursor.execute("""
                    SELECT COUNT(*) + 1
                    FROM users
                    WHERE points > (SELECT points FROM users WHERE user_id = %s)
                """, (str(user_id)))  # Convert to str
    result = await cursor.fetchone()
    return result

# Fetch points for a user
async def fetch_points(user_id: int):
    global users_dict
    
    if user_id in users_dict:
        return users_dict[user_id]["Points"]  # Return points from the dictionary
    else:
        await update_dict_from_db(user_id)
        return users_dict[user_id]["Points"]
      

# Fetch rank for a user
async def fetch_rank(user_id: int):
    global users_dict
    
    if user_id in users_dict and users_dict[user_id]["Rank"] is not None:
        return users_dict[user_id]["Rank"]  # Return rank from the dictionary
    
    else:
        if user_id not in users_dict:
            await update_dict_from_db(user_id)        
        result = await fetch_rank_from_db()
        
        if result is not None:      
            users_dict[user_id]["Rank"] = result[0]    # Update rank in the dictionary
            return result[0]
        else:
            return DATABASE_ERROR #database issue

     


# Fetch the top 5 users with the best point scores
async def fetch_top_users():
    global pool, users_dict, USER_ID, POINTS
    
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
    top_users_dict = {user[USER_ID]: str(user[POINTS]) for user in top_users}
    return top_users_dict
        


# Reduce points for a user
async def reduce_points(user_id: int, points: int):
    global pool, users_dict
    
    if user_id in users_dict:
        users_dict[user_id][0] -= points  # Reduce points in the dictionary        
   
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Reduce points in the database
            await cursor.execute("UPDATE users SET points = (points - %s) WHERE user_id = %s", (points, str(user_id)))  # Convert to str
            await conn.commit()
           

# Add points for a user
async def add_points(user_id: int, points: int):
    global pool, users_dict
    
    if user_id in users_dict:
        users_dict[user_id][0] += points  # Add points in the dictionary
    else:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add points in the database
                await cursor.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (points, str(user_id)))  # Convert to str
                await conn.commit()
 

# Add a user
async def add_user(user_id: int):
    global pool, users_dict
    
    if user_id not in users_dict:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add or replace user in the database (use "REPLACE INTO" or "INSERT INTO ON DUPLICATE KEY UPDATE" depending on your database)
                await cursor.execute("REPLACE INTO users (user_id) VALUES (%s)", (str(user_id)))  # Convert to str
                await conn.commit()
        user_data = {"Points": 0, "Warnings": 0}
        users_dict[user_id] = user_data  # Add user to the dictionary

# Remove a user
async def remove_user(user_id: int):
    global pool, users_dict
    
    if user_id in users_dict:
        del users_dict[user_id]  # Remove user from the dictionary
        
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Send SQL query to remove the user from the database
            await cursor.execute("DELETE FROM users WHERE user_id = %s", (str(user_id)))  # Convert to str
            await conn.commit()

# Reset points for a user
async def reset_points(user_id: int):
    global pool, users_dict
    
    if user_id in users_dict:
        users_dict[user_id]["Points"] = 0  # Reset points in the dictionary
        
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Send SQL query to reset points for the user in the database
            await cursor.execute("UPDATE users SET points = 0 WHERE user_id = %s", (str(user_id)))  # Convert to str
            await conn.commit()
    

async def json_migration(users):
    global pool
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # The batch to accumulate SQL commands
            batch = []
            
            for user_id, user_data in users.items():
                points = user_data.get("points", 0)  # Default points to 0 if not present
                batch.append((user_id, points))
                
                # If the batch size reaches 500 or at the end of the loop, execute the REPLACE command
                if len(batch) == 500 or user_id == list(users.keys())[-1]:
                    placeholders = ",".join(["(%s, %s, 0)"] * len(batch))
                    sql = f"REPLACE INTO users (user_id, points, warnings) VALUES {placeholders}; "
                    values = [item for sublist in batch for item in sublist]
                    
                    await cursor.execute(sql, values)
                    await conn.commit()     
                    
                    # Clear the batch for the next set of data
                    batch = []
    



    
