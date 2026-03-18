"""
LinkedIn Easy Apply Bot
━━━━━━━━━━━━━━━━━━━━━━
Automates LinkedIn Easy Apply for relevant jobs.

IMPORTANT:
  - Set ENABLE_AUTO_APPLY = True in config.py to use this.
  - Start with DRY_RUN = True to preview without actually submitting.
  - LinkedIn may flag automated activity. Use reasonable MAX_DAILY_APPLICATIONS.
  - Requires Chrome to be installed on your machine.
"""

import time
import logging
import os
import random
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, ElementNotInteractableException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def _wait(lo=1.5, hi=3.0):
    time.sleep(random.uniform(lo, hi))


def _get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    # Uncomment to run headless (no visible browser window):
    # options.add_argument("--headless=new")
    driver = uc.Chrome(options=options)
    return driver


def _login(driver, email: str, password: str) -> bool:
    try:
        driver.get("https://www.linkedin.com/login")
        wait = WebDriverWait(driver, 15)

        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        _wait(3, 5)

        if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
            logger.warning("LinkedIn security checkpoint detected!")
            logger.warning("Please solve it manually in the browser window. Waiting 60s...")
            time.sleep(60)

        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            logger.info("LinkedIn login successful.")
            return True

        logger.error(f"Login may have failed. Current URL: {driver.current_url}")
        return False
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


def _fill_text_field(driver, element, value: str):
    try:
        element.clear()
        _wait(0.2, 0.5)
        for char in value:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.07))
    except Exception:
        pass


def _handle_form_field(driver, field, profile: dict):
    """Try to intelligently fill a single form field."""
    try:
        tag  = field.tag_name.lower()
        label_text = ""

        # Find associated label
        try:
            fid = field.get_attribute("id")
            if fid:
                labels = driver.find_elements(By.XPATH, f"//label[@for='{fid}']")
                if labels:
                    label_text = labels[0].text.lower()
        except Exception:
            pass

        if tag in ("input", "textarea"):
            input_type = (field.get_attribute("type") or "text").lower()

            if input_type in ("text", "email", "tel", "number", ""):
                current_val = field.get_attribute("value") or ""
                if current_val.strip():
                    return  # Already filled

                if "phone" in label_text or "mobile" in label_text:
                    _fill_text_field(driver, field, profile.get("phone", ""))
                elif "city" in label_text or "location" in label_text:
                    _fill_text_field(driver, field, profile.get("city", "Pune"))
                elif "experience" in label_text or "years" in label_text:
                    _fill_text_field(driver, field, str(profile.get("experience_years", 4)))
                elif "name" in label_text:
                    _fill_text_field(driver, field, profile.get("name", ""))
                elif "linkedin" in label_text or "profile" in label_text:
                    _fill_text_field(driver, field, profile.get("linkedin_url", ""))
                elif "website" in label_text or "portfolio" in label_text:
                    _fill_text_field(driver, field, profile.get("portfolio_url", ""))
                elif "salary" in label_text or "ctc" in label_text or "compensation" in label_text:
                    _fill_text_field(driver, field, profile.get("expected_salary", ""))

            elif input_type == "radio":
                # Handle yes/no questions — default to "Yes" for standard questions
                if field.get_attribute("value") and field.get_attribute("value").lower() in ("yes", "true"):
                    if not field.is_selected():
                        field.click()

        elif tag == "select":
            sel = Select(field)
            options_text = [o.text.lower() for o in sel.options]

            # Try to pick a sensible option
            if "experience" in label_text or "years" in label_text:
                for opt in sel.options:
                    if str(profile.get("experience_years", 4)) in opt.text:
                        sel.select_by_visible_text(opt.text)
                        break
            elif any(w in label_text for w in ["country", "nation"]):
                for opt in sel.options:
                    if "india" in opt.text.lower():
                        sel.select_by_visible_text(opt.text)
                        break
            elif "notice" in label_text:
                for opt in sel.options:
                    if any(x in opt.text.lower() for x in ["immediately", "0", "15"]):
                        sel.select_by_visible_text(opt.text)
                        break

    except Exception as e:
        logger.debug(f"Field fill error (non-fatal): {e}")


def _upload_resume(driver, resume_path: str):
    if not resume_path or not os.path.exists(resume_path):
        logger.warning(f"Resume not found at: {resume_path}")
        return

    try:
        upload_inputs = driver.find_elements(
            By.XPATH, "//input[@type='file' and contains(@accept,'pdf')]"
        )
        if upload_inputs:
            upload_inputs[0].send_keys(os.path.abspath(resume_path))
            logger.info("Resume uploaded.")
            _wait(2, 3)
    except Exception as e:
        logger.warning(f"Resume upload error: {e}")


def _apply_to_job(driver, job: dict, profile: dict, dry_run: bool) -> str:
    """
    Attempt Easy Apply for a single job.
    Returns: "applied", "skipped_complex", "skipped_no_easy_apply", "error"
    """
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(job["url"])
        _wait(2, 4)

        # Click Easy Apply button
        easy_apply_btn = None
        for xpath in [
            "//button[contains(@class,'jobs-apply-button') and contains(.,'Easy Apply')]",
            "//button[contains(.,'Easy Apply')]",
            "//span[contains(.,'Easy Apply')]/..",
        ]:
            try:
                easy_apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                break
            except TimeoutException:
                continue

        if not easy_apply_btn:
            return "skipped_no_easy_apply"

        easy_apply_btn.click()
        _wait(1.5, 2.5)

        step = 0
        MAX_STEPS = 4

        while step < MAX_STEPS:
            step += 1

            # Upload resume if prompt exists
            _upload_resume(driver, profile.get("resume_path", ""))

            # Fill all visible form fields
            fields = driver.find_elements(
                By.XPATH,
                "//input[not(@type='hidden')] | //textarea | //select"
            )
            for field in fields:
                try:
                    if field.is_displayed() and field.is_enabled():
                        _handle_form_field(driver, field, profile)
                        _wait(0.1, 0.3)
                except Exception:
                    pass

            _wait(1, 2)

            # Check for "Review" or "Submit" button
            for submit_xpath in [
                "//button[contains(.,'Submit application')]",
                "//button[contains(.,'Submit')]",
            ]:
                try:
                    submit_btn = driver.find_element(By.XPATH, submit_xpath)
                    if submit_btn.is_displayed():
                        if dry_run:
                            logger.info(f"[DRY RUN] Would submit: {job['title']} @ {job['company']}")
                            # Close the modal
                            try:
                                driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']").click()
                            except Exception:
                                pass
                            return "dry_run"
                        else:
                            submit_btn.click()
                            _wait(2, 3)
                            logger.info(f"Applied: {job['title']} @ {job['company']}")
                            return "applied"
                except NoSuchElementException:
                    pass

            # Click "Next" to go to the next step
            next_clicked = False
            for next_xpath in [
                "//button[contains(.,'Next')]",
                "//button[contains(.,'Continue')]",
                "//button[contains(.,'Review')]",
            ]:
                try:
                    next_btn = driver.find_element(By.XPATH, next_xpath)
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        next_btn.click()
                        _wait(1.5, 2.5)
                        next_clicked = True
                        break
                except NoSuchElementException:
                    pass

            if not next_clicked:
                logger.warning(f"Could not find Next/Submit on step {step}. Skipping.")
                try:
                    driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']").click()
                except Exception:
                    pass
                return "skipped_complex"

        # Too many steps — skip
        logger.warning(f"Too many steps for: {job['title']}. Skipping.")
        try:
            driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']").click()
        except Exception:
            pass
        return "skipped_complex"

    except Exception as e:
        logger.error(f"Error applying to {job.get('url','')}: {e}")
        return "error"


def run_auto_apply(jobs: list, db=None):
    """
    Main entry point. Called from main.py when ENABLE_AUTO_APPLY = True.
    """
    import config

    if not SELENIUM_AVAILABLE:
        logger.error("selenium / undetected-chromedriver not installed.")
        logger.error("Run: pip install selenium undetected-chromedriver")
        return

    if not config.ENABLE_AUTO_APPLY:
        return

    # Filter: only Easy Apply jobs above score threshold
    candidates = [
        j for j in jobs
        if j.get("easy_apply") and j.get("score", 0) >= config.AUTO_APPLY_MIN_SCORE
    ]

    if not candidates:
        logger.info("[AutoApply] No Easy Apply jobs above score threshold.")
        return

    # Daily limit check
    if db:
        applied_today = db.count_applied_today()
        remaining = config.MAX_DAILY_APPLICATIONS - applied_today
        if remaining <= 0:
            logger.info(f"[AutoApply] Daily limit ({config.MAX_DAILY_APPLICATIONS}) reached.")
            return
        candidates = candidates[:remaining]

    profile = {
        "name":            config.CANDIDATE_NAME,
        "phone":           "",      # Add your phone number
        "city":            "Pune",
        "experience_years": config.EXPERIENCE_YEARS,
        "linkedin_url":    "",      # Your LinkedIn profile URL
        "portfolio_url":   "",
        "expected_salary": "",
        "resume_path":     config.RESUME_PATH,
    }

    logger.info(f"[AutoApply] Starting. {len(candidates)} candidate jobs. DRY_RUN={config.DRY_RUN}")

    driver = _get_driver()
    try:
        if not _login(driver, config.LINKEDIN_EMAIL, config.LINKEDIN_PASSWORD):
            logger.error("[AutoApply] Login failed. Aborting.")
            return

        for job in candidates:
            logger.info(f"[AutoApply] Attempting: {job['title']} @ {job['company']} (score={job['score']})")
            status = _apply_to_job(driver, job, profile, dry_run=config.DRY_RUN)
            logger.info(f"[AutoApply] Status: {status}")

            if db and status in ("applied", "dry_run"):
                db.mark_applied(job["url"], status)

            _wait(5, 10)   # Pause between applications

    finally:
        driver.quit()
