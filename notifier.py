"""
Email notifier — sends a clean HTML digest of new jobs.
Uses Gmail SMTP with an App Password (2FA required on Gmail).
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import config

logger = logging.getLogger(__name__)

PLATFORM_COLORS = {
    "linkedin":     "#0A66C2",
    "indeed":       "#2164F3",
    "glassdoor":    "#0CAA41",
    "naukri":       "#ff7555",
    "hitmarker":    "#E8175D",
    "workwithindies": "#7B2FBE",
    "zip_recruiter": "#00A26B",
}

SCORE_COLORS = {
    (75, 101): "#16a34a",   # green  — great match
    (50, 75):  "#d97706",   # amber  — good match
    (0,  50):  "#6b7280",   # grey   — low match
}


def _score_color(score: int) -> str:
    for (lo, hi), color in SCORE_COLORS.items():
        if lo <= score < hi:
            return color
    return "#6b7280"


def _platform_badge(platform: str) -> str:
    color = PLATFORM_COLORS.get(platform.lower(), "#374151")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;">'
        f'{platform}</span>'
    )


def _job_card(job: dict) -> str:
    score     = job.get("score", 0)
    easy      = job.get("easy_apply", False)
    location  = job.get("location", "N/A")
    date_str  = job.get("date_posted", "")
    desc      = (job.get("description", "") or "")[:300].strip()
    if desc:
        desc += "..."

    easy_badge = (
        '<span style="background:#16a34a;color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:600;">⚡ EASY APPLY</span>'
        if easy else ""
    )

    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;
                margin-bottom:16px;font-family:Arial,sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
                <h3 style="margin:0 0 4px;font-size:16px;color:#111827;">
                    <a href="{job['url']}" style="color:#1d4ed8;text-decoration:none;">
                        {job.get('title','N/A')}
                    </a>
                </h3>
                <p style="margin:0;font-size:13px;color:#374151;">
                    🏢 {job.get('company','N/A')} &nbsp;|&nbsp; 📍 {location}
                    {f'&nbsp;|&nbsp; 📅 {date_str}' if date_str else ''}
                </p>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
                {_platform_badge(job.get('platform',''))}
                {easy_badge}
                <span style="background:{_score_color(score)};color:#fff;padding:2px 10px;
                             border-radius:4px;font-size:12px;font-weight:700;">
                    Score: {score}/100
                </span>
            </div>
        </div>
        {f'<p style="margin:10px 0 0;font-size:12px;color:#6b7280;line-height:1.5;">{desc}</p>' if desc else ''}
        <div style="margin-top:10px;">
            <a href="{job['url']}" style="background:#1d4ed8;color:#fff;padding:6px 14px;
               border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;">
               View &amp; Apply →
            </a>
        </div>
    </div>
    """


def build_html_email(jobs: list) -> str:
    total      = len(jobs)
    easy_count = sum(1 for j in jobs if j.get("easy_apply"))
    top_score  = jobs[0]["score"] if jobs else 0
    now        = datetime.now().strftime("%d %b %Y, %I:%M %p")

    cards = "".join(_job_card(j) for j in jobs)

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="background:#f3f4f6;margin:0;padding:20px;font-family:Arial,sans-serif;">
        <div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);">

            <!-- Header -->
            <div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);
                        padding:24px;color:#fff;text-align:center;">
                <h1 style="margin:0;font-size:22px;">🎮 Games QA Job Alert</h1>
                <p style="margin:6px 0 0;font-size:13px;opacity:.85;">{now}</p>
            </div>

            <!-- Stats bar -->
            <div style="display:flex;background:#eff6ff;padding:14px 24px;gap:24px;flex-wrap:wrap;">
                <div style="text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#1d4ed8;">{total}</div>
                    <div style="font-size:11px;color:#6b7280;text-transform:uppercase;">New Jobs</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#16a34a;">{easy_count}</div>
                    <div style="font-size:11px;color:#6b7280;text-transform:uppercase;">Easy Apply</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#d97706;">{top_score}</div>
                    <div style="font-size:11px;color:#6b7280;text-transform:uppercase;">Best Score</div>
                </div>
            </div>

            <!-- Job cards -->
            <div style="padding:20px 24px;">
                {cards}
            </div>

            <!-- Footer -->
            <div style="background:#f9fafb;padding:14px 24px;
                        border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;text-align:center;">
                Sent by Games QA Job Hunter &nbsp;|&nbsp; Running on your machine
            </div>
        </div>
    </body>
    </html>
    """


def send_job_notification(jobs: list, db=None):
    if not config.ENABLE_EMAIL:
        logger.info("Email disabled in config. Skipping notification.")
        return

    if not jobs:
        return

    subject = f"🎮 {len(jobs)} New Games QA Job{'s' if len(jobs) > 1 else ''} Found!"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = config.EMAIL_FROM
        msg["To"]      = config.EMAIL_TO

        html = build_html_email(jobs)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(config.EMAIL_FROM, config.EMAIL_APP_PASSWORD)
            server.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())

        logger.info(f"Email sent: {len(jobs)} jobs → {config.EMAIL_TO}")

        if db:
            for job in jobs:
                db.mark_email_sent(job["url"])

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        logger.error("Tip: Make sure you're using a Gmail App Password, not your login password.")
        logger.error("     Get one at: myaccount.google.com → Security → App passwords")
