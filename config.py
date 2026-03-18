# ============================================================
# GAMES QA JOB HUNTER - CONFIGURATION
# Sensitive values are read from environment variables.
# Set these in Railway → Variables (or a local .env file).
# ============================================================

import os

# --- Your Profile ---
CANDIDATE_NAME   = os.environ.get("CANDIDATE_NAME",   "Jibin Jose")
EXPERIENCE_YEARS = int(os.environ.get("EXPERIENCE_YEARS", "4"))

SKILLS = [
    "Manual QA", "Game Testing", "Games QA", "Quality Assurance",
    "Unity", "Jira", "TestRail", "GitHub", "Firebase", "Crashlytics",
    "Bug Reporting", "Test Cases", "Regression Testing",
    "Functional Testing", "Mobile Testing", "iOS Testing", "Android Testing",
    "Test Plans", "Defect Tracking", "Smoke Testing", "Sanity Testing"
]

RESUME_PATH = os.environ.get("RESUME_PATH", "/app/data/resume.pdf")

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

HOURS_OLD            = int(os.environ.get("HOURS_OLD",            "48"))
MAX_JOBS_PER_SEARCH  = int(os.environ.get("MAX_JOBS_PER_SEARCH",  "25"))
MIN_RELEVANCE_SCORE  = int(os.environ.get("MIN_RELEVANCE_SCORE",  "30"))

# --- Keywords ---
BOOST_KEYWORDS = [
    "games", "gaming", "mobile game", "game studio", "unity",
    "unreal", "console", "pc game", "game development", "qa"
]

EXCLUDE_KEYWORDS = [
    "15+ years", "15 years", "12+ years", "12 years experience",
    "director of qa", "vp of qa", "head of qa", "unpaid", "intern only"
]

# --- Platforms ---
JOBSPY_PLATFORMS  = ["linkedin", "indeed"]
SEARCH_LOCATIONS  = ["India", "Remote", "Pune India"]

# --- Extra Scrapers ---
ENABLE_NAUKRI    = os.environ.get("ENABLE_NAUKRI",    "true").lower() == "true"
ENABLE_HITMARKER = os.environ.get("ENABLE_HITMARKER", "true").lower() == "true"
ENABLE_WORKINDIE = os.environ.get("ENABLE_WORKINDIE", "true").lower() == "true"

# --- Email Notifications ---
ENABLE_EMAIL       = os.environ.get("ENABLE_EMAIL", "true").lower() == "true"
EMAIL_FROM         = os.environ.get("EMAIL_FROM",         "jibinjosejo29@gmail.com")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.environ.get("EMAIL_TO",           "jibinjosejo29@gmail.com")
SMTP_SERVER        = os.environ.get("SMTP_SERVER",        "smtp.gmail.com")
SMTP_PORT          = int(os.environ.get("SMTP_PORT",      "587"))

# --- Browser Auto-Open ---
BROWSER_OPEN_TOP_N = int(os.environ.get("BROWSER_OPEN_TOP_N", "5"))

# --- LinkedIn Easy Apply ---
ENABLE_AUTO_APPLY      = os.environ.get("ENABLE_AUTO_APPLY", "false").lower() == "true"
LINKEDIN_EMAIL         = os.environ.get("LINKEDIN_EMAIL",    "jibinjosejo29@gmail.com")
LINKEDIN_PASSWORD      = os.environ.get("LINKEDIN_PASSWORD", "")
MAX_DAILY_APPLICATIONS = int(os.environ.get("MAX_DAILY_APPLICATIONS", "15"))
AUTO_APPLY_MIN_SCORE   = int(os.environ.get("AUTO_APPLY_MIN_SCORE",   "65"))
DRY_RUN                = os.environ.get("DRY_RUN", "true").lower() == "true"

# --- Scheduler ---
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "30"))
