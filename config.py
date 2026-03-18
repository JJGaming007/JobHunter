# ============================================================
# GAMES QA JOB HUNTER - CONFIGURATION
# Edit this file before running main.py
# ============================================================

# --- Your Profile ---
CANDIDATE_NAME = "Jibin Jose"
EXPERIENCE_YEARS = 4

SKILLS = [
    "Manual QA", "Game Testing", "Games QA", "Quality Assurance",
    "Unity", "Jira", "TestRail", "GitHub", "Firebase", "Crashlytics",
    "Bug Reporting", "Test Cases", "Regression Testing",
    "Functional Testing", "Mobile Testing", "iOS Testing", "Android Testing",
    "Test Plans", "Defect Tracking", "Smoke Testing", "Sanity Testing"
]

# Absolute path to your resume PDF
RESUME_PATH = r"D:\Automation\job_hunter\resume.pdf"

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
# Jobs containing ANY of these will get a bonus score
BOOST_KEYWORDS = [
    "games", "gaming", "mobile game", "game studio", "unity",
    "unreal", "console", "pc game", "game development", "qa"
]

# Jobs containing ANY of these will be skipped entirely
EXCLUDE_KEYWORDS = [
    "15+ years", "15 years", "12+ years", "12 years experience",
    "director of qa", "vp of qa", "head of qa", "unpaid", "intern only"
]

# --- Platforms via python-jobspy ---
# Options: "linkedin", "indeed", "glassdoor", "zip_recruiter", "google"
JOBSPY_PLATFORMS = ["linkedin", "indeed"]  # Glassdoor removed — blocks scrapers

# Locations to search (runs one search per title per location)
SEARCH_LOCATIONS = ["India", "Remote", "Pune India"]

# --- Extra Scrapers ---
ENABLE_NAUKRI    = True   # Naukri.com  (India's biggest job portal)
ENABLE_HITMARKER = True   # Hitmarker.net (games-specific board)
ENABLE_WORKINDIE = True   # WorkWithIndies.com

# --- Email Notifications ---
ENABLE_EMAIL     = True
EMAIL_FROM       = "jibinjosejo29@gmail.com"      # ← change this
EMAIL_APP_PASSWORD = "iznr lmho sodh wdzm"     # ← Gmail App Password (not your login password)
EMAIL_TO         = "jibinjosejo29@gmail.com"      # ← where to send alerts
SMTP_SERVER      = "smtp.gmail.com"
SMTP_PORT        = 587

# --- Browser Auto-Open ---
# Automatically opens top N jobs in your browser when new ones are found
BROWSER_OPEN_TOP_N = 5

# --- LinkedIn Easy Apply (Auto-Apply) ---
# WARNING: Use at own risk. LinkedIn can flag automated activity.
# Recommended: Keep False and use browser auto-open instead.
ENABLE_AUTO_APPLY     = False
LINKEDIN_EMAIL        = "jibinjosejo29@gmail.com"
LINKEDIN_PASSWORD     = "Jibinjose007"
MAX_DAILY_APPLICATIONS = 15          # Hard cap per day
AUTO_APPLY_MIN_SCORE  = 65           # Only apply to very relevant jobs
DRY_RUN               = True         # True = fills form but does NOT click Submit (safe test mode)

# --- Scheduler ---
CHECK_INTERVAL_MINUTES = 30   # How often to check for new jobs
