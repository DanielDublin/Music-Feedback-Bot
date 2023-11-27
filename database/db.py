import aiomysql
import os
import asyncio
from dotenv import load_dotenv
import json
import logging


#for every sql querry - search in error "Lost connection " and restart thing

load_dotenv()
DATABASE_ERROR = -2

WEEK_TIME_IN_SECONDS = 60 * 60 * 24 * 7

# Your database connection pool (initialize it as needed)
pool = None

users_dict = {}  # id -> points, rank, warnings, kicks


# Initialize the database connection (async)
async def init_database():
    global pool
    pool = await aiomysql.create_pool(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("PORT")),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        db=os.environ.get("DB_NAME"),
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

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None


async def update_dict_from_db(user_id):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    users_dict[user_id] = {}  # Initializes the parent dict - the user ID

    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:

                # Fetch all the data about the user from DB
                await cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id)))  # Convert to str
                result = await cursor.fetchone()

                if result is not None:  # Adding only points and warnings, not Rank to reduce queries
                    users_dict[user_id]["Points"] = int(result["points"])
                    users_dict[user_id]["Warnings"] = int(result["warnings"])
                    users_dict[user_id]["Kicks"] = int(result["kicks"])
                else:
                    del users_dict[user_id]
                    await add_user(user_id, True)  # User is absent from DB
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            update_dict_from_db(user_id)


async def fetch_rank_from_db(user_id):
    global pool

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch rank from the database
                await cursor.execute("""
                    SELECT (SELECT COUNT(*) + 1
                            FROM users AS u
                            WHERE u.points > (SELECT points FROM users WHERE user_id = %s)) AS Rank_value
                """, (str(user_id)))  # Convert to str

        result = await cursor.fetchone()
        return result
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            return fetch_rank_from_db(user_id)


# Fetch points for a user
async def fetch_points(user_id: str):
    global users_dict

    if user_id in users_dict:
        return users_dict[user_id]["Points"]  # Return points from the dictionary
    else:
        await update_dict_from_db(user_id)
        return users_dict[user_id]["Points"]


# Fetch rank for a user
async def fetch_rank(user_id: str):
    global users_dict

    if user_id in users_dict and "Rank" in users_dict[user_id].keys():
        return users_dict[user_id]["Rank"]  # Return rank from the dictionary

    else:
        if user_id not in users_dict:
            await update_dict_from_db(user_id)
        result = await fetch_rank_from_db(user_id)

        if result is not None:
            users_dict[user_id]["Rank"] = result["Rank_value"]  # Update rank in the dictionary
            return result["Rank_value"]
        else:
            return DATABASE_ERROR  # database issue


# Fetch kicks for a user
async def fetch_kicks(user_id: str):
    global users_dict

    if user_id in users_dict:
        return users_dict[user_id]["Kicks"]  # Return points from the dictionary
    else:
        await update_dict_from_db(user_id)
        return users_dict[user_id]["Kicks"]
    

# Fetch the top 5 users with the best point scores
async def fetch_top_users():
    global pool, users_dict
    top_users = None

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None
    try:
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
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            return fetch_top_users()
    top_users_dict = {}

    for index, user in enumerate(top_users, start=1):
        user_id = user["user_id"]
        points = user["points"]
        rank = index  # Calculate the rank based on the order in the result set

        user_data = {"points": points, "rank": rank}
        top_users_dict[user_id] = user_data

    return top_users_dict


# Reduce points for a user
async def reduce_points(user_id, points: int):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if user_id in users_dict:
        users_dict[user_id]["Points"] -= points  # Reduce points in the dictionary
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Reduce points in the database
                await cursor.execute("UPDATE users SET points = (points - %s) WHERE user_id = %s",
                                     (points, str(user_id)))  # Convert to str
                await conn.commit()
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            reduce_points(user_id, points)


# Add points for a user
async def add_points(user_id, points: int):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if user_id in users_dict:
        users_dict[user_id]["Points"] += points  # Add points in the dictionary
        
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add points in the database
                await cursor.execute("UPDATE users SET points = points + %s WHERE user_id = %s",
                                     (points, str(user_id)))  # Convert to str
                await conn.commit()
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            add_points(user_id, points)
          
            
# Add a kick to a user
async def add_kick(user_id):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None
 
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add a kick in the database
                await cursor.execute("UPDATE users SET kicks = kicks + %s WHERE user_id = %s",
                                     (1, str(user_id)))  # Convert to str
                await conn.commit()
    except Exception as e:
        if "lost connection" in str(e).lower():
            await init_database()
            add_kick(user_id)
    

# Add a user
async def add_user(user_id, called_from_update_func=False):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if user_id not in users_dict:
        users_dict[user_id] = {}  # Initializes the parent dict - the user ID
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Add or insert user in the database if it doesnt exist
                
                    await cursor.execute("INSERT IGNORE INTO users (user_id) VALUES (%s)", (str(user_id)))  # Convert to str
                    await conn.commit()
        except Exception as e:
            if "lost connection" in str(e).lower():
                await init_database()
                add_user(user_id)
                return
            
        # Update the dict to whatever the db has,
        #  in case that its a user that just joined after being kicked
        if not called_from_update_func:
            await update_dict_from_db(user_id)


# Remove a user from DB - User was banned
async def remove_user(user_id):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if user_id in users_dict:
        del users_dict[user_id]  # Remove user from the dictionary
        
    
        
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM users WHERE user_id = %s", (str(user_id)))  # Convert to str
                await conn.commit()
    except Exception as e:
            if "lost connection" in str(e).lower():
                await init_database()
                remove_user(user_id)



# Add warning to a user
async def add_warning_to_user(user_id: str):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if user_id not in users_dict:
        await update_dict_from_db(user_id)

    users_dict[user_id]["Warnings"] += 1  # Add points in the dictionary
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Add points in the database
                await cursor.execute("UPDATE users SET warnings = warnings + %s WHERE user_id = %s",
                                     (1, str(user_id)))  # Convert to str
                await conn.commit()
    except Exception as e:
            if "lost connection" in str(e).lower():
                await init_database()
                return add_warning_to_user(user_id)            

    return users_dict[user_id]["Warnings"]


async def migrate_warnings():
    global pool, users_dict
    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    # Configure the logger
    logging.basicConfig(filename='migration.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Read user_ids_json from a file
    with open('user_ids.json', 'r') as file:
        user_ids_json = json.load(file)

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for user_id, warnings in user_ids_json.items():
                # Check if the user ID exists in the database
                await cursor.execute("UPDATE users SET warnings = %s WHERE user_id = %s;", (warnings, user_id))
                if cursor.rowcount > 0:
                    logging.info(f"Updated user {user_id} with {warnings} warnings")
                else:
                    logging.warning(f"User {user_id} not found in the database")


# Reset points for a user - user left or by command
async def reset_points(user_id, is_kicked=False):
    global pool, users_dict

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    if is_kicked:
        del users_dict[user_id]
        
    if user_id in users_dict:
        users_dict[user_id]["Points"] = 0  # Reset points in the dictionary
        
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Send SQL query to reset points for the user in the database
                await cursor.execute("UPDATE users SET points = 0 WHERE user_id = %s", (str(user_id)))  # Convert to str
    except Exception as e:
            if "lost connection" in str(e).lower():
                await init_database()
                reset_points(user_id)    
          


async def json_migration(users):
    global pool

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # The batch to accumulate SQL commands
            batch = []

            for user_id, user_data in users.items():
                points = user_data["points"]  # Get points from the sub-dictionary or default to 0
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



async def migrate_warnings_extreme(user_warnings):

    global pool

    if pool is None:
        await init_database()  # Reconnect the database if the pool is None
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                    for user_id, warnings in user_warnings.items():
                        # Check if the user is in the database
                        await cur.execute("SELECT * FROM users WHERE user_id = %s;", (user_id))
                        existing_user = await cur.fetchone()

                        if existing_user is not None:
                            # Update the existing user's warnings
                            await cur.execute("UPDATE users SET warnings = %s WHERE user_id = %s;",
                                              (warnings, user_id))
                            print(f"Updated warnings for user {user_id}")
                        else:
                            # Insert a new row for the user
                            await cur.execute("INSERT INTO users (user_id, points, warnings, kicks) "
                                              "VALUES (%s, %s, %s, %s);",
                                              (user_id, 0, warnings, 0))
                            print(f"Inserted a new row for user {user_id}")

    except Exception as e:
        print(f"An error occurred: {e}")