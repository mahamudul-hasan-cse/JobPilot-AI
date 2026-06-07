# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Core job-application loop for JobPilot AI.

Implements the per-job workflow:
  1. Iterate job cards on each search-results page.
  2. Extract job metadata and check blacklists / experience thresholds.
  3. (Optional) AI relevance scoring — skip low-match jobs.
  4. Attempt Easy Apply or collect the external apply URL.
  5. Delegate form-filling to :mod:`modules.jobs.form_filler`.
  6. Log results via :mod:`modules.jobs.logger`.
"""

import re
from datetime import datetime
from random import shuffle
from typing import Any
from urllib.parse import quote_plus

import pyautogui

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    NoSuchWindowException,
    InvalidSessionIdException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

import modules.browser.session as browser
from modules.browser.interactions import (
    find_by_class,
    scroll_to_view,
    try_xp,
    try_find_by_classes,
    wait_span_click,
)
from modules.helpers import print_lg, buffer, calculate_date_posted, critical_error_log
from modules.jobs.logger import (
    get_applied_job_ids,
    submitted_jobs,
    failed_job,
    screenshot,
)
from modules.jobs.form_filler import answer_questions, upload_resume
from modules.jobs.filters import apply_filters, get_page_info, build_search_url

from config.settings import (
    click_gap, close_tabs, follow_companies, keep_screen_awake,
)
from config.search import (
    switch_number, randomize_search_order,
    bad_words, security_clearance, did_masters, current_experience,
    about_company_bad_words, about_company_good_words,
    easy_apply_only,
    company_skip_patterns, title_skip_keywords, max_jobs_to_scan,
)
from config.questions import (
    default_resume_path, pause_before_submit, pause_at_failed_question,
)
from config.secrets import (
    use_AI,
    ai_provider,
    use_relevance_scoring,
    ai_relevance_threshold,
    strict_relevance_scoring,
)


# ---------------------------------------------------------------------------
# Module-level counters (reset each call to apply_to_jobs if needed)
# ---------------------------------------------------------------------------
_easy_applied_count: int = 0
_external_jobs_count: int = 0
_failed_count: int = 0
_skip_count: int = 0
_tabs_count: int = 1
_daily_limit_reached: bool = False
_use_new_resume: bool = True

_re_experience = re.compile(
    r"[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?", re.IGNORECASE
)


def get_summary() -> dict[str, int | bool]:
    """Return a summary dict of application counts for the current run.

    Returns:
        Dict with keys: ``easy_applied``, ``external``, ``failed``,
        ``skipped``, ``daily_limit_reached``.
    """
    return {
        "easy_applied": _easy_applied_count,
        "external": _external_jobs_count,
        "failed": _failed_count,
        "skipped": _skip_count,
        "daily_limit_reached": _daily_limit_reached,
    }


# ---------------------------------------------------------------------------
# Per-job detail helpers
# ---------------------------------------------------------------------------

def get_job_main_details(
    job: WebElement,
    blacklisted_companies: set[str],
    rejected_jobs: set[str],
) -> tuple[str, str, str, str, str, bool]:
    """Extract title, company, location and work style from a job card element.

    Also checks whether the job should be skipped (blacklist / already applied).

    Args:
        job: A ``<li data-occludable-job-id>`` WebElement from the job list.
        blacklisted_companies: Set of company names already blacklisted this run.
        rejected_jobs: Set of job IDs already rejected this run.

    Returns:
        6-tuple ``(job_id, title, company, work_location, work_style, skip)``.
        ``skip=True`` means this job should be skipped without applying.
    """
    skip = False
    job_link = job.find_element(By.TAG_NAME, "a")
    scroll_to_view(browser.driver, job_link, top=True)
    job_id = job.get_dom_attribute("data-occludable-job-id")
    title = job_link.text
    title = title[: title.find("\n")] if "\n" in title else title

    details = job.find_element(By.CLASS_NAME, "artdeco-entity-lockup__subtitle").text
    sep = details.find(" · ")
    company = details[:sep]
    work_location = details[sep + 3 :]
    work_style = work_location[work_location.rfind("(") + 1 : work_location.rfind(")")]
    work_location = work_location[: work_location.rfind("(")].strip()

    if company in blacklisted_companies:
        print_lg(f'Skipping blacklisted company: "{company}" | Job ID: {job_id}')
        skip = True
    elif job_id in rejected_jobs:
        print_lg(f'Skipping previously rejected job ID: {job_id}')
        skip = True
    else:
        for pattern in company_skip_patterns:
            if pattern.lower() in company.lower():
                print_lg(f'Skipping company pattern "{pattern}": "{company}" | Job ID: {job_id}')
                blacklisted_companies.add(company)
                skip = True
                break
        if not skip:
            title_lower = title.lower()
            for keyword in title_skip_keywords:
                if keyword.lower() in title_lower:
                    print_lg(f'Skipping title keyword "{keyword}": "{title}" | Job ID: {job_id}')
                    skip = True
                    break
    try:
        applied_state = job.find_element(
            By.CLASS_NAME, "job-card-container__footer-job-state"
        ).text
        if applied_state == "Applied":
            print_lg(f'Already applied to "{title}" at "{company}" | Job ID: {job_id}')
            skip = True
    except Exception:
        pass

    try:
        if not skip:
            job_link.click()
    except Exception as e:
        print_lg(f'Could not click job card for "{title}" | Job ID: {job_id}', e)
        discard_job()
        job_link.click()

    buffer(click_gap)
    return job_id, title, company, work_location, work_style, skip


def check_blacklist(
    rejected_jobs: set[str],
    job_id: str,
    company: str,
    blacklisted_companies: set[str],
) -> tuple[set[str], set[str], WebElement]:
    """Check the 'About Company' section for blacklisted keywords.

    Args:
        rejected_jobs: Running set of rejected job IDs.
        job_id: Current job ID.
        company: Current company name.
        blacklisted_companies: Running set of blacklisted company names.

    Returns:
        Updated ``(rejected_jobs, blacklisted_companies, jobs_top_card_element)``.

    Raises:
        ValueError: If a blacklisted word is found in the About Company text.
    """
    jobs_top_card = try_find_by_classes(browser.driver, [
        "job-details-jobs-unified-top-card__primary-description-container",
        "job-details-jobs-unified-top-card__primary-description",
        "jobs-unified-top-card__primary-description",
        "jobs-details__main-content",
    ])
    about_box = find_by_class(browser.driver, "jobs-company__box")
    scroll_to_view(browser.driver, about_box)
    about_text_raw = about_box.text
    about_text = about_text_raw.lower()

    skip_checking = any(word.lower() in about_text for word in about_company_good_words)
    if not skip_checking:
        for word in about_company_bad_words:
            if word.lower() in about_text:
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(
                    f'\n"{about_text_raw}"\n\nContains blacklisted word "{word}".'
                )

    buffer(click_gap)
    scroll_to_view(browser.driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card


def extract_years_of_experience(text: str) -> int:
    """Parse the maximum years-of-experience requirement from job description text.

    Args:
        text: Full job description text.

    Returns:
        The highest experience value found (capped at 12 years), or ``0``
        if no experience requirement is detected.
    """
    matches = re.findall(_re_experience, text)
    if not matches:
        print_lg("No experience requirement found in job description.")
        return 0
    valid = [int(m) for m in matches if int(m) <= 12]
    return max(valid) if valid else 0


def get_job_description() -> tuple[str, int | str, bool, str | None, str | None]:
    """Extract and evaluate the job description from the open job detail pane.

    Checks for bad keywords, security-clearance mentions, and experience
    thresholds.

    Returns:
        5-tuple ``(job_description, experience_required, skip, skip_reason, skip_message)``.

        - ``job_description``: Full text or ``"Unknown"`` if extraction fails.
        - ``experience_required``: Parsed integer or sentinel string.
        - ``skip``: ``True`` if the job should be skipped.
        - ``skip_reason``: Short label for the failure CSV column.
        - ``skip_message``: Detailed log message.
    """
    job_description = "Unknown"
    experience_required: int | str = "Unknown"
    skip = False
    skip_reason = None
    skip_message = None

    try:
        job_description = find_by_class(browser.driver, "jobs-box__html-content").text
        desc_lower = job_description.lower()

        for word in bad_words:
            if word.lower() in desc_lower:
                skip_message = f'\n{job_description}\n\nContains bad word "{word}". Skipping.\n'
                skip_reason = "Found a Bad Word in About Job"
                skip = True
                break

        if not skip and not security_clearance:
            if any(kw in desc_lower for kw in ("polygraph", "clearance", "secret")):
                skip_message = f'\n{job_description}\n\nRequires security clearance. Skipping.\n'
                skip_reason = "Asking for Security Clearance"
                skip = True

        if not skip:
            masters_bonus = 2 if did_masters and "master" in desc_lower else 0
            experience_required = extract_years_of_experience(job_description)
            if current_experience > -1 and experience_required > current_experience + masters_bonus:
                skip_message = (
                    f"\nRequired experience ({experience_required} yrs) exceeds "
                    f"current experience ({current_experience + masters_bonus} yrs). Skipping.\n"
                )
                skip_reason = "Required experience is too high"
                skip = True

    except Exception as e:
        if job_description == "Unknown":
            print_lg("Could not extract job description.")
        else:
            experience_required = "Error in extraction"
            print_lg("Could not extract years of experience.", e)

    return job_description, experience_required, skip, skip_reason, skip_message


# ---------------------------------------------------------------------------
# Application-action helpers
# ---------------------------------------------------------------------------

def follow_company(modal: WebElement | None = None) -> None:
    """Check or uncheck the 'Follow company' checkbox in the Easy Apply modal.

    Args:
        modal: The Easy Apply modal ``WebElement``. Defaults to ``browser.driver``
            if not provided.
    """
    target = modal if modal else browser.driver
    try:
        checkbox = try_xp(
            target,
            ".//input[@id='follow-company-checkbox' and @type='checkbox']",
            click=False,
        )
        if checkbox and checkbox.is_selected() != follow_companies:
            try_xp(target, ".//label[@for='follow-company-checkbox']")
    except Exception as e:
        print_lg("Could not update 'Follow company' checkbox.", e)


def discard_job() -> None:
    """Dismiss the current Easy Apply modal by pressing Escape then 'Discard'."""
    from selenium.webdriver.common.keys import Keys
    browser.actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(browser.driver, "Discard", 2)


def _easy_apply_submit_confirmed() -> bool:
    """Click Submit application or Done and confirm the modal advanced.

    Returns:
        ``True`` if either button was found and clicked successfully.
    """
    if wait_span_click(browser.driver, "Submit application", 2, scrollTop=True):
        wait_span_click(browser.driver, "Done", 2)
        return True
    if wait_span_click(browser.driver, "Done", 2, scrollTop=True):
        return True
    return False


def external_apply(
    pagination_element: WebElement | None,
    job_id: str,
    job_link: str,
    resume: str,
    date_listed: object,
    application_link: str,
    screenshot_name: str,
) -> tuple[bool, str, int]:
    """Open the external application URL in a new tab and record it.

    Args:
        pagination_element: Current page's pagination element (used to
            detect end-of-results).
        job_id: LinkedIn job ID.
        job_link: Full LinkedIn job URL.
        resume: Resume path used this run.
        date_listed: Approximate posting date.
        application_link: Current placeholder for the external URL.
        screenshot_name: Debug screenshot filename.

    Returns:
        3-tuple ``(skip: bool, application_link: str, tabs_count: int)``.
        ``skip=True`` means the caller should move to the next job.
    """
    global _tabs_count, _daily_limit_reached

    if easy_apply_only:
        try:
            limit_msg = browser.driver.find_element(
                By.CLASS_NAME, "artdeco-inline-feedback__message"
            ).text
            if "exceeded the daily application limit" in limit_msg:
                _daily_limit_reached = True
        except Exception:
            pass
        print_lg("Easy Apply not available — skipping external apply.")
        if pagination_element is not None:
            return True, application_link, _tabs_count

    try:
        browser.wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                ".//button[contains(@class,'jobs-apply-button') "
                "and contains(@class, 'artdeco-button--3')]",
            ))
        ).click()
        wait_span_click(browser.driver, "Continue", 1, True, False)
        windows = browser.driver.window_handles
        _tabs_count = len(windows)
        browser.driver.switch_to.window(windows[-1])
        application_link = browser.driver.current_url
        print_lg(f'External apply URL: "{application_link}"')
        if close_tabs and browser.driver.current_window_handle != _linkedin_tab:
            browser.driver.close()
        browser.driver.switch_to.window(_linkedin_tab)
        return False, application_link, _tabs_count
    except Exception as e:
        print_lg("External apply failed.", e)
        critical_error_log("In external_apply", e)
        failed_job(job_id, job_link, resume, date_listed, "External apply failed", e,
                   application_link, screenshot_name)
        global _failed_count
        _failed_count += 1
        return True, application_link, _tabs_count


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_linkedin_tab: str = ""
_pause_before_submit = pause_before_submit


def apply_to_jobs(
    search_terms: list[str],
    ai_client: Any = None,
    linkedin_tab: str = "",
) -> None:
    """Iterate every job listing for each search term and attempt to apply.

    This is the main application loop. For each search term:
      1. Opens the LinkedIn jobs search page.
      2. Applies configured filters.
      3. Paginates through results up to ``switch_number`` applications.
      4. For each job card: extracts details, checks blacklists/thresholds,
         optionally runs AI relevance scoring, then performs Easy Apply or
         records the external URL.

    Args:
        search_terms: List of job title search strings.
        ai_client: Active AI client (or ``None`` if AI is disabled).
        linkedin_tab: Window handle of the LinkedIn tab (set by ``main.py``).
    """
    global _easy_applied_count, _external_jobs_count, _failed_count, _skip_count
    global _tabs_count, _daily_limit_reached, _use_new_resume, _pause_before_submit
    global _linkedin_tab

    _linkedin_tab = linkedin_tab or browser.driver.current_window_handle

    from modules.ai.scoring import clear_score_cache
    clear_score_cache()

    applied_jobs = get_applied_job_ids()
    rejected_jobs: set[str] = set()
    blacklisted_companies: set[str] = set()

    _pause_before_submit = pause_before_submit

    if randomize_search_order:
        shuffle(search_terms)

    # Import mutable pause_after_filters from config (may be toggled)
    import config.search as _search_cfg
    pause_after = _search_cfg.pause_after_filters

    from config.search import search_location as _search_location, use_ui_filters

    for search_term in search_terms:
        url = build_search_url(search_term)
        browser.driver.get(url)
        print_lg("\n" + "=" * 120)
        print_lg(f'\nSearching for: "{search_term}"\n')

        if use_ui_filters:
            loc = quote_plus(_search_location.strip()) if _search_location.strip() else ""
            try:
                pause_after = apply_filters(pause_after, location_in_url=bool(loc))
            except TimeoutException:
                print_lg("Filter button not found within 15s — skipping filters and continuing.")
            _search_cfg.pause_after_filters = pause_after
        else:
            buffer(2)

        current_count = 0
        stale_retries = 0
        try:
            while current_count < switch_number:
                try:
                    WebDriverWait(browser.driver, 12).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH, "//li[@data-occludable-job-id]"
                        ))
                    )
                    pagination_element, current_page = get_page_info()
                    stale_retries = 0

                    buffer(1)
                    job_listings = browser.driver.find_elements(
                        By.XPATH, "//li[@data-occludable-job-id]"
                    )
                    if not job_listings:
                        print_lg("No job listings visible yet — retrying.")
                        buffer(2)
                        continue
                except (StaleElementReferenceException, TimeoutException):
                    stale_retries += 1
                    if stale_retries > 6:
                        print_lg("Job list not loading — moving to next search term.")
                        break
                    print_lg("Waiting for LinkedIn job results to load...")
                    buffer(2)
                    continue

                jobs_scanned_this_page = 0
                for job in job_listings:
                    if keep_screen_awake:
                        pyautogui.press("shiftright")
                    if current_count >= switch_number:
                        break

                    jobs_scanned_this_page += 1
                    if jobs_scanned_this_page > max_jobs_to_scan:
                        print_lg(
                            f"Scanned {max_jobs_to_scan} jobs on this page "
                            "without enough applies — paginating."
                        )
                        break

                    print_lg("\n--- Next job ---")

                    # Extract job card details
                    job_id, title, company, work_location, work_style, skip = get_job_main_details(
                        job, blacklisted_companies, rejected_jobs
                    )
                    if skip:
                        continue

                    # Redundant already-applied check
                    try:
                        already_applied = find_by_class(
                            browser.driver, "jobs-s-apply__application-link", 2
                        )
                        if job_id in applied_jobs or already_applied:
                            print_lg(f'Already applied to "{title}" at "{company}".')
                            continue
                    except Exception:
                        print_lg(f'Attempting to apply to "{title}" at "{company}".')

                    job_link = f"https://www.linkedin.com/jobs/view/{job_id}"
                    application_link = "Easy Applied"
                    date_applied: datetime | str = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development"
                    date_listed: object = "Unknown"
                    skills: object = "Needs AI"
                    resume = "Pending"
                    reposted = False
                    questions_list: set | None = None
                    screenshot_name = "Not Available"
                    relevance_score: int | str = "N/A"

                    # Check About Company blacklist
                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(
                            rejected_jobs, job_id, company, blacklisted_companies
                        )
                    except ValueError as e:
                        print_lg(e, "Skipping.\n")
                        failed_job(
                            job_id, job_link, resume, date_listed,
                            "Blacklisted word in About Company", e, "Skipped", screenshot_name,
                        )
                        _skip_count += 1
                        continue
                    except Exception as e:
                        print_lg("Could not scroll to About Company.", e)

                    # Hiring manager info
                    try:
                        hr_card = WebDriverWait(browser.driver, 2).until(
                            EC.presence_of_element_located((
                                By.CLASS_NAME, "hirer-card__hirer-information"
                            ))
                        )
                        hr_link = hr_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_card.find_element(By.TAG_NAME, "span").text
                    except Exception:
                        print_lg(f'No hiring manager info for "{title}" (Job ID: {job_id}).')

                    # Date posted
                    try:
                        time_text = jobs_top_card.find_element(
                            By.XPATH, './/span[contains(normalize-space(), " ago")]'
                        ).text
                        if "Reposted" in time_text:
                            reposted = True
                            time_text = time_text.replace("Reposted", "").strip()
                        date_listed = calculate_date_posted(time_text)
                    except Exception as e:
                        print_lg("Could not parse date posted.", e)

                    # Job description + filters
                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message,
                                   "Skipped", screenshot_name)
                        rejected_jobs.add(job_id)
                        _skip_count += 1
                        continue

                    # AI Skill Extraction — skipped when relevance scoring is on
                    # to save API quota.
                    if (
                        use_AI and ai_client and description != "Unknown"
                        and use_relevance_scoring is False
                    ):
                        try:
                            from modules.ai.client_factory import extract_skills
                            skills = extract_skills(ai_client, ai_provider, description)
                            print_lg(f"Skills extracted via {ai_provider}.")
                        except Exception as e:
                            print_lg("Skill extraction failed.", e)
                            skills = "Error extracting skills"
                    elif use_AI and use_relevance_scoring:
                        skills = "Via relevance scoring"

                    # AI Relevance Scoring (JobPilot AI Feature)
                    if use_AI and use_relevance_scoring and ai_client and description != "Unknown":
                        from modules.ai.scoring import is_ai_quota_exhausted
                        if is_ai_quota_exhausted():
                            relevance_score = "N/A (quota exhausted)"
                        else:
                            try:
                                from modules.ai.client_factory import score_job_relevance
                                from config.questions import user_information_all
                                result = score_job_relevance(
                                    ai_client,
                                    ai_provider,
                                    description,
                                    user_information_all,
                                    job_id=job_id,
                                    fail_open=not strict_relevance_scoring,
                                )
                                relevance_score = result.get("score", 100)
                                reason = result.get("reason", "")
                                print_lg(f"Relevance score: {relevance_score}/100 — {reason}")
                                threshold = ai_relevance_threshold
                                if isinstance(relevance_score, int) and relevance_score < threshold:
                                    skip_msg = (
                                        f"Relevance score {relevance_score}/100 < "
                                        f"threshold {ai_relevance_threshold}. Skipping."
                                    )
                                    print_lg(skip_msg)
                                    failed_job(
                                        job_id, job_link, resume, date_listed,
                                        "Low AI relevance score", skip_msg,
                                        "Skipped", screenshot_name,
                                    )
                                    _skip_count += 1
                                    continue
                            except Exception as e:
                                if strict_relevance_scoring and not is_ai_quota_exhausted():
                                    skip_msg = f"Relevance scoring failed (strict mode): {e}"
                                    print_lg(skip_msg)
                                    failed_job(
                                        job_id, job_link, resume, date_listed,
                                        "AI scoring failed", skip_msg,
                                        "Skipped", screenshot_name,
                                    )
                                    _skip_count += 1
                                    continue
                                print_lg("Relevance scoring failed — proceeding anyway.", e)

                    uploaded = False

                    # Detect Easy Apply
                    is_easy_apply = try_xp(
                        browser.driver,
                        ".//button[contains(@class,'jobs-apply-button') and "
                        "contains(@class, 'artdeco-button--3') and contains(@aria-label, 'Easy')]",
                    )
                    if not is_easy_apply:
                        try:
                            link_el = browser.driver.find_element(
                                By.XPATH, ".//a[contains(@href, 'openSDUIApplyFlow=true')]"
                            )
                            link_el.click()
                            is_easy_apply = True
                            print_lg("Detected Easy Apply via URL pattern.")
                        except Exception:
                            pass

                    if not is_easy_apply:
                        try:
                            apply_btn = browser.driver.find_element(
                                By.XPATH, ".//button[contains(@class,'jobs-apply-button')]"
                            )
                            tabs_before = len(browser.driver.window_handles)
                            apply_btn.click()
                            buffer(click_gap)
                            if len(browser.driver.window_handles) > tabs_before:
                                browser.driver.switch_to.window(browser.driver.window_handles[-1])
                                cur_handle = browser.driver.current_window_handle
                                if close_tabs and cur_handle != _linkedin_tab:
                                    browser.driver.close()
                                browser.driver.switch_to.window(_linkedin_tab)
                                print_lg("External tab opened — treating as external apply.")
                            else:
                                try:
                                    find_by_class(browser.driver, "jobs-easy-apply-modal")
                                    is_easy_apply = True
                                    print_lg("Easy Apply modal appeared after click.")
                                except Exception:
                                    try:
                                        from selenium.webdriver.common.keys import Keys
                                        browser.actions.send_keys(Keys.ESCAPE).perform()
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                    # Easy Apply path
                    if is_easy_apply:
                        submit_confirmed = False
                        try:
                            errored = ""
                            modal = None
                            questions_list = set()
                            try:
                                modal = find_by_class(browser.driver, "jobs-easy-apply-modal")
                                wait_span_click(modal, "Next", 1)
                                resume = "Previous resume"
                                next_button = True
                                next_counter = 0

                                while next_button:
                                    next_counter += 1
                                    if next_counter >= 15:
                                        if pause_at_failed_question:
                                            screenshot(
                                                browser.driver, job_id, "Needed manual intervention"
                                            )
                                            pyautogui.alert(
                                                "Could not answer one or more questions.\n"
                                                "Please answer manually, then click Continue.\n"
                                                "DO NOT click Back, Next, or Review in LinkedIn.",
                                                "Help Needed", "Continue",
                                            )
                                            next_counter = 1
                                            continue
                                        if questions_list:
                                            print_lg("Stuck on questions:", questions_list)
                                        screenshot_name = screenshot(
                                            browser.driver, job_id, "Failed at questions"
                                        )
                                        errored = "stuck"
                                        raise Exception("Stuck in loop — too many Next clicks.")

                                    questions_list = answer_questions(
                                        modal, questions_list, work_location,
                                        job_description=description,
                                        company=company,
                                        title=title,
                                        ai_client=ai_client,
                                        ai_provider=ai_provider,
                                    )

                                    if _use_new_resume and not uploaded:
                                        uploaded, resume = upload_resume(modal, default_resume_path)

                                    try:
                                        next_button = modal.find_element(
                                            By.XPATH, './/span[normalize-space(.)="Review"]'
                                        )
                                    except NoSuchElementException:
                                        next_button = modal.find_element(
                                            By.XPATH, './/button[contains(span, "Next")]'
                                        )
                                    try:
                                        next_button.click()
                                    except ElementClickInterceptedException:
                                        break
                                    buffer(click_gap)

                            except NoSuchElementException:
                                errored = "nose"

                            if modal is None:
                                skip_msg = (
                                    f'Easy Apply modal not found for "{title}" at "{company}".'
                                )
                                print_lg(skip_msg)
                                failed_job(
                                    job_id, job_link, resume, date_listed,
                                    "Easy Apply modal not found", skip_msg,
                                    "Skipped", screenshot_name,
                                )
                                _skip_count += 1
                                continue

                            if questions_list and errored != "stuck":
                                print_lg("Questions answered:", questions_list)

                            wait_span_click(browser.driver, "Review", 1, scrollTop=True)
                            cur_pause = _pause_before_submit

                            if errored != "stuck" and cur_pause:
                                decision = pyautogui.confirm(
                                    "1. Please verify your application information.\n"
                                    "2. If you edited anything, return to the final screen.\n"
                                    "3. Do NOT click 'Submit Application'.\n\n"
                                    "Turn off 'pause_before_submit' in config/questions.py "
                                    "to disable this.",
                                    "Confirm Application",
                                    ["Disable Pause", "Discard Application", "Submit Application"],
                                )
                                if decision == "Discard Application":
                                    skip_msg = "Application discarded by user."
                                    print_lg(skip_msg)
                                    failed_job(
                                        job_id, job_link, resume, date_listed,
                                        "Application discarded", skip_msg,
                                        "Skipped", screenshot_name,
                                    )
                                    _skip_count += 1
                                    discard_job()
                                    continue
                                if decision == "Disable Pause":
                                    _pause_before_submit = False
                                else:
                                    _pause_before_submit = True

                            follow_company(modal)

                            submit_confirmed = _easy_apply_submit_confirmed()
                            if not submit_confirmed and errored != "stuck" and cur_pause:
                                confirm = pyautogui.confirm(
                                    "Did you submit the application manually?",
                                    "Confirm Submission",
                                    ["Yes", "No"],
                                )
                                if "Yes" in confirm:
                                    submit_confirmed = (
                                        wait_span_click(browser.driver, "Done", 2)
                                        or wait_span_click(browser.driver, "Submit application", 1)
                                    )

                            if not submit_confirmed:
                                skip_msg = (
                                    f'Easy Apply not completed for "{title}" at "{company}" '
                                    "(Submit/Done not confirmed)."
                                )
                                print_lg(skip_msg)
                                failed_job(
                                    job_id, job_link, resume, date_listed,
                                    "Easy Apply not submitted", skip_msg,
                                    "Skipped", screenshot_name,
                                )
                                _skip_count += 1
                                discard_job()
                                continue

                            date_applied = datetime.now()

                        except Exception as e:
                            print_lg("Failed to Easy Apply!")
                            critical_error_log("Easy Apply process", e)
                            failed_job(
                                job_id, job_link, resume, date_listed,
                                "Problem in Easy Applying", e,
                                application_link, screenshot_name,
                            )
                            _failed_count += 1
                            discard_job()
                            continue

                    elif easy_apply_only:
                        skip_msg = f'Easy Apply not available for "{title}" at "{company}".'
                        print_lg(skip_msg)
                        failed_job(
                            job_id, job_link, resume, date_listed,
                            "Easy Apply not available", skip_msg,
                            "Skipped", screenshot_name,
                        )
                        _skip_count += 1
                        continue
                    else:
                        # External apply path
                        skip, application_link, _tabs_count = external_apply(
                            pagination_element, job_id, job_link, resume, date_listed,
                            application_link, screenshot_name,
                        )
                        if _daily_limit_reached:
                            print_lg("\n### Daily Easy Apply limit reached! ###\n")
                            return
                        if skip:
                            continue

                    submitted_jobs(
                        job_id, title, company, work_location, work_style,
                        description, experience_required, skills,
                        hr_name, hr_link, resume, reposted,
                        date_listed, date_applied, job_link, application_link,
                        questions_list, connect_request, relevance_score,
                    )
                    if uploaded:
                        _use_new_resume = False

                    print_lg(f'Applied: "{title}" at "{company}" (Job ID: {job_id})')
                    current_count += 1
                    if application_link == "Easy Applied":
                        _easy_applied_count += 1
                    else:
                        _external_jobs_count += 1
                    applied_jobs.add(job_id)

                # Paginate
                if pagination_element is None:
                    print_lg("No more pages found.")
                    break
                try:
                    pagination_element.find_element(
                        By.XPATH, f"//button[@aria-label='Page {current_page + 1}']"
                    ).click()
                    print_lg(f"Moved to page {current_page + 1}")
                except NoSuchElementException:
                    print_lg(f"Page {current_page + 1} not found — end of results.")
                    break

        except (NoSuchWindowException, InvalidSessionIdException) as e:
            print_lg("Browser window closed or session invalid.", e)
            raise
        except StaleElementReferenceException as e:
            print_lg("Stale element in job loop — retrying next page.", e)
        except TimeoutException:
            print_lg("Timed out waiting for job listings — moving to next search term.")
        except WebDriverException as e:
            if "invalid session id" in str(e).lower() or "no such window" in str(e).lower():
                print_lg("Browser window closed or session invalid.", e)
                raise
            if "stale element" in str(e).lower():
                print_lg("Stale element in job loop — continuing.", e)
            else:
                print_lg("WebDriver error in job loop — stopping this search term.", e)
                break
        except Exception as e:
            print_lg("Error in job listing loop.")
            critical_error_log("In apply_to_jobs loop", e)
            try:
                print_lg(f"Page URL at error: {browser.driver.current_url}")
            except Exception:
                pass
