import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

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

# Define your models and database interactions here