import aiomysql
from config import DATABASE_URI

# Initialize the database connection (async)
async def init_database():
    pool = await aiomysql.create_pool(
        host='localhost',
        port=3306,
        user='your_username',
        password='your_password',
        db='your_database',
        autocommit=True,
        charset='utf8mb4',
        cursorclass=aiomysql.DictCursor,
    )
    print("Database connection established.")
    return pool

# Define your models and database interactions here