"""
Relevance scoring engine.
Scores each job 0–100 based on how well it matches the Games QA profile.
"""

from config import SKILLS, BOOST_KEYWORDS, EXCLUDE_KEYWORDS, EXPERIENCE_YEARS


def score_job(job: dict) -> int:
    title    = (job.get("title", "") or "").lower()
    desc     = (job.get("description", "") or "").lower()
    company  = (job.get("company", "") or "").lower()
    location = (job.get("location", "") or "").lower()
    full_text = f"{title} {desc} {company} {location}"

    score = 0

    # Hard disqualify on excluded keywords
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in full_text:
            return 0

    # Title match (most important)
    title_hits = [kw for kw in [
        "qa", "quality assurance", "tester", "test engineer",
        "game", "games", "gaming"
    ] if kw in title]
    score += min(len(title_hits) * 15, 45)

    # Exact "games qa" / "game qa" in title — big bonus
    if any(phrase in title for phrase in ["game qa", "games qa", "qa games", "game test", "games test"]):
        score += 20

    # Skills match in description
    skill_hits = sum(1 for s in SKILLS if s.lower() in full_text)
    score += min(skill_hits * 4, 20)

    # Boost keywords in description
    boost_hits = sum(1 for kw in BOOST_KEYWORDS if kw in full_text)
    score += min(boost_hits * 3, 15)

    # Remote / India location bonus
    if any(kw in location for kw in ["india", "remote", "pune", "anywhere"]):
        score += 5

    # Experience range check (penalize if clearly out of range)
    for marker in ["10+ years", "10 years", "8+ years", "8 years", "7+ years"]:
        if marker in full_text:
            score -= 20
            break

    return max(0, min(score, 100))


def score_jobs(jobs: list) -> list:
    for job in jobs:
        job["score"] = score_job(job)
    return sorted(jobs, key=lambda x: x["score"], reverse=True)
