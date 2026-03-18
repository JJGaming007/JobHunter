"""
Job scrapers:
  - python-jobspy  → LinkedIn, Indeed, Glassdoor
  - Naukri.com     → India's largest job portal
  - Hitmarker.net  → Games-industry specific board
  - WorkWithIndies → Indie game studios board
"""

import requests
import logging
import time
import random
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


# Ordered most-specific first so "new york" matches before ", us"
_COUNTRY_MAP = [
    ("united states", "USA"), ("u.s.a", "USA"), ("new york", "USA"),
    ("california", "USA"), ("texas", "USA"), ("washington", "USA"),
    ("chicago", "USA"), ("seattle", "USA"), ("san francisco", "USA"),
    ("los angeles", "USA"), ("boston", "USA"), ("austin", "USA"), (", us", "USA"),
    ("united kingdom", "UK"), ("u.k.", "UK"), ("london", "UK"),
    ("manchester", "UK"), ("edinburgh", "UK"), ("birmingham", "UK"),
    ("bengaluru", "India"), ("bangalore", "India"), ("gurugram", "India"),
    ("gurgaon", "India"), ("noida", "India"), ("pune", "India"),
    ("mumbai", "India"), ("hyderabad", "India"), ("chennai", "India"),
    ("delhi", "India"), ("india", "India"),
    ("toronto", "Canada"), ("vancouver", "Canada"), ("montreal", "Canada"),
    ("calgary", "Canada"), ("canada", "Canada"),
    ("sydney", "Australia"), ("melbourne", "Australia"), ("brisbane", "Australia"),
    ("australia", "Australia"),
    ("berlin", "Germany"), ("munich", "Germany"), ("hamburg", "Germany"),
    ("frankfurt", "Germany"), ("germany", "Germany"),
    ("paris", "France"), ("france", "France"),
    ("warsaw", "Poland"), ("krakow", "Poland"), ("poland", "Poland"),
    ("amsterdam", "Netherlands"), ("netherlands", "Netherlands"),
    ("stockholm", "Sweden"), ("sweden", "Sweden"),
    ("helsinki", "Finland"), ("finland", "Finland"),
    ("oslo", "Norway"), ("norway", "Norway"),
    ("singapore", "Singapore"),
    ("tokyo", "Japan"), ("osaka", "Japan"), ("japan", "Japan"),
    ("seoul", "South Korea"), ("south korea", "South Korea"), ("korea", "South Korea"),
    ("dubai", "UAE"), ("abu dhabi", "UAE"), ("uae", "UAE"),
    ("madrid", "Spain"), ("barcelona", "Spain"), ("spain", "Spain"),
    ("dublin", "Ireland"), ("ireland", "Ireland"),
    ("prague", "Czech Republic"), ("czech", "Czech Republic"),
    ("bucharest", "Romania"), ("romania", "Romania"),
    ("kyiv", "Ukraine"), ("ukraine", "Ukraine"),
    ("lisbon", "Portugal"), ("portugal", "Portugal"),
    ("milan", "Italy"), ("rome", "Italy"), ("italy", "Italy"),
    ("zurich", "Switzerland"), ("switzerland", "Switzerland"),
    ("tel aviv", "Israel"), ("israel", "Israel"),
    ("brussels", "Belgium"), ("belgium", "Belgium"),
    ("vienna", "Austria"), ("austria", "Austria"),
    ("sao paulo", "Brazil"), ("são paulo", "Brazil"), ("brazil", "Brazil"),
    ("mexico city", "Mexico"), ("mexico", "Mexico"),
]

def _extract_country(location: str) -> str:
    loc = (location or "").lower().strip()
    skip = {"remote", "worldwide", "global", "anywhere", "work from home", "wfh", ""}
    if loc in skip:
        return ""
    for kw, country in _COUNTRY_MAP:
        if kw in loc:
            return country
    # Fallback: last segment of "City, Country" if it looks like a country name
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        last = parts[-1].strip()
        if 2 < len(last) <= 25 and not any(c.isdigit() for c in last):
            return last.title()
    return ""


def _work_type(location: str, description: str) -> str:
    """Detect remote / hybrid / on-site from location + description text."""
    text = f"{location} {description}".lower()
    remote_kw  = {"remote", "work from home", "wfh", "fully remote", "100% remote", "anywhere"}
    hybrid_kw  = {"hybrid", "partially remote", "flexible location", "part remote"}
    if any(k in text for k in hybrid_kw):
        return "hybrid"
    if any(k in text for k in remote_kw):
        return "remote"
    return "on-site"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ─────────────────────────────────────────────
# 1. python-jobspy  (LinkedIn / Indeed / Glassdoor)
# ─────────────────────────────────────────────

def scrape_jobspy() -> list:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    jobs = []
    for title in config.JOB_TITLES[:6]:          # Limit to avoid rate-limits
        for location in config.SEARCH_LOCATIONS:
            try:
                logger.info(f"[JobSpy] Searching '{title}' in '{location}'...")
                df = scrape_jobs(
                    site_name=config.JOBSPY_PLATFORMS,
                    search_term=title,
                    location=location,
                    results_wanted=config.MAX_JOBS_PER_SEARCH,
                    hours_old=config.HOURS_OLD,
                    country_indeed="India",
                    linkedin_fetch_description=True,
                )
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        job = {
                            "title":       row.get("title", ""),
                            "company":     row.get("company", ""),
                            "location":    row.get("location", ""),
                            "url":         row.get("job_url", "") or row.get("job_url_direct", ""),
                            "description": row.get("description", ""),
                            "date_posted": str(row.get("date_posted", "")),
                            "platform":    row.get("site", "jobspy"),
                            "easy_apply":  bool(row.get("is_easy_apply", False)),
                            "work_type":   _work_type(
                                str(row.get("location", "") or ""),
                                str(row.get("description", "") or ""),
                            ),
                            "country": _extract_country(str(row.get("location", "") or "")),
                        }
                        if job["url"]:
                            jobs.append(job)
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.warning(f"[JobSpy] Error for '{title}' / '{location}': {e}")
    return jobs


# ─────────────────────────────────────────────
# 2. Naukri.com
# ─────────────────────────────────────────────

def scrape_naukri() -> list:
    jobs = []
    search_queries = ["games qa", "game tester", "gaming qa engineer", "qa games"]

    for query in search_queries:
        try:
            keyword_slug = query.replace(" ", "%20")
            url = (
                f"https://www.naukri.com/jobapi/v3/search"
                f"?noOfResults=20&urlType=search_by_key_loc"
                f"&searchType=adv&keyword={keyword_slug}"
                f"&experience={config.EXPERIENCE_YEARS}"
                f"&pageNo=1"
            )
            headers = {
                **HEADERS,
                "appid": "109",
                "systemid": "109",
                "Referer": "https://www.naukri.com/",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                job_list = data.get("jobDetails", [])
                for j in job_list:
                    jd_url = j.get("jdURL", "")
                    if not jd_url.startswith("http"):
                        jd_url = "https://www.naukri.com" + jd_url
                    jobs.append({
                        "title":       j.get("title", ""),
                        "company":     j.get("companyName", ""),
                        "location":    ", ".join(j.get("placeholders", [{}])[0].get("label", "").split(",")[:2]) if j.get("placeholders") else "",
                        "url":         jd_url,
                        "description": j.get("jobDescription", ""),
                        "date_posted": j.get("footerPlaceholderLabel", ""),
                        "platform":    "naukri",
                        "easy_apply":  False,
                    })
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.warning(f"[Naukri] Error for '{query}': {e}")

    return jobs


# ─────────────────────────────────────────────
# 3. Hitmarker.net  (games-industry jobs)
# ─────────────────────────────────────────────

def scrape_hitmarker() -> list:
    jobs = []
    search_terms = ["qa", "quality-assurance", "tester"]

    for term in search_terms:
        try:
            url = f"https://hitmarker.net/jobs?q={term}&category=quality-assurance"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("article.job-card, div.job-listing, li.job-item")

            # Fallback: try generic link extraction
            if not cards:
                cards = soup.select("a[href*='/jobs/']")
                for card in cards:
                    href = card.get("href", "")
                    if not href.startswith("http"):
                        href = "https://hitmarker.net" + href
                    title = card.get_text(strip=True)
                    if title and href:
                        jobs.append({
                            "title":       title,
                            "company":     "",
                            "location":    "Remote / Global",
                            "url":         href,
                            "description": "",
                            "date_posted": "",
                            "platform":    "hitmarker",
                            "easy_apply":  False,
                        })
            else:
                for card in cards:
                    title_el  = card.select_one(".job-title, h2, h3, .title")
                    company_el = card.select_one(".company, .employer")
                    loc_el    = card.select_one(".location, .place")
                    link_el   = card.select_one("a[href]") or card

                    href = link_el.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://hitmarker.net" + href

                    jobs.append({
                        "title":       title_el.get_text(strip=True) if title_el else "",
                        "company":     company_el.get_text(strip=True) if company_el else "",
                        "location":    loc_el.get_text(strip=True) if loc_el else "Remote",
                        "url":         href,
                        "description": "",
                        "date_posted": "",
                        "platform":    "hitmarker",
                        "easy_apply":  False,
                    })

            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.warning(f"[Hitmarker] Error: {e}")

    return [j for j in jobs if j["url"]]


# ─────────────────────────────────────────────
# 4. WorkWithIndies.com
# ─────────────────────────────────────────────

def scrape_workindie() -> list:
    jobs = []
    try:
        url = "https://www.workwithindies.com/jobs?search=qa+tester&type=all"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("a.job-listing, div.job-card a, li.listing a")

        for card in cards:
            href = card.get("href", "")
            if not href.startswith("http"):
                href = "https://www.workwithindies.com" + href
            title = card.get_text(strip=True)
            if title and href:
                jobs.append({
                    "title":       title,
                    "company":     "",
                    "location":    "Remote",
                    "url":         href,
                    "description": "",
                    "date_posted": "",
                    "platform":    "workwithindies",
                    "easy_apply":  False,
                })
    except Exception as e:
        logger.warning(f"[WorkWithIndies] Error: {e}")

    return jobs


# ─────────────────────────────────────────────
# Master scraper — calls all enabled sources
# ─────────────────────────────────────────────

def scrape_all_platforms() -> list:
    all_jobs = []

    logger.info(f"Scraping JobSpy platforms: {config.JOBSPY_PLATFORMS}...")
    all_jobs += scrape_jobspy()

    if config.ENABLE_NAUKRI:
        logger.info("Scraping Naukri.com...")
        all_jobs += scrape_naukri()

    if config.ENABLE_HITMARKER:
        logger.info("Scraping Hitmarker.net...")
        all_jobs += scrape_hitmarker()

    if config.ENABLE_WORKINDIE:
        logger.info("Scraping WorkWithIndies.com...")
        all_jobs += scrape_workindie()

    # Deduplicate: same URL OR same (title + company) pair
    # This removes the same job appearing from multiple search queries.
    seen_urls        = set()
    seen_fingerprints = set()
    unique = []

    for job in all_jobs:
        url = job.get("url", "").strip()
        title   = (job.get("title",   "") or "").lower().strip()
        company = (job.get("company", "") or "").lower().strip()
        fingerprint = f"{title}||{company}"

        # Clean HTML entities from title/company
        import html
        job["title"]   = html.unescape(job.get("title", "") or "")
        job["company"] = html.unescape(job.get("company", "") or "")
        # Stamp work_type if not already set by the scraper
        if not job.get("work_type"):
            job["work_type"] = _work_type(
                job.get("location", "") or "",
                job.get("description", "") or "",
            )
        if not job.get("country"):
            job["country"] = _extract_country(job.get("location", "") or "")

        if not url:
            continue
        if url in seen_urls:
            continue
        if company and fingerprint in seen_fingerprints:
            continue  # Same job from a different search query

        seen_urls.add(url)
        if company:
            seen_fingerprints.add(fingerprint)
        unique.append(job)

    logger.info(f"Total unique jobs scraped this cycle: {len(unique)}")
    return unique
