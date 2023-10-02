import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the database connection (async)
async def init_database():
    pool = await aiomysql.create_pool(
        host= os.getenv("DB_HOST"),
        port= os.getenv("PORT"),
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASSWORD"),
        db= os.getenv("DB_NAME"),
        autocommit=True,
        charset='utf8mb4',
        cursorclass=aiomysql.DictCursor,
    )
    print("Database connection established.")
    return pool

# Define your models and database interactions here