# ============================================================
# GAMES QA JOB HUNTER - CONFIGURATION
# Non-sensitive settings live here.
# Passwords/secrets go in .env (never committed to git).
# ============================================================

import os

# --- Your Profile ---
CANDIDATE_NAME   = "Jibin Jose"
EXPERIENCE_YEARS = 4

SKILLS = [
    "Manual QA", "Game Testing", "Games QA", "Quality Assurance",
    "Unity", "Jira", "TestRail", "GitHub", "Firebase", "Crashlytics",
    "Bug Reporting", "Test Cases", "Regression Testing",
    "Functional Testing", "Mobile Testing", "iOS Testing", "Android Testing",
    "Test Plans", "Defect Tracking", "Smoke Testing", "Sanity Testing"
]

# Absolute path to your resume PDF
RESUME_PATH = os.environ.get("RESUME_PATH", r"D:\Automation\job_hunter\resume.pdf")

# --- Job Search Settings ---
JOB_TITLES = [
    "Games QA Engineer",
    "Game QA Engineer",
    "QA Engineer Games",
    "Game Tester",
    "Games Tester",
    "Quality Assurance Games",
    "Mobile Games QA",
    "QA Analyst Games",
    "Game Quality Assurance",
    "QA Tester Games",
    "QA Lead Games",
    "Senior QA Games",
]

# Jobs posted within these many hours will be fetched
HOURS_OLD = 48

# Max jobs fetched per search query per platform
MAX_JOBS_PER_SEARCH = 25

# Jobs with relevance score below this will be silently ignored (0–100)
MIN_RELEVANCE_SCORE = 30

# --- Keywords ---
BOOST_KEYWORDS = [
    "games", "gaming", "mobile game", "game studio", "unity",
    "unreal", "console", "pc game", "game development", "qa"
]

EXCLUDE_KEYWORDS = [
    "15+ years", "15 years", "12+ years", "12 years experience",
    "director of qa", "vp of qa", "head of qa", "unpaid", "intern only"
]

# --- Platforms via python-jobspy ---
JOBSPY_PLATFORMS = ["linkedin", "indeed"]  # glassdoor removed — blocks scrapers

# Locations to search (one search per title per location)
SEARCH_LOCATIONS = ["India", "Remote", "Pune India"]

# --- Extra Scrapers ---
ENABLE_NAUKRI    = True
ENABLE_HITMARKER = True
ENABLE_WORKINDIE = True

# --- Email Notifications ---
ENABLE_EMAIL       = True
EMAIL_FROM         = os.environ.get("EMAIL_FROM",         "")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.environ.get("EMAIL_TO",           "")
SMTP_SERVER        = "smtp.gmail.com"
SMTP_PORT          = 587

# --- Browser Auto-Open ---
BROWSER_OPEN_TOP_N = 5

# --- LinkedIn Easy Apply (Auto-Apply) ---
ENABLE_AUTO_APPLY      = False
LINKEDIN_EMAIL         = os.environ.get("LINKEDIN_EMAIL",    "")
LINKEDIN_PASSWORD      = os.environ.get("LINKEDIN_PASSWORD", "")
MAX_DAILY_APPLICATIONS = 15
AUTO_APPLY_MIN_SCORE   = 65
DRY_RUN                = True

# --- Scheduler ---
CHECK_INTERVAL_MINUTES = 30
