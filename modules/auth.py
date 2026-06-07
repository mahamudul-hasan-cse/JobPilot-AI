# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""LinkedIn authentication helpers for JobPilot AI.

Provides functions to detect login state and perform automated or
manual login to LinkedIn.
"""

import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import modules.browser.session as browser
from modules.browser.interactions import (
    find_by_class,
    text_input_by_ID,
    try_linkText,
    try_xp,
)
from modules.helpers import manual_login_retry, print_lg

_PLACEHOLDER_USERNAME = "username@example.com"
_PLACEHOLDER_PASSWORD = "example_password"
_LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
_LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"


def is_logged_in_linkedin() -> bool:
    """Check whether the browser is currently logged into LinkedIn.

    Inspects the current URL and looks for known sign-in page elements.

    Returns:
        ``True`` if the user appears to be logged in, ``False`` otherwise.
    """
    current_url = browser.driver.current_url or ""
    logged_in_paths = ("/feed", "/jobs/", "/mynetwork/", "/messaging/")
    if any(path in current_url for path in logged_in_paths):
        return True
    if try_xp(browser.driver, "//nav[contains(@class,'global-nav')]", 2):
        return True
    if try_xp(browser.driver, "//button[contains(@aria-label,'Me')]", 2):
        return True
    if current_url == _LINKEDIN_FEED_URL:
        return True
    if try_linkText(browser.driver, "Sign in"):
        return False
    sign_in_xpath = '//button[@type="submit" and contains(text(), "Sign in")]'
    if try_xp(browser.driver, sign_in_xpath):
        return False
    if try_linkText(browser.driver, "Join now"):
        return False

    print_lg("Could not confirm login state — will attempt sign-in.")
    return False


def ensure_linkedin_login(username: str, password: str) -> None:
    """Open LinkedIn and sign in only when the saved session is not active.

    Args:
        username: LinkedIn account email address.
        password: LinkedIn account password.
    """
    browser.driver.get(_LINKEDIN_FEED_URL)
    from modules.helpers import buffer

    buffer(5)
    if is_logged_in_linkedin():
        print_lg("LinkedIn session active — already logged in.")
        return

    print_lg(
        "Not logged in — attempting automatic sign-in with "
        "config/secrets.py credentials..."
    )
    browser.driver.get(_LINKEDIN_LOGIN_URL)
    buffer(4)
    login_linkedin(username, password)
    buffer(6)

    if is_logged_in_linkedin():
        print_lg("LinkedIn login successful.")
        return

    print_lg(
        "Automatic login did not complete — waiting for manual login in Chrome."
    )
    manual_login_retry(is_logged_in_linkedin, limit=5)


def login_linkedin(username: str, password: str) -> None:
    """Attempt to log into LinkedIn using the provided credentials.

    Tries the following strategies in order:
    1. Fill the username/password form at ``/login``.
    2. Click a saved-profile button if the form is not found.
    3. Fall back to :func:`manual_login_retry` with a PyAutoGUI dialog.

    Args:
        username: LinkedIn account email address.
        password: LinkedIn account password.
    """
    browser.driver.get(_LINKEDIN_LOGIN_URL)

    if username == _PLACEHOLDER_USERNAME and password == _PLACEHOLDER_PASSWORD:
        pyautogui.alert(
            "LinkedIn credentials are not configured in config/secrets.py.\n"
            "Please log in manually.",
            "Manual Login Required",
            "OK",
        )
        print_lg(
            "Default placeholder credentials detected — requesting manual login."
        )
        manual_login_retry(is_logged_in_linkedin, limit=2)
        return

    try:
        WebDriverWait(browser.driver, 20).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        credential_fields = (("username", username), ("password", password))
        for field_id, field_value in credential_fields:
            try:
                text_input_by_ID(browser.driver, field_id, field_value, 1)
            except Exception:
                field_name = (
                    "session_key" if field_id == "username" else "session_password"
                )
                element = browser.driver.find_element(By.NAME, field_name)
                element.clear()
                element.send_keys(field_value)

        browser.driver.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()
    except Exception as form_error:
        print_lg(
            "Standard login form not found — trying profile button fallback.",
            form_error,
        )
        try:
            profile_button = find_by_class(browser.driver, "profile__details")
            profile_button.click()
        except Exception as profile_error:
            print_lg(
                "Could not log in via profile button either.",
                profile_error,
            )

    try:
        WebDriverWait(browser.driver, 25).until(
            lambda driver: "feed" in (driver.current_url or "")
        )
        print_lg("Login successful!")
        return
    except Exception:
        print_lg(
            "Login attempt failed — possibly wrong credentials or already "
            "logged in. Prompting for manual login."
        )
        manual_login_retry(is_logged_in_linkedin, limit=2)
