# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Low-level Selenium helper functions for JobPilot AI.

All functions in this module are thin wrappers around Selenium's WebDriver
API. They exist to centralise common patterns (wait-then-click, scroll-
to-view, robust element lookup) and to insulate the rest of the codebase
from repetitive try/except boilerplate.
"""

from config.settings import click_gap, smooth_scroll
from modules.helpers import buffer, print_lg, sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains

# WebDriver or nested WebElement — both support find_element / WebDriverWait.
SearchContext = WebDriver | WebElement


# ---------------------------------------------------------------------------
# Click helpers
# ---------------------------------------------------------------------------

def click_action(
    driver: SearchContext,
    text: str,
    time: float = 5.0,
    click: bool = True,
    scroll: bool = True,
    scrollTop: bool = False,
) -> WebElement | bool:
    """Click a button or span by visible text (LinkedIn Easy Apply compatible).

    Tries multiple XPath patterns because LinkedIn uses both ``<span>`` and
    ``<button>`` labels, and sometimes nests text inside ``aria-label``.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        text: Visible label text to match.
        time: Max seconds to wait for each XPath attempt.
        click: If ``True``, click the element when found.
        scroll: If ``True``, scroll the element into view before clicking.
        scrollTop: If ``True``, align the element to the top of the viewport.

    Returns:
        The located ``WebElement`` on success, or ``False`` if no match is found.
    """
    if not text:
        return False

    xpaths = [
        f'.//span[normalize-space(.)="{text}"]',
        f'.//button[normalize-space(.)="{text}"]',
        f'.//button[.//span[normalize-space(.)="{text}"]]',
        f'.//span[contains(normalize-space(.), "{text}")]',
        f'.//button[contains(@aria-label, "{text}")]',
    ]

    for xpath in xpaths:
        try:
            button = WebDriverWait(driver, time).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if scroll:
                scroll_to_view(driver, button, scrollTop)
            if click:
                button.click()
                buffer(click_gap)
            return button
        except Exception:
            continue

    print_lg(f"Click failed — could not find action '{text}'")
    return False


def wait_span_click(
    driver: SearchContext,
    text: str,
    time: float = 5.0,
    click: bool = True,
    scroll: bool = True,
    scrollTop: bool = False,
) -> WebElement | bool:
    """Find a ``<span>`` with exact text, optionally scroll to it and click it.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        text: Exact span text to match.
        time: Max seconds to wait for the element.
        click: If ``True``, click the element when found.
        scroll: If ``True``, scroll the element into view before clicking.
        scrollTop: If ``True``, align the element to the top of the viewport.

    Returns:
        The located ``WebElement`` on success, or ``False`` if not found.
    """
    return click_action(driver, text, time, click, scroll, scrollTop)


def multi_sel(driver: SearchContext, texts: list[str], time: float = 5.0) -> None:
    """Click every element in *texts*, waiting up to *time* seconds each.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        texts: List of visible label texts to click in order.
        time: Max seconds to wait for each click attempt.
    """
    for text in texts:
        click_action(driver, text, time)


def multi_sel_noWait(
    driver: SearchContext,
    texts: list[str],
    actions: ActionChains | None = None,
) -> None:
    """Click each span in *texts* without waiting for page load.

    If an element is not immediately found and *actions* is provided,
    falls back to :func:`company_search_click` to add it via the search box.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        texts: List of span text values to click.
        actions: Optional ActionChains for company-search fallback.
    """
    for text in texts:
        try:
            button = driver.find_element(
                By.XPATH, f'.//span[normalize-space(.)="{text}"]'
            )
            scroll_to_view(driver, button)
            button.click()
            buffer(click_gap)
        except Exception:
            if actions:
                company_search_click(driver, actions, text)
            else:
                print_lg(f"Click failed — could not find '{text}'")


def boolean_button_click(
    driver: SearchContext,
    actions: ActionChains,
    text: str,
) -> None:
    """Toggle a boolean/switch button identified by its visible heading text.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        actions: ActionChains used for the click (handles intercept-safe clicks).
        text: The ``<h3>`` text that labels the toggle fieldset.
    """
    try:
        list_container = driver.find_element(
            By.XPATH, f'.//h3[normalize-space()="{text}"]/ancestor::fieldset'
        )
        button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
        scroll_to_view(driver, button)
        actions.move_to_element(button).click().perform()
        buffer(click_gap)
    except Exception:
        print_lg(f"Click failed — could not find boolean button '{text}'")


# ---------------------------------------------------------------------------
# Find helpers
# ---------------------------------------------------------------------------

def find_by_class(
    driver: SearchContext,
    class_name: str,
    time: float = 5.0,
) -> WebElement:
    """Wait for and return an element by its CSS class name.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        class_name: CSS class name to locate.
        time: Max seconds to wait.

    Returns:
        The located ``WebElement``.

    Raises:
        TimeoutException: If the element is not found within *time* seconds.
    """
    return WebDriverWait(driver, time).until(
        EC.presence_of_element_located((By.CLASS_NAME, class_name))
    )


def try_find_by_classes(driver: SearchContext, classes: list[str]) -> WebElement:
    """Try each class name in *classes* and return the first element found.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        classes: List of CSS class names to try in order.

    Returns:
        The first located ``WebElement``.

    Raises:
        ValueError: If none of the class names produces a match.
    """
    for cls in classes:
        try:
            return driver.find_element(By.CLASS_NAME, cls)
        except Exception:
            pass
    raise ValueError(f"Could not find an element matching any of: {classes}")


def try_xp(
    driver: SearchContext,
    xpath: str,
    click: bool = True,
) -> WebElement | bool:
    """Attempt to find (and optionally click) an element by XPath.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        xpath: XPath expression to evaluate.
        click: If ``True``, click the element if found.

    Returns:
        ``True`` (click mode) or the ``WebElement`` (no-click mode) on
        success; ``False`` if the element is not found.
    """
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click()
            return True
        return driver.find_element(By.XPATH, xpath)
    except Exception:
        return False


def try_linkText(driver: SearchContext, link_text: str) -> WebElement | bool:
    """Return an anchor element by its visible link text, or False if absent.

    Args:
        driver: Active WebDriver or scoped WebElement to search within.
        link_text: Exact visible text of the link.

    Returns:
        The ``WebElement`` or ``False``.
    """
    try:
        return driver.find_element(By.LINK_TEXT, link_text)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Scroll helpers
# ---------------------------------------------------------------------------

def scroll_to_view(
    driver: SearchContext,
    element: WebElement,
    top: bool = False,
    smooth: bool = smooth_scroll,
) -> None:
    """Scroll *element* into the visible viewport.

    Args:
        driver: Active WebDriver used to execute scroll scripts.
        element: The element to scroll to.
        top: If ``True``, align element to the top of the viewport.
        smooth: If ``True``, use CSS smooth scrolling behavior.
    """
    if top:
        driver.execute_script("arguments[0].scrollIntoView();", element)
        return
    behavior = "smooth" if smooth else "instant"
    driver.execute_script(
        f'arguments[0].scrollIntoView({{block: "center", behavior: "{behavior}"}});',
        element,
    )


# ---------------------------------------------------------------------------
# Text input helpers
# ---------------------------------------------------------------------------

def text_input_by_ID(
    driver: WebDriver,
    element_id: str,
    value: str,
    time: float = 5.0,
) -> None:
    """Clear and type *value* into an input field located by its HTML ``id``.

    Args:
        driver: Active WebDriver instance.
        element_id: The ``id`` attribute of the input element.
        value: Text to type into the field.
        time: Max seconds to wait for the element.

    Raises:
        TimeoutException: If the element is not found within *time* seconds.
    """
    field = WebDriverWait(driver, time).until(
        EC.presence_of_element_located((By.ID, element_id))
    )
    field.send_keys(Keys.CONTROL + "a")
    field.send_keys(value)


def text_input(
    actions: ActionChains,
    text_input_element: WebElement | bool,
    value: str,
    field_name: str = "Text",
) -> None:
    """Clear and type *value* into a text input, then confirm with Enter.

    Used for search boxes and location fields that require an explicit
    selection from a dropdown after typing.

    Args:
        actions: Active ActionChains instance.
        text_input_element: The input ``WebElement``, or ``False`` to skip.
        value: Text to type.
        field_name: Human-readable name used in log messages.
    """
    if text_input_element:
        sleep(1)
        text_input_element.clear()
        text_input_element.send_keys(value.strip())
        sleep(2)
        actions.send_keys(Keys.ENTER).perform()
    else:
        print_lg(f"{field_name} input element was not found — skipping.")


def company_search_click(
    driver: WebDriver,
    actions: ActionChains,
    company_name: str,
) -> None:
    """Search for and select a company in the LinkedIn company filter search box.

    Args:
        driver: Active WebDriver instance.
        actions: Active ActionChains for keyboard navigation.
        company_name: Exact company name to search and select.
    """
    wait_span_click(driver, "Add a company", 1)
    search_box = driver.find_element(
        By.XPATH, "(.//input[@placeholder='Add a company'])[1]"
    )
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(company_name)
    buffer(3)
    actions.send_keys(Keys.DOWN).perform()
    actions.send_keys(Keys.ENTER).perform()
    print_lg(f'Searched and added company filter: "{company_name}"')
