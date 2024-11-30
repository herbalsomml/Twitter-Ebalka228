from datetime import datetime, timedelta

import aiosqlite

from functions.basic import add_message
from logic.classes import Account


async def create_database_and_table(account: Account, worker_name:str=None):
    add_message(f"Создаю БД...", account.screen_name, account.color, "log", worker_name)
    try: 
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS interactions (
                user_id INTEGER CHECK(user_id > 0) UNIQUE, -- Положительное число
                interaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Время взаимодействия
            );
            """
            await db.execute(create_table_query)
            await db.commit()

            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS tweet_interactions (
                tweet_id INTEGER CHECK(tweet_id > 0) UNIQUE
            );
            """
            await db.execute(create_table_query)
            await db.commit()

            return True

    except Exception as e:
        add_message(f"Ошибка при создании БД: {e}", account.screen_name, account.color, "success", worker_name)
        return False


async def create_shared_database(account:Account, worker_name:str=None):
    try:
        async with aiosqlite.connect(f"databases/bad_users.db") as db:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS bad_users (
                user_id INTEGER CHECK(user_id > 0) UNIQUE -- Положительное число
            );
            """
            await db.execute(create_table_query)
            await db.commit()
        return True
    
    except Exception as e:
        add_message(f"Ошибка при создании общей БД: {e}", account.screen_name, account.color, "success", worker_name)
        return False


async def add_or_update_user(account: Account, user_id: int, worker_name: str = None):
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            INSERT INTO interactions (user_id, interaction_time)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id)
            DO UPDATE SET interaction_time = CURRENT_TIMESTAMP;
            """
            await db.execute(query, (user_id,))
            await db.commit()
            return True
    except Exception as e:
        return False


async def has_enough_time_passed(account: Account, user_id: int, x_minutes: int, worker_name: str = None) -> bool:
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            SELECT interaction_time 
            FROM interactions 
            WHERE user_id = ?;
            """
            async with db.execute(query, (user_id,)) as cursor:
                result = await cursor.fetchone()
                
                if result is None:
                    return True
                
                last_interaction = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                time_difference = current_time - last_interaction
                
                if time_difference > timedelta(minutes=x_minutes):
                    return True
                else:
                    return False
    except Exception as e:
        return False


async def add_tweet_to_db(account, tweet_id: int):
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            INSERT OR IGNORE INTO tweet_interactions (tweet_id)
            VALUES (?)
            """
            await db.execute(query, (tweet_id,))
            await db.commit()
            return True
    except aiosqlite.Error as e:
        return False
    except Exception as e:
        return False


async def is_tweet_did(account, tweet_id: int) -> bool:
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            SELECT 1 
            FROM tweet_interactions 
            WHERE tweet_id = ?;
            """
            async with db.execute(query, (tweet_id,)) as cursor:
                result = await cursor.fetchone()
                return result is not None
    except Exception as e:
        return False


async def is_user_in_db(account: Account, user_id: int, worker_name: str = None) -> bool:
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            SELECT 1 
            FROM interactions 
            WHERE user_id = ?;
            """
            async with db.execute(query, (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result is not None:
                    return True
                else:
                    return False
    except Exception as e:
        return False


async def is_user_in_blacklist(account: Account, user_id: int, worker_name: str = None) -> bool:
    try:
        async with aiosqlite.connect(f"databases/bad_users.db") as db:
            query = """
            SELECT 1 
            FROM bad_users 
            WHERE user_id = ?;
            """
            async with db.execute(query, (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result is not None:
                    return True
                else:
                    return False
    except Exception as e:
        return False


async def block_user(account: Account, user_id: int):
    try:
        async with aiosqlite.connect(f"databases/{account.id}.db") as db:
            query = """
            INSERT OR IGNORE INTO bad_users (user_id)
            VALUES (?);
            """
            await db.execute(query, (user_id,))
            await db.commit()
            return True
    except Exception as e:
        return False
