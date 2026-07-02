import sqlite3
from contextlib import closing
from datetime import datetime

from config import DB_PATH


def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                added_by INTEGER,
                created_at TEXT,
                last_status TEXT DEFAULT 'unknown',
                last_code INTEGER,
                last_response_time REAL,
                last_checked_at TEXT,
                last_error TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                status TEXT,
                code INTEGER,
                response_time REAL,
                error TEXT,
                checked_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                user_id INTEGER PRIMARY KEY,
                phone TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                registered_at TEXT
            )
        """)


def add_project(name: str, url: str, added_by: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cur = conn.execute(
            "INSERT INTO projects (name, url, added_by, created_at) VALUES (?, ?, ?, ?)",
            (name, url, added_by, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def remove_project(project_id: int) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.execute("DELETE FROM check_history WHERE project_id = ?", (project_id,))
        return cur.rowcount > 0


def list_projects():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM projects ORDER BY id").fetchall()


def get_project(project_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return "+" + digits if digits else phone


def save_contact(user_id: int, phone: str, first_name: str, last_name: str, username: str):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(
            """INSERT INTO contacts (user_id, phone, first_name, last_name, username, registered_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   phone = excluded.phone,
                   first_name = excluded.first_name,
                   last_name = excluded.last_name,
                   username = excluded.username""",
            (user_id, _normalize_phone(phone), first_name, last_name, username,
             datetime.utcnow().isoformat()),
        )


def get_user_id_by_phone(phone: str):
    norm = _normalize_phone(phone)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM contacts WHERE phone = ?", (norm,)).fetchone()
        return row


def list_contacts():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM contacts ORDER BY registered_at").fetchall()


def update_project_status(project_id: int, status: str, code, response_time, error):
    now = datetime.utcnow().isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(
            """UPDATE projects
               SET last_status = ?, last_code = ?, last_response_time = ?,
                   last_checked_at = ?, last_error = ?
               WHERE id = ?""",
            (status, code, response_time, now, error, project_id),
        )
        conn.execute(
            """INSERT INTO check_history (project_id, status, code, response_time, error, checked_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, status, code, response_time, error, now),
