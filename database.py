"""
PostgreSQL database — jobs + multi-user accounts + per-user tracking.
Reads DATABASE_URL from the environment (set automatically by Railway PostgreSQL).
"""

import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash

_raw_url = os.environ.get("DATABASE_URL", "")
# psycopg2 requires postgresql:// not postgres://
DATABASE_URL = _raw_url.replace("postgres://", "postgresql://", 1) if _raw_url.startswith("postgres://") else _raw_url


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def _q(sql, params=(), fetch=True):
    """Run a query and optionally return rows as dicts."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch:
                    return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return []


def _x(sql, params=()):
    """Execute a write statement."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id            SERIAL PRIMARY KEY,
                        username      TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        email         TEXT DEFAULT '',
                        created_at    TIMESTAMP DEFAULT NOW(),
                        is_admin      INTEGER DEFAULT 0
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id           SERIAL PRIMARY KEY,
                        url          TEXT UNIQUE NOT NULL,
                        title        TEXT,
                        company      TEXT,
                        location     TEXT,
                        platform     TEXT,
                        posted_date  TEXT,
                        found_date   TIMESTAMP DEFAULT NOW(),
                        score        INTEGER DEFAULT 0,
                        easy_apply   INTEGER DEFAULT 0,
                        work_type    TEXT DEFAULT '',
                        country      TEXT DEFAULT '',
                        opened       INTEGER DEFAULT 0,
                        email_sent   INTEGER DEFAULT 0,
                        applied      INTEGER DEFAULT 0,
                        apply_date   TIMESTAMP,
                        apply_status TEXT DEFAULT 'not_applied'
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_jobs (
                        id         SERIAL PRIMARY KEY,
                        user_id    INTEGER NOT NULL REFERENCES users(id),
                        job_id     INTEGER NOT NULL REFERENCES jobs(id),
                        opened     INTEGER DEFAULT 0,
                        applied    INTEGER DEFAULT 0,
                        apply_date TIMESTAMP,
                        UNIQUE(user_id, job_id)
                    )
                """)
    finally:
        conn.close()


class JobDatabase:
    def __init__(self):
        init_db()

    def is_seen(self, url: str) -> bool:
        rows = _q("SELECT id FROM jobs WHERE url = %s", (url,))
        return len(rows) > 0

    def add_job(self, job: dict):
        _x("""
            INSERT INTO jobs
                (url, title, company, location, platform, posted_date, score, easy_apply, work_type, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
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

    def mark_opened(self, url: str):
        _x("UPDATE jobs SET opened = 1 WHERE url = %s", (url,))

    def mark_email_sent(self, url: str):
        _x("UPDATE jobs SET email_sent = 1 WHERE url = %s", (url,))

    def mark_applied(self, url: str, status: str = "applied"):
        _x("""
            UPDATE jobs SET applied = 1, apply_status = %s, apply_date = NOW()
            WHERE url = %s
        """, (status, url))

    def count_applied_today(self) -> int:
        rows = _q("""
            SELECT COUNT(*) AS cnt FROM jobs
            WHERE applied = 1 AND apply_date::date = CURRENT_DATE
        """)
        return rows[0]["cnt"] if rows else 0

    def get_recent_jobs(self, limit: int = 50) -> list:
        return _q("SELECT * FROM jobs ORDER BY found_date DESC LIMIT %s", (limit,))

    # ── Per-user tracking ─────────────────────────────────

    def mark_opened_by_user(self, job_id: int, user_id: int):
        _x("""
            INSERT INTO user_jobs (user_id, job_id, opened)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, job_id) DO UPDATE SET opened = 1
        """, (user_id, job_id))

    def mark_applied_by_user(self, job_id: int, user_id: int):
        _x("""
            INSERT INTO user_jobs (user_id, job_id, applied, apply_date)
            VALUES (%s, %s, 1, NOW())
            ON CONFLICT (user_id, job_id) DO UPDATE SET applied = 1, apply_date = NOW()
        """, (user_id, job_id))

    def mark_unapplied_by_user(self, job_id: int, user_id: int):
        _x("""
            INSERT INTO user_jobs (user_id, job_id, applied)
            VALUES (%s, %s, 0)
            ON CONFLICT (user_id, job_id) DO UPDATE SET applied = 0, apply_date = NULL
        """, (user_id, job_id))

    def count_applied_today_by_user(self, user_id: int) -> int:
        rows = _q("""
            SELECT COUNT(*) AS cnt FROM user_jobs
            WHERE user_id = %s AND applied = 1 AND apply_date::date = CURRENT_DATE
        """, (user_id,))
        return rows[0]["cnt"] if rows else 0


# ── User account helpers ───────────────────────────────────────────────────────

def create_user(username: str, password: str, email: str = "", is_admin: bool = False) -> bool:
    try:
        _x(
            "INSERT INTO users (username, password_hash, email, is_admin) VALUES (%s, %s, %s, %s)",
            (username.strip(), generate_password_hash(password), email.strip(), 1 if is_admin else 0)
        )
        return True
    except Exception:
        return False


def verify_user(username: str, password: str):
    rows = _q("SELECT * FROM users WHERE username = %s", (username.strip(),))
    if rows and check_password_hash(rows[0]["password_hash"], password):
        return rows[0]
    return None


def get_user_by_id(user_id: int):
    rows = _q("SELECT * FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None


def list_users():
    return _q("SELECT id, username, email, is_admin, created_at FROM users")
