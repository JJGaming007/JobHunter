"""
Games QA Job Hunter — Web Dashboard + Scheduler
Run with: python app.py
Opens at:  http://127.0.0.1:5000

This single process runs BOTH the Flask GUI and the job-scraping scheduler.
No need for a second terminal.
"""

import sqlite3
import os
import sys
import json
import time
import threading
import webbrowser
import schedule as _schedule
from pathlib import Path
from flask import (Flask, render_template, jsonify, request,
                   Response, stream_with_context,
                   redirect, url_for, session, flash)
from flask_login import (LoginManager, UserMixin,
                         login_user, logout_user,
                         login_required, current_user)

# ── Path setup (so imports from this directory always work) ───────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

DB_PATH  = Path(os.environ.get("DB_PATH",  str(BASE_DIR / "jobs.db")))
LOG_PATH = Path(os.environ.get("LOG_PATH", str(BASE_DIR / "job_hunter.log")))

# ── Logging (must be configured before importing main) ────────────────────────
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("JobSpy").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

import config
from database import init_db, create_user, verify_user, get_user_by_id, list_users, JobDatabase
from main import run_job_hunt

# Run migrations + seed first admin if no users exist
init_db()
_db = JobDatabase()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

# ── Flask-Login ────────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message = ""

class User(UserMixin):
    def __init__(self, data: dict):
        self.id       = data["id"]
        self.username = data["username"]
        self.is_admin = bool(data.get("is_admin", 0))

@login_manager.user_loader
def load_user(user_id):
    data = get_user_by_id(int(user_id))
    return User(data) if data else None

# ── Scrape-running state ───────────────────────────────────────────────────────
_scrape_lock    = threading.Lock()
_scrape_running = False


def _tracked_run():
    """Wrapper that flips _scrape_running around run_job_hunt."""
    global _scrape_running
    with _scrape_lock:
        if _scrape_running:
            logger.info("Scrape already in progress — skipping this trigger.")
            return
        _scrape_running = True
    try:
        run_job_hunt()
    finally:
        _scrape_running = False


# ── Background scheduler thread ───────────────────────────────────────────────

def _scheduler_loop():
    logger.info(f"Scheduler started — running immediately, then every {config.CHECK_INTERVAL_MINUTES} min.")
    _tracked_run()                                                      # Run once on startup
    _schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(_tracked_run)
    while True:
        _schedule.run_pending()
        time.sleep(30)


_scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
_scheduler_thread.start()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=()):
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def execute(sql, params=()):
    with _conn() as c:
        c.execute(sql, params)
        c.commit()


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET","POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        user_data = verify_user(request.form["username"], request.form["password"])
        if user_data:
            login_user(User(user_data), remember=True)
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))


@app.route("/register", methods=["GET","POST"])
def register_page():
    # Only allow registration if no users exist, OR if current user is admin
    user_count = len(list_users())
    if user_count > 0 and (not current_user.is_authenticated or not current_user.is_admin):
        return redirect(url_for("login_page"))
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        email    = request.form.get("email","").strip()
        is_admin = user_count == 0  # First user is always admin
        if len(username) < 3 or len(password) < 6:
            error = "Username ≥ 3 chars and password ≥ 6 chars required."
        elif not create_user(username, password, email, is_admin):
            error = "Username already taken."
        else:
            logger.info(f"New user registered: {username} (admin={is_admin})")
            return redirect(url_for("login_page"))
    return render_template("register.html", error=error, first_user=(user_count==0))


# ── Main routes ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username, is_admin=current_user.is_admin)


@app.route("/api/stats")
@login_required
def api_stats():
    if not DB_PATH.exists():
        return jsonify({"total": 0, "today": 0, "easy_apply": 0,
                        "applied": 0, "best_score": 0,
                        "platforms": [], "work_types": [], "scraping": _scrape_running})

    rows = query("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN date(found_date) = date('now','localtime') THEN 1 ELSE 0 END) as today,
            SUM(easy_apply) as easy_apply,
            SUM(applied)    as applied,
            MAX(score)      as best_score
        FROM jobs
    """)
    stat = rows[0] if rows else {}

    platforms  = [r["platform"]  for r in query(
        "SELECT DISTINCT platform  FROM jobs WHERE platform  IS NOT NULL AND platform  != '' ORDER BY platform")]
    work_types = [r["work_type"] for r in query(
        "SELECT DISTINCT work_type FROM jobs WHERE work_type IS NOT NULL AND work_type != '' ORDER BY work_type")]
    countries = [r["country"] for r in query(
        "SELECT DISTINCT country FROM jobs WHERE country IS NOT NULL AND country != '' ORDER BY country")]

    return jsonify({
        "total":      stat.get("total", 0)      or 0,
        "today":      stat.get("today", 0)      or 0,
        "easy_apply": stat.get("easy_apply", 0) or 0,
        "applied":    stat.get("applied", 0)    or 0,
        "best_score": stat.get("best_score", 0) or 0,
        "platforms":  platforms,
        "work_types": work_types,
        "countries":  countries,
        "scraping":   _scrape_running,
    })


@app.route("/api/jobs")
@login_required
def api_jobs():
    if not DB_PATH.exists():
        return jsonify([])

    platform  = request.args.get("platform",  "").strip()
    work_type = request.args.get("work_type", "").strip()
    country   = request.args.get("country",   "").strip()
    min_score = int(request.args.get("min_score", 0))
    easy_only = request.args.get("easy_only", "false") == "true"
    applied   = request.args.get("applied", "")
    search    = request.args.get("search", "").strip().lower()
    sort_col  = request.args.get("sort", "score")
    sort_dir  = request.args.get("dir", "desc")

    allowed = {"score", "found_date", "title", "company", "platform", "work_type", "country", "id"}
    if sort_col not in allowed:
        sort_col = "score"
    sort_dir = "DESC" if sort_dir == "desc" else "ASC"

    where  = ["score >= ?"]
    params = [min_score]

    if platform:
        where.append("platform = ?")
        params.append(platform)
    if work_type:
        where.append("work_type = ?")
        params.append(work_type)
    if country:
        where.append("country = ?")
        params.append(country)
    if easy_only:
        where.append("easy_apply = 1")
    uid = current_user.id
    if applied == "yes":
        where.append("EXISTS (SELECT 1 FROM user_jobs uj WHERE uj.job_id=jobs.id AND uj.user_id=? AND uj.applied=1)")
        params.append(uid)
    elif applied == "no":
        where.append("NOT EXISTS (SELECT 1 FROM user_jobs uj WHERE uj.job_id=jobs.id AND uj.user_id=? AND uj.applied=1)")
        params.append(uid)
    if search:
        where.append("(LOWER(title) LIKE ? OR LOWER(company) LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    sql = f"""
        SELECT jobs.id, title, company, location, platform, work_type, country, score,
               easy_apply, found_date, posted_date, url,
               COALESCE(uj.applied, 0) as applied,
               COALESCE(uj.opened,  0) as opened
        FROM jobs
        LEFT JOIN user_jobs uj ON uj.job_id=jobs.id AND uj.user_id={uid}
        WHERE {' AND '.join(where)}
        ORDER BY {sort_col} {sort_dir}
        LIMIT 500
    """
    return jsonify(query(sql, params))


@app.route("/api/open/<int:job_id>", methods=["POST"])
@login_required
def api_open(job_id):
    rows = query("SELECT url FROM jobs WHERE id = ?", (job_id,))
    if not rows:
        return jsonify({"ok": False}), 404
    webbrowser.open(rows[0]["url"])
    _db.mark_opened_by_user(job_id, current_user.id)
    return jsonify({"ok": True})


@app.route("/api/mark-applied/<int:job_id>", methods=["POST"])
@login_required
def api_mark_applied(job_id):
    _db.mark_applied_by_user(job_id, current_user.id)
    return jsonify({"ok": True})


@app.route("/api/mark-unapplied/<int:job_id>", methods=["POST"])
@login_required
def api_mark_unapplied(job_id):
    _db.mark_unapplied_by_user(job_id, current_user.id)
    return jsonify({"ok": True})


@app.route("/api/run-now", methods=["POST"])
@login_required
def api_run_now():
    if _scrape_running:
        return jsonify({"status": "already_running"})
    threading.Thread(target=_tracked_run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/run-status")
@login_required
def api_run_status():
    return jsonify({"running": _scrape_running})


@app.route("/api/logs/stream")
@login_required
def api_logs_stream():
    def generate():
        if LOG_PATH.exists():
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for line in (lines[-80:] if len(lines) > 80 else lines):
                yield f"data: {json.dumps(line.rstrip())}\n\n"

        with open(LOG_PATH, "a+", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {json.dumps(line.rstrip())}\n\n"
                else:
                    yield ": keep-alive\n\n"
                    time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Launch ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  🎮  Games QA Job Hunter")
    print(f"  Dashboard : http://127.0.0.1:5000")
    print(f"  Scraping  : every {config.CHECK_INTERVAL_MINUTES} min (running now...)")
    print("  Stop      : Ctrl+C")
    print("=" * 55 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
