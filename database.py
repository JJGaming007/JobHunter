"""
SQLite database — jobs + multi-user accounts + per-user tracking.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "jobs.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        # ── Users ──────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email        TEXT DEFAULT '',
                created_at   TEXT DEFAULT (datetime('now','localtime')),
                is_admin     INTEGER DEFAULT 0
            )
        """)

        # ── Per-user tracking (applied / opened per job per user) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_jobs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                job_id     INTEGER NOT NULL,
                opened     INTEGER DEFAULT 0,
                applied    INTEGER DEFAULT 0,
                apply_date TEXT,
                UNIQUE(user_id, job_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(job_id)  REFERENCES jobs(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                url           TEXT UNIQUE NOT NULL,
                title         TEXT,
                company       TEXT,
                location      TEXT,
                platform      TEXT,
                posted_date   TEXT,
                found_date    TEXT DEFAULT (datetime('now','localtime')),
                score         INTEGER DEFAULT 0,
                easy_apply    INTEGER DEFAULT 0,
                work_type     TEXT DEFAULT '',
                opened        INTEGER DEFAULT 0,
                email_sent    INTEGER DEFAULT 0,
                applied       INTEGER DEFAULT 0,
                apply_date    TEXT,
                apply_status  TEXT DEFAULT 'not_applied'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON jobs(url)")
        # Migrations for existing DBs
        for col_sql in [
            "ALTER TABLE jobs ADD COLUMN easy_apply INTEGER DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN work_type TEXT DEFAULT ''",
            "ALTER TABLE jobs ADD COLUMN country TEXT DEFAULT ''",
        ]:
            try:
                conn.execute(col_sql)
            except Exception:
                pass
        conn.commit()


class JobDatabase:
    def __init__(self):
        init_db()

    def is_seen(self, url: str) -> bool:
        with get_conn() as conn:
            row = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
            return row is not None

    def add_job(self, job: dict):
        with get_conn() as conn:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO jobs
                        (url, title, company, location, platform, posted_date, score, easy_apply, work_type, country)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.get("url", ""),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("platform", ""),
                    str(job.get("date_posted", "")),
                    job.get("score", 0),
                    1 if job.get("easy_apply") else 0,
                    job.get("work_type", ""),
                    job.get("country", ""),
                ))
                conn.commit()
            except Exception:
                pass

    def mark_opened(self, url: str):
        with get_conn() as conn:
            conn.execute("UPDATE jobs SET opened = 1 WHERE url = ?", (url,))
            conn.commit()

    def mark_email_sent(self, url: str):
        with get_conn() as conn:
            conn.execute("UPDATE jobs SET email_sent = 1 WHERE url = ?", (url,))
            conn.commit()

    def mark_applied(self, url: str, status: str = "applied"):
        with get_conn() as conn:
            conn.execute("""
                UPDATE jobs SET applied = 1, apply_status = ?, apply_date = datetime('now','localtime')
                WHERE url = ?
            """, (status, url))
            conn.commit()

    def count_applied_today(self) -> int:
        with get_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as cnt FROM jobs
                WHERE applied = 1
                AND date(apply_date) = date('now','localtime')
            """).fetchone()
            return row["cnt"] if row else 0

    def get_recent_jobs(self, limit: int = 50) -> list:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs ORDER BY found_date DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ── Per-user tracking ─────────────────────────────────
    def mark_opened_by_user(self, job_id: int, user_id: int):
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO user_jobs (user_id, job_id, opened)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, job_id) DO UPDATE SET opened=1
            """, (user_id, job_id))
            conn.commit()

    def mark_applied_by_user(self, job_id: int, user_id: int):
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO user_jobs (user_id, job_id, applied, apply_date)
                VALUES (?, ?, 1, datetime('now','localtime'))
                ON CONFLICT(user_id, job_id) DO UPDATE
                SET applied=1, apply_date=datetime('now','localtime')
            """, (user_id, job_id))
            conn.commit()

    def mark_unapplied_by_user(self, job_id: int, user_id: int):
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO user_jobs (user_id, job_id, applied)
                VALUES (?, ?, 0)
                ON CONFLICT(user_id, job_id) DO UPDATE SET applied=0, apply_date=NULL
            """, (user_id, job_id))
            conn.commit()

    def count_applied_today_by_user(self, user_id: int) -> int:
        with get_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as cnt FROM user_jobs
                WHERE user_id=? AND applied=1
                AND date(apply_date) = date('now','localtime')
            """, (user_id,)).fetchone()
            return row["cnt"] if row else 0


# ── User account helpers ───────────────────────────────────────────────────────

def create_user(username: str, password: str, email: str = "", is_admin: bool = False) -> bool:
    """Returns True if created, False if username already exists."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, email, is_admin) VALUES (?,?,?,?)",
                (username.strip(), generate_password_hash(password), email.strip(), 1 if is_admin else 0)
            )
            conn.commit()
        return True
    except Exception:
        return False


def verify_user(username: str, password: str):
    """Returns user dict on success, None on failure."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (username.strip(),)
        ).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def get_user_by_id(user_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT id,username,email,is_admin,created_at FROM users").fetchall()]
