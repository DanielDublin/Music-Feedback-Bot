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



#fetch_points, fetch_rank, reduce_points, add_points, fetch_top_users, add_user, remove_user

async def fetch_points(user_id : int):
    a=0

async def fetch_rank(user_id : int):
    a=0  

async def fetch_top_users():
    a=0  
    
async def reduce_points(user_id:int, points : int):
    a=0    
    
async def add_points(user_id:int, points : int):
    a=0      

async def add_user(user_id):
    a=0      

async def remove_user(user_id):
    a=0      

async def reset_points(user_id):
    a=0  

    

    
