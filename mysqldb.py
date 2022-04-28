import aiomysql
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

loop = asyncio.get_event_loop()

async def the_database():
    pool = await aiomysql.create_pool(
        host=os.getenv("SLOTH_DB_HOST"),
        user=os.getenv("SLOTH_DB_USER"),
        password=os.getenv("SLOTH_DB_PASSWORD"),
        db=os.getenv("SLOTH_DB_NAME"), loop=loop)
    db = await pool.acquire()
    mycursor = await db.cursor()
    return mycursor, db