# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""General-purpose utility functions for JobPilot AI.

Covers: directory creation, Chrome profile discovery, logging,
random delay buffers, date-string parsing, and CSV helpers.
"""

import json
import os
import pathlib
import re
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from pprint import pprint
from random import randint
from time import sleep

from pyautogui import alert

from config.settings import logs_folder_path


# ---------------------------------------------------------------------------
# Directory utilities
# ---------------------------------------------------------------------------

def make_directories(paths: list[str]) -> None:
    """Create any missing directories for the given file or folder paths.

    Args:
        paths: List of file paths or directory paths. If a path looks like
            a file path (has an extension), only the parent directory is
            created.
    """
    for path in paths:
        path = os.path.expanduser(path)
        path = path.replace("//", "/")

        if "." in os.path.basename(path):
            path = os.path.dirname(path)

        if not path:
            continue

        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        except Exception as e:
            print(f'Error creating directory "{path}": {e}')


def get_default_temp_profile() -> str:
    """Return a platform-appropriate path for a temporary Chrome user profile.

    Returns:
        Absolute path string suitable for the ``--user-data-dir`` Chrome flag.
    """
    if sys.platform.startswith("win"):
        return r"C:\temp\jobpilot-ai-profile"

    home = pathlib.Path.home()
    if sys.platform.startswith("linux"):
        return str(home / ".jobpilot-ai-profile")
    return str(
        home / "Library" / "Application Support" / "Google" / "Chrome" / "jobpilot-ai-profile"
    )


def find_default_profile_directory() -> str | None:
    """Locate the default Chrome 'User Data' directory on the current OS.

    Checks several well-known paths across Windows and Linux. macOS is
    excluded because undetected-chromedriver does not reliably create a
    session when loading a profile on that platform.

    Returns:
        Absolute path string if found, or ``None`` if not detected.
    """
    home = pathlib.Path.home()

    if sys.platform.startswith("win"):
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data"),
            os.path.expandvars(
                r"%USERPROFILE%\Local Settings\Application Data\Google\Chrome\User Data"
            ),
        ]
    elif sys.platform.startswith("linux"):
        candidates = [
            str(home / ".config" / "google-chrome"),
            str(
                home
                / ".var"
                / "app"
                / "com.google.Chrome"
                / "data"
                / ".config"
                / "google-chrome"
            ),
        ]
    else:
        return None

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


# ---------------------------------------------------------------------------
# Logging utilities
# ---------------------------------------------------------------------------

def critical_error_log(possible_reason: str, stack_trace: Exception) -> None:
    """Log a critical error with a timestamp to both console and log file.

    Args:
        possible_reason: Short human-readable description of where/why the
            error occurred.
        stack_trace: The caught exception object.
    """
    print_lg(possible_reason, stack_trace, datetime.now(), from_critical=True)


def _get_log_path() -> str:
    """Build the full path to the main log file.

    Returns:
        Normalized path string (no double slashes).
    """
    try:
        return (logs_folder_path + "/log.txt").replace("//", "/")
    except Exception as e:
        critical_error_log("Failed to resolve log path — using default 'logs/log.txt'", e)
        return "logs/log.txt"


_logs_file_path: str = _get_log_path()


def print_lg(
    *msgs: object,
    end: str = "\n",
    pretty: bool = False,
    flush: bool = False,
    from_critical: bool = False,
) -> None:
    """Print one or more messages to stdout and append them to the log file.

    ``end`` and ``flush`` are ignored when ``pretty=True``.

    Args:
        *msgs: One or more objects to log. Each is converted to string.
        end: Line ending appended after each message (default ``"\\n"``).
        pretty: If True, use ``pprint`` for richer dict/list formatting.
        flush: If True, flush stdout after each write.
        from_critical: Internal flag — prevents recursive error logging
            when called from :func:`critical_error_log`.
    """
    try:
        for message in msgs:
            pprint(message) if pretty else print(message, end=end, flush=flush)
            with open(_logs_file_path, "a+", encoding="utf-8") as f:
                f.write(str(message) + end)
    except Exception as e:
        trail = (
            f'Skipped saving message: "{message}" to log.txt!'
            if from_critical
            else "Will attempt one more log write..."
        )
        alert(
            f"log.txt in '{logs_folder_path}' is open or locked by another program! "
            f"Please close it. {trail}",
            "Logging Failed",
        )
        if not from_critical:
            critical_error_log("log.txt is open or locked by another program!", e)


# ---------------------------------------------------------------------------
# Timing utilities
# ---------------------------------------------------------------------------

def buffer(speed: int = 0) -> None:
    """Sleep for a random duration scaled by *speed* to mimic human pacing.

    Args:
        speed: Controls the sleep range:
            - ``<= 0``: no sleep
            - ``1 ≤ speed < 2``: 0.6 – 1.0 s
            - ``2 ≤ speed < 3``: 1.0 – 1.8 s
            - ``>= 3``: 1.8 – speed s
    """
    if speed <= 0:
        return
    if speed < 2:
        sleep(randint(6, 10) * 0.1)
    elif speed < 3:
        sleep(randint(10, 18) * 0.1)
    else:
        sleep(randint(18, round(speed) * 10) * 0.1)


def manual_login_retry(is_logged_in: Callable[[], bool], limit: int = 2) -> None:
    """Loop until the user manually completes a LinkedIn login.

    Prompts the user via a PyAutoGUI alert to confirm they have logged in.
    After *limit* confirmations that still fail, offers a "Skip" option.

    Args:
        is_logged_in: A callable that returns ``True`` when login is detected.
        limit: Number of confirmation attempts before showing the skip option.
    """
    count = 0
    while not is_logged_in():
        print_lg("Not logged in — waiting for manual login.")
        button = "Confirm Login"
        message = f'After you successfully log in, click "{button}" below.'
        if count > limit:
            button = "Skip Confirmation"
            message = (
                f'If you\'re still seeing this after logging in, click "{button}". '
                "Auto-confirmation may have failed."
            )
        count += 1
        if alert(message, "Login Required", button) and count > limit:
            return


# ---------------------------------------------------------------------------
# Date parsing utilities
# ---------------------------------------------------------------------------

def calculate_date_posted(time_string: str) -> datetime | None:
    """Parse a LinkedIn-style relative time string into an absolute datetime.

    Args:
        time_string: A string like ``"2 hours ago"``, ``"1 day ago"``,
            ``"3 weeks ago"``, etc.

    Returns:
        A ``datetime`` object representing the approximate posting date,
        or ``None`` if the string cannot be parsed.

    Examples:
        >>> calculate_date_posted("2 hours ago")
        datetime(...)  # 2 hours before now
        >>> calculate_date_posted("1 week ago")
        datetime(...)  # 7 days before now
    """
    time_string = time_string.strip()
    now = datetime.now()

    match = re.search(
        r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago",
        time_string,
        re.IGNORECASE,
    )
    if not match:
        return None

    try:
        value = int(match.group(1))
        unit = match.group(2).lower()

        deltas = {
            "second": timedelta(seconds=value),
            "minute": timedelta(minutes=value),
            "hour": timedelta(hours=value),
            "day": timedelta(days=value),
            "week": timedelta(weeks=value),
            "month": timedelta(days=value * 30),
            "year": timedelta(days=value * 365),
        }
        return now - deltas.get(unit, timedelta(0))
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Data-conversion utilities
# ---------------------------------------------------------------------------

def convert_to_lakhs(value: str) -> str:
    """Convert a numeric string to a lakh-formatted string (Indian numbering).

    No validation is performed beyond stripping whitespace.

    Args:
        value: Numeric string, e.g. ``"2400000"``.

    Returns:
        Lakh-formatted string, e.g. ``"24.00"``.

    Examples:
        >>> convert_to_lakhs("2400000")
        '24.00'
        >>> convert_to_lakhs("850000")
        '8.50'
    """
    value = value.strip()
    length = len(value)
    if length > 5:
        return value[: length - 5] + "." + value[length - 5 : length - 3]
    return "0." + "0" * (5 - length) + value[:2]


def convert_to_json(data: object) -> dict:
    """Attempt to parse *data* as JSON.

    Args:
        data: Any object. If it is a ``str``, it is parsed with
            ``json.loads``; otherwise it is returned as-is.

    Returns:
        Parsed dict, or ``{"error": "Unable to parse...", "data": data}``
        on failure.
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {"error": "Unable to parse the response as JSON", "data": data}


def truncate_for_csv(
    data: object,
    max_length: int = 131000,
    suffix: str = "...[TRUNCATED]",
) -> str:
    """Convert *data* to a string and truncate if it exceeds *max_length*.

    Used before writing to CSV to avoid hitting field-size limits.

    Args:
        data: Any Python object. ``None`` becomes an empty string.
        max_length: Maximum allowed character count (default 131 000).
        suffix: Text appended to truncated output.

    Returns:
        A string of at most ``max_length + len(suffix)`` characters.
    """
    try:
        text = str(data) if data is not None else ""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix
    except Exception as e:
        return f"[ERROR CONVERTING DATA: {e}]"
