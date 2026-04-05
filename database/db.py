import aiosqlite
import os
import asyncio
from dotenv import load_dotenv
import json
import logging

load_dotenv()

DATABASE_ERROR = -2
WEEK_TIME_IN_SECONDS = 60 * 60 * 24 * 7

# Single persistent connection (best practice for SQLite + async)
db_connection = None
users_dict = {}  # id -> {"Points": int, "Warnings": int, "Kicks": int, "Rank": int (optional)}


async def init_database():
    global db_connection

    # === PATH TO DB inside database/data/ ===
    current_dir = os.path.dirname(os.path.abspath(__file__))   # points to "database" folder
    data_dir = os.path.join(current_dir, "data")
    os.makedirs(data_dir, exist_ok=True)                       # create data/ if missing

    # Let .env dictate the filename (default to MF_DB.db), but FORCE it into the data_dir
    db_filename = os.environ.get("DB_NAME", "MF_DB.db")
    db_file = os.path.join(data_dir, db_filename)

    db_connection = await aiosqlite.connect(db_file)
    db_connection.row_factory = aiosqlite.Row

    # === CRITICAL FOR SAFE ASYNC READ/WRITE ===
    await db_connection.execute("PRAGMA journal_mode=WAL;")
    await db_connection.execute("PRAGMA busy_timeout=5000;")   # helps with rare lock issues
    await db_connection.commit()

    # Auto-create table if it doesn't exist
    await db_connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            kicks INTEGER DEFAULT 0
        )
    """)
    await db_connection.commit()

    print(f"SQLite database connected (WAL mode) at: {db_file}")


# ====================== WEEKLY RESET ======================
def weekly_task():
    global users_dict
    users_dict.clear()


async def schedule_weekly_task():
    while True:
        await asyncio.sleep(WEEK_TIME_IN_SECONDS)
        weekly_task()


# ====================== INIT HELPER ======================
async def initialize_database_pool():
    global db_connection
    if db_connection is None:
        await init_database()


# ====================== CORE FUNCTIONS ======================
async def update_dict_from_db(user_id: str):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    users_dict[user_id] = {}
    async with db_connection.execute(
        "SELECT * FROM users WHERE user_id = ?", (str(user_id),)
    ) as cursor:
        result = await cursor.fetchone()

    if result:
        users_dict[user_id]["Points"] = int(result["points"])
        users_dict[user_id]["Warnings"] = int(result["warnings"])
        users_dict[user_id]["Kicks"] = int(result["kicks"])
    else:
        del users_dict[user_id]
        await add_user(user_id, called_from_update_func=True)
        users_dict[user_id] = {"Points": 0, "Warnings": 0, "Kicks": 0}


async def fetch_rank_from_db(user_id: str):
    global db_connection
    if db_connection is None:
        await init_database()

    query = """
        SELECT (SELECT COUNT(*) + 1 
                FROM users AS u 
                WHERE u.points > (SELECT points FROM users WHERE user_id = ?)) AS Rank_value
    """
    async with db_connection.execute(query, (str(user_id),)) as cursor:
        result = await cursor.fetchone()
        return result


# Fetch points (cached)
async def fetch_points(user_id: str):
    if user_id in users_dict and "Points" in users_dict[user_id]:
        return users_dict[user_id]["Points"]
    if user_id in users_dict:
        del users_dict[user_id]
    await update_dict_from_db(user_id)
    return users_dict[user_id]["Points"]


# Top 10
async def top_10():
    if db_connection is None:
        await init_database()
    async with db_connection.execute("""
        SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10
    """) as cursor:
        return await cursor.fetchall()


# Fetch rank (cached)
async def fetch_rank(user_id: str):
    if user_id in users_dict and "Rank" in users_dict[user_id]:
        return users_dict[user_id]["Rank"]

    if user_id not in users_dict:
        await update_dict_from_db(user_id)

    result = await fetch_rank_from_db(user_id)
    if result and result["Rank_value"] is not None:
        users_dict[user_id]["Rank"] = result["Rank_value"]
        return result["Rank_value"]
    return DATABASE_ERROR


async def fetch_kicks(user_id: str):
    if user_id in users_dict and "Kicks" in users_dict[user_id]:
        return users_dict[user_id]["Kicks"]
    await update_dict_from_db(user_id)
    return users_dict[user_id]["Kicks"]


# Top 5 with rank
async def fetch_top_users():
    if db_connection is None:
        await init_database()

    top_users_dict = {}
    async with db_connection.execute("""
        SELECT user_id, points FROM users ORDER BY points DESC LIMIT 5
    """) as cursor:
        top_users = await cursor.fetchall()

    for index, user in enumerate(top_users, start=1):
        top_users_dict[user["user_id"]] = {
            "points": user["points"],
            "rank": index
        }
    return top_users_dict


# ====================== WRITE OPERATIONS ======================
async def reduce_points(user_id: str, points: int):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id in users_dict:
        users_dict[user_id]["Points"] -= points

    await db_connection.execute(
        "UPDATE users SET points = points - ? WHERE user_id = ?",
        (points, str(user_id))
    )
    await db_connection.commit()


async def add_points(user_id: str, points: int):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id in users_dict:
        users_dict[user_id]["Points"] += points

    await db_connection.execute(
        "UPDATE users SET points = points + ? WHERE user_id = ?",
        (points, str(user_id))
    )
    await db_connection.commit()


async def add_kick(user_id: str):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id not in users_dict:
        await update_dict_from_db(user_id)

    if "Kicks" in users_dict[user_id]:
        users_dict[user_id]["Kicks"] += 1
    else:
        users_dict[user_id]["Kicks"] = 1

    await db_connection.execute(
        "UPDATE users SET kicks = kicks + 1 WHERE user_id = ?",
        (str(user_id),)
    )
    await db_connection.commit()


async def add_user(user_id: str, called_from_update_func=False):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id not in users_dict:
        users_dict[user_id] = {}

    await db_connection.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (str(user_id),)
    )
    await db_connection.commit()

    if not called_from_update_func:
        await update_dict_from_db(user_id)


async def remove_user(user_id: str):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id in users_dict:
        del users_dict[user_id]

    await db_connection.execute(
        "DELETE FROM users WHERE user_id = ?",
        (str(user_id),)
    )
    await db_connection.commit()


async def add_warning_to_user(user_id: str):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if user_id not in users_dict:
        await update_dict_from_db(user_id)

    if "Warnings" in users_dict[user_id]:
        users_dict[user_id]["Warnings"] += 1
    else:
        users_dict[user_id]["Warnings"] = 1

    await db_connection.execute(
        "UPDATE users SET warnings = warnings + 1 WHERE user_id = ?",
        (str(user_id),)
    )
    await db_connection.commit()
    return users_dict[user_id]["Warnings"]


async def reset_points(user_id: str, is_kicked=False):
    global db_connection, users_dict
    if db_connection is None:
        await init_database()

    if is_kicked and user_id in users_dict:
        del users_dict[user_id]
    if user_id in users_dict:
        users_dict[user_id]["Points"] = 0

    await db_connection.execute(
        "UPDATE users SET points = 0 WHERE user_id = ?",
        (str(user_id),)
    )
    await db_connection.commit()


# ====================== MIGRATIONS ======================
async def json_migration(users):
    global db_connection
    if db_connection is None:
        await init_database()

    batch = [(str(uid), data["points"]) for uid, data in users.items()]
    await db_connection.executemany(
        "INSERT OR REPLACE INTO users (user_id, points, warnings) VALUES (?, ?, 0)",
        batch
    )
    await db_connection.commit()


async def migrate_warnings():
    global db_connection
    if db_connection is None:
        await init_database()

    logging.basicConfig(filename='migration.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        with open('user_ids.json', 'r') as file:
            user_ids_json = json.load(file)
            
        for user_id, warnings in user_ids_json.items():
            async with db_connection.execute("UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id))) as cursor:
                if cursor.rowcount > 0:
                    logging.info(f"Updated user {user_id} with {warnings} warnings")
                else:
                    logging.warning(f"User {user_id} not found in the database")
        
        await db_connection.commit()
    except Exception as e:
        logging.error(f"Migration failed: {e}")


async def migrate_warnings_extreme(user_warnings):
    global db_connection

    if db_connection is None:
        await init_database()
        
    try:
        for user_id, warnings in user_warnings.items():
            async with db_connection.execute("SELECT * FROM users WHERE user_id = ?;", (str(user_id),)) as cur:
                existing_user = await cur.fetchone()

            if existing_user is not None:
                await db_connection.execute("UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id)))
                print(f"Updated warnings for user {user_id}")
            else:
                await db_connection.execute(
                    "INSERT INTO users (user_id, points, warnings, kicks) VALUES (?, ?, ?, ?);",
                    (str(user_id), 0, warnings, 0)
                )
                print(f"Inserted a new row for user {user_id}")
                
        await db_connection.commit()

    except Exception as e:
        print(f"An error occurred in extreme migration: {e}")


# Optional: graceful shutdown
async def close_database():
    global db_connection
    if db_connection:
        await db_connection.close()
        print("Database connection closed.")