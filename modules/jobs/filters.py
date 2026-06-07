# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""LinkedIn job-search filter management for JobPilot AI.

Handles setting the search location, applying all configured filters
in the LinkedIn 'All filters' panel, and reading pagination state.
"""

import pyautogui

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

import modules.browser.session as browser
from modules.browser.interactions import (
    wait_span_click,
    multi_sel_noWait,
    boolean_button_click,
    try_xp,
    scroll_to_view,
    try_find_by_classes,
    text_input,
)
from modules.helpers import print_lg, buffer
from urllib.parse import quote_plus

from config.settings import click_gap
from config.search import (
    search_location,
    sort_by, date_posted, salary,
    easy_apply_only,
    experience_level, job_type, on_site,
    companies, location, industry, job_function, job_titles,
    benefits, commitments,
    under_10_applicants, in_your_network, fair_chance_employer,
)


_EXP_LEVEL_CODES = {
    "Internship": "1",
    "Entry level": "2",
    "Associate": "3",
    "Mid-Senior level": "4",
    "Director": "5",
    "Executive": "6",
}
_WORK_TYPE_CODES = {"On-site": "1", "Remote": "2", "Hybrid": "3"}
_JOB_TYPE_CODES = {
    "Full-time": "F",
    "Part-time": "P",
    "Contract": "C",
    "Temporary": "T",
    "Volunteer": "V",
    "Internship": "I",
}
_DATE_POSTED_CODES = {
    "Past 24 hours": "r86400",
    "Past week": "r604800",
    "Past month": "r2592000",
}


def build_search_url(search_term: str) -> str:
    """Build a LinkedIn jobs search URL with configured filters as query params.

    Args:
        search_term: Job title or keyword string to search for.

    Returns:
        Full LinkedIn jobs search URL including encoded filter parameters.
    """
    parts = [f"keywords={quote_plus(search_term)}"]
    if search_location.strip():
        parts.append(f"location={quote_plus(search_location.strip())}")
    if easy_apply_only:
        parts.append("f_AL=true")
    exp_codes = [_EXP_LEVEL_CODES[level] for level in experience_level if level in _EXP_LEVEL_CODES]
    if exp_codes:
        parts.append(f"f_E={','.join(exp_codes)}")
    wt_codes = [_WORK_TYPE_CODES[style] for style in on_site if style in _WORK_TYPE_CODES]
    if wt_codes:
        parts.append(f"f_WT={','.join(wt_codes)}")
    jt_codes = [_JOB_TYPE_CODES[jt] for jt in job_type if jt in _JOB_TYPE_CODES]
    if jt_codes:
        parts.append(f"f_JT={','.join(jt_codes)}")
    if date_posted in _DATE_POSTED_CODES:
        parts.append(f"f_TPR={_DATE_POSTED_CODES[date_posted]}")
    parts.append(f"sortBy={'DD' if sort_by == 'Most recent' else 'R'}")
    return "https://www.linkedin.com/jobs/search/?" + "&".join(parts)


def set_search_location() -> None:
    """Fill the LinkedIn location search box with the configured search location.

    If ``search_location`` is empty the function returns immediately without
    interacting with the page.
    """
    if not search_location.strip():
        return

    print_lg(f'Setting search location: "{search_location.strip()}"')
    try:
        location_input = try_xp(
            browser.driver,
            ".//input[@aria-label='City, state, or zip code' and not(@disabled)]",
            click=False,
        )
        text_input(browser.actions, location_input, search_location, "Search Location")
    except Exception as e:
        try_xp(browser.driver, ".//button[@aria-label='Cancel']")
        print_lg("Failed to set search location — continuing with default.", e)


def apply_filters(pause_after_filters: bool, location_in_url: bool = False) -> bool:
    """Open the 'All filters' panel and apply every configured filter option.

    After applying all filters the 'Show results' button is clicked.
    If ``pause_after_filters`` is True the user is shown a confirmation
    dialog so they can adjust filters or verify the results before the
    bot continues.

    Args:
        pause_after_filters: Whether to pause and prompt the user after
            applying filters.
        location_in_url: When True, skip the UI location box because the
            search URL already includes ``&location=...``.

    Returns:
        Updated value of ``pause_after_filters`` — may be set to False
        if the user elects to disable future pauses.
    """
    if not location_in_url:
        set_search_location()

    try:
        recommended_wait = 1 if click_gap < 1 else 0
        buffer(5)

        WebDriverWait(browser.driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, '//button[normalize-space()="All filters"]')
            )
        ).click()
        buffer(recommended_wait)

        wait_span_click(browser.driver, sort_by)
        wait_span_click(browser.driver, date_posted)
        buffer(recommended_wait)

        multi_sel_noWait(browser.driver, experience_level)
        multi_sel_noWait(browser.driver, companies, browser.actions)
        if experience_level or companies:
            buffer(recommended_wait)

        multi_sel_noWait(browser.driver, job_type)
        multi_sel_noWait(browser.driver, on_site)
        if job_type or on_site:
            buffer(recommended_wait)

        if easy_apply_only:
            boolean_button_click(browser.driver, browser.actions, "Easy Apply")

        multi_sel_noWait(browser.driver, location)
        multi_sel_noWait(browser.driver, industry)
        if location or industry:
            buffer(recommended_wait)

        multi_sel_noWait(browser.driver, job_function)
        multi_sel_noWait(browser.driver, job_titles)
        if job_function or job_titles:
            buffer(recommended_wait)

        if under_10_applicants:
            boolean_button_click(browser.driver, browser.actions, "Under 10 applicants")
        if in_your_network:
            boolean_button_click(browser.driver, browser.actions, "In your network")
        if fair_chance_employer:
            boolean_button_click(browser.driver, browser.actions, "Fair Chance Employer")

        wait_span_click(browser.driver, salary)
        buffer(recommended_wait)

        multi_sel_noWait(browser.driver, benefits)
        multi_sel_noWait(browser.driver, commitments)
        if benefits or commitments:
            buffer(recommended_wait)

        show_btn = browser.driver.find_element(
            By.XPATH,
            '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
            ' "abcdefghijklmnopqrstuvwxyz"), "apply current filters to show")]',
        )
        show_btn.click()
        buffer(8)

        if pause_after_filters:
            choice = pyautogui.confirm(
                "Review your search results and filters.\n"
                "You may adjust them while this dialog is open.\n"
                "Click 'Continue' when ready.",
                "Review Filters",
                ["Turn off Pause after search", "Continue"],
            )
            if choice == "Turn off Pause after search":
                pause_after_filters = False

    except TimeoutException as e:
        print_lg("Filter panel not found within 15s — skipping UI filters and continuing.", e)
    except Exception as e:
        print_lg("Failed to apply filters — skipping UI filters and continuing.", e)
        if pause_after_filters:
            pyautogui.confirm(
                f"Error applying filters: {e}\n\n"
                "Please adjust filters manually, click 'Show results', then click a button below.",
                "Filter Error",
                ["Continue anyway"],
            )

    return pause_after_filters


def get_page_info() -> tuple[WebElement | None, int | None]:
    """Read the current pagination element and active page number.

    Returns:
        A 2-tuple of ``(pagination_element, current_page_number)``.
        Both values are ``None`` if the pagination element cannot be found
        (e.g., only one page of results).
    """
    try:
        pagination = try_find_by_classes(
            browser.driver,
            ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"],
        )
        scroll_to_view(browser.driver, pagination)
        current_page = int(
            pagination.find_element(By.XPATH, "//button[contains(@class, 'active')]").text
        )
        return pagination, current_page
    except Exception as e:
        print_lg("Could not find pagination element — may be on the last page.", e)
        return None, None
