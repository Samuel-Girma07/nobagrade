import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from config import DB_PATH

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                api_key TEXT NOT NULL,
                admin_message_id INTEGER,
                response_credit TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_admin_msg ON credit_requests(admin_message_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_id ON credit_requests(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_status ON credit_requests(status)"
        )
        await db.commit()

async def create_request(
    user_id: int, username: Optional[str], full_name: str, api_key: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO credit_requests (user_id, username, full_name, api_key, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (user_id, username, full_name, api_key),
        )
        await db.commit()
        return cursor.lastrowid

async def set_admin_message_id(request_id: int, admin_message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE credit_requests SET admin_message_id = ? WHERE id = ?",
            (admin_message_id, request_id),
        )
        await db.commit()

async def get_request_by_admin_message(admin_message_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM credit_requests WHERE admin_message_id = ?",
            (admin_message_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM credit_requests WHERE id = ?",
            (request_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def update_request_reply(
    request_id: int, response_credit: str
) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            """
            UPDATE credit_requests
            SET response_credit = ?, status = 'replied', replied_at = ?
            WHERE id = ?
            """,
            (response_credit, now_str, request_id),
        )
        await db.commit()

        async with db.execute(
            "SELECT * FROM credit_requests WHERE id = ?", (request_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_user_recent_requests(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM credit_requests
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_pending_requests(limit: int = 10) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM credit_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_stats() -> Dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM credit_requests") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM credit_requests WHERE status = 'pending'"
        ) as cursor:
            pending = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM credit_requests WHERE status = 'replied'"
        ) as cursor:
            replied = (await cursor.fetchone())[0]
        return {"total": total, "pending": pending, "replied": replied}
