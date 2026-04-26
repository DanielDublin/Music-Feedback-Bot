import aiosqlite
import os
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

DATABASE_ERROR = -2
_WEEK = 60 * 60 * 24 * 7


class Database:
    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None
        self.users_dict: dict[str, dict] = {}

    # ── connection ──────────────────────────────────────────────────────────

    async def init_database(self) -> None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        db_filename = os.environ.get("DB_NAME", "MF_DB.db")
        db_file = os.path.join(data_dir, db_filename)

        self._conn = await aiosqlite.connect(db_file)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA busy_timeout=5000;")
        await self._conn.commit()

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                kicks INTEGER DEFAULT 0
            )
        """)
        await self._conn.commit()
        logger.info("SQLite database connected (WAL mode) at: %s", db_file)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed.")

    def _ensure_connected(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.init_database() has not been called.")
        return self._conn

    # ── weekly cache reset ───────────────────────────────────────────────────

    async def schedule_weekly_task(self) -> None:
        while True:
            await asyncio.sleep(_WEEK)
            self.users_dict.clear()

    # ── internal ─────────────────────────────────────────────────────────────

    async def _update_dict_from_db(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        self.users_dict[user_id] = {}
        async with conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()

        if result:
            self.users_dict[user_id]["Points"] = int(result["points"])
            self.users_dict[user_id]["Warnings"] = int(result["warnings"])
            self.users_dict[user_id]["Kicks"] = int(result["kicks"])
        else:
            del self.users_dict[user_id]
            await self.add_user(user_id, called_from_update_func=True)
            self.users_dict[user_id] = {"Points": 0, "Warnings": 0, "Kicks": 0}

    async def _fetch_rank_from_db(self, user_id: str) -> aiosqlite.Row | None:
        conn = self._ensure_connected()
        query = """
            SELECT (SELECT COUNT(*) + 1
                    FROM users AS u
                    WHERE u.points > (SELECT points FROM users WHERE user_id = ?)) AS Rank_value
        """
        async with conn.execute(query, (str(user_id),)) as cursor:
            return await cursor.fetchone()

    # ── read ──────────────────────────────────────────────────────────────────

    async def fetch_points(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Points" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Points"]
        if user_id in self.users_dict:
            del self.users_dict[user_id]
        await self._update_dict_from_db(user_id)
        return self.users_dict[user_id]["Points"]

    async def fetch_rank(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Rank" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Rank"]
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        result = await self._fetch_rank_from_db(user_id)
        if result and result["Rank_value"] is not None:
            self.users_dict[user_id]["Rank"] = result["Rank_value"]
            return result["Rank_value"]
        return DATABASE_ERROR

    async def fetch_kicks(self, user_id: str) -> int:
        user_id = str(user_id)
        if user_id in self.users_dict and "Kicks" in self.users_dict[user_id]:
            return self.users_dict[user_id]["Kicks"]
        await self._update_dict_from_db(user_id)
        return self.users_dict[user_id]["Kicks"]

    async def top_10(self) -> list:
        conn = self._ensure_connected()
        async with conn.execute(
            "SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10"
        ) as cursor:
            return await cursor.fetchall()

    async def fetch_top_users(self) -> dict:
        conn = self._ensure_connected()
        async with conn.execute(
            "SELECT user_id, points FROM users ORDER BY points DESC LIMIT 5"
        ) as cursor:
            top_users = await cursor.fetchall()
        return {
            user["user_id"]: {"points": user["points"], "rank": i}
            for i, user in enumerate(top_users, start=1)
        }

    # ── write ─────────────────────────────────────────────────────────────────

    async def add_points(self, user_id: str, points: int) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] += points
        await conn.execute(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points, user_id)
        )
        await conn.commit()

    async def reduce_points(self, user_id: str, points: int) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] -= points
        await conn.execute(
            "UPDATE users SET points = points - ? WHERE user_id = ?",
            (points, user_id)
        )
        await conn.commit()

    async def reset_points(self, user_id: str, is_kicked: bool = False) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if is_kicked and user_id in self.users_dict:
            del self.users_dict[user_id]
        if user_id in self.users_dict:
            self.users_dict[user_id]["Points"] = 0
        await conn.execute(
            "UPDATE users SET points = 0 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_user(self, user_id: str, called_from_update_func: bool = False) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            self.users_dict[user_id] = {}
        await conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await conn.commit()
        if not called_from_update_func:
            await self._update_dict_from_db(user_id)

    async def remove_user(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        self.users_dict.pop(user_id, None)
        await conn.execute(
            "DELETE FROM users WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_kick(self, user_id: str) -> None:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        self.users_dict[user_id]["Kicks"] = self.users_dict[user_id].get("Kicks", 0) + 1
        await conn.execute(
            "UPDATE users SET kicks = kicks + 1 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()

    async def add_warning_to_user(self, user_id: str) -> int:
        conn = self._ensure_connected()
        user_id = str(user_id)
        if user_id not in self.users_dict:
            await self._update_dict_from_db(user_id)
        self.users_dict[user_id]["Warnings"] = self.users_dict[user_id].get("Warnings", 0) + 1
        await conn.execute(
            "UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,)
        )
        await conn.commit()
        return self.users_dict[user_id]["Warnings"]

    # ── migrations ─────────────────────────────────────────────────────────────

    async def json_migration(self, users: dict) -> None:
        conn = self._ensure_connected()
        batch = [(str(uid), data["points"]) for uid, data in users.items()]
        await conn.executemany(
            "INSERT OR REPLACE INTO users (user_id, points, warnings) VALUES (?, ?, 0)",
            batch
        )
        await conn.commit()

    async def migrate_warnings(self) -> None:
        conn = self._ensure_connected()
        try:
            with open('user_ids.json', 'r') as file:
                user_ids_json = json.load(file)
            for user_id, warnings in user_ids_json.items():
                async with conn.execute(
                    "UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id))
                ) as cursor:
                    if cursor.rowcount > 0:
                        logger.info("Updated user %s with %d warnings", user_id, warnings)
                    else:
                        logger.warning("User %s not found in the database", user_id)
            await conn.commit()
        except Exception:
            logger.error("migrate_warnings failed", exc_info=True)

    async def migrate_warnings_extreme(self, user_warnings: dict) -> None:
        conn = self._ensure_connected()
        try:
            for user_id, warnings in user_warnings.items():
                async with conn.execute(
                    "SELECT * FROM users WHERE user_id = ?;", (str(user_id),)
                ) as cur:
                    existing_user = await cur.fetchone()
                if existing_user is not None:
                    await conn.execute(
                        "UPDATE users SET warnings = ? WHERE user_id = ?;", (warnings, str(user_id))
                    )
                    logger.info("Updated warnings for user %s", user_id)
                else:
                    await conn.execute(
                        "INSERT INTO users (user_id, points, warnings, kicks) VALUES (?, ?, ?, ?);",
                        (str(user_id), 0, warnings, 0)
                    )
                    logger.info("Inserted new row for user %s", user_id)
            await conn.commit()
        except Exception:
            logger.error("migrate_warnings_extreme failed", exc_info=True)
