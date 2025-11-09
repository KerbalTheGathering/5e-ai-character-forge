import sqlite3
from datetime import datetime
from .config import DB_PATH, logger
from typing import Any

def get_db_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db_connection()
    cur = con.cursor()
    # Character library
    cur.execute("""
    CREATE TABLE IF NOT EXISTS library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      draft_json TEXT NOT NULL,
      backstory_json TEXT,
      portrait_png BLOB,
      progression_json TEXT
    )
    """)
    # ensure portrait column exists for older DBs
    try:
        cur.execute("ALTER TABLE library ADD COLUMN portrait_png BLOB")
        con.commit()
        logger.info("Added portrait_png column to library table.")
    except sqlite3.OperationalError:
        pass # column already exists
    # ensure progression column exists for older DBs
    try:
        cur.execute("ALTER TABLE library ADD COLUMN progression_json TEXT")
        con.commit()
        logger.info("Added progression_json column to library table.")
    except sqlite3.OperationalError:
        pass # column already exists

    # Magic item library
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      item_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    # Spell library
    cur.execute("""
    CREATE TABLE IF NOT EXISTS spell_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      spell_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    # Progression plans library
    cur.execute("""
    CREATE TABLE IF NOT EXISTS progression_library (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT NOT NULL,
      plan_json TEXT NOT NULL,
      prompt TEXT
    )
    """)
    con.commit()
    con.close()
    logger.info("Database initialized.")


init_db()

# Generic CRUD operations
def create_item(table_name: str, item_data: dict) -> dict:
    con = get_db_connection()
    cur = con.cursor()
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    item_data["created_at"] = created_at

    columns = ", ".join(item_data.keys())
    placeholders = ", ".join(["?"] * len(item_data))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cur.execute(query, tuple(item_data.values()))
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return {"id": new_id, "name": item_data.get("name"), "created_at": created_at}

def get_item(table_name: str, item_id: int) -> sqlite3.Row | None:
    con = get_db_connection()
    row = con.execute(f"SELECT * FROM {table_name} WHERE id = ?", (item_id,)).fetchone()
    con.close()
    return row

def list_items(table_name: str, limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc") -> dict[str, Any]:
    con = get_db_connection()
    q_base = f"FROM {table_name}"
    params: list[object] = []
    if search:
        q_base += " WHERE name LIKE ?"
        params.append(f"%{search}%")
    total = con.execute(f"SELECT COUNT(*) {q_base}", params).fetchone()[0]
    sort_map = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "created_asc": "created_at ASC",
        "created_desc": "created_at DESC",
    }
    order_sql = sort_map.get(sort, "created_at DESC")
    offset = max(0, (page-1) * limit)
    rows = con.execute(
        f"SELECT id, name, created_at {q_base} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        (*params, limit, offset)
    ).fetchall()
    con.close()
    return {"items": [dict(r) for r in rows], "total": total}

def delete_item(table_name: str, item_id: int) -> int:
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
    con.commit()
    deleted = cur.rowcount
    con.close()
    return deleted
