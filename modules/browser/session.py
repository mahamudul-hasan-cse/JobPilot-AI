# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Browser session management for JobPilot AI.

Chrome is **not** opened on import. Call :func:`init_session` from ``main.py``
after config validation to launch the browser and populate ``driver``,
``wait``, and ``actions``.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from modules.helpers import (
    get_default_temp_profile,
    make_directories,
    find_default_profile_directory,
    critical_error_log,
    print_lg,
)
from config.settings import (
    run_in_background,
    stealth_mode,
    disable_extensions,
    safe_mode,
    file_name,
    failed_file_name,
    logs_folder_path,
    generated_resume_path,
    chrome_user_data_dir,
    chrome_profile_directory,
    implicit_wait,
    page_load_timeout,
)
from config.questions import default_resume_path

# Module-level session handles (None until init_session() is called)
options: Options | None = None
driver: WebDriver | None = None
actions: ActionChains | None = None
wait: WebDriverWait | None = None
_initialized: bool = False
_chrome_process: subprocess.Popen[bytes] | subprocess.Popen[str] | None = None
_debug_port: int = 9222


def _automation_profile_dir() -> Path:
    """Return the dedicated Chrome user-data directory for JobPilot AI.

    Using a separate folder avoids Chrome's profile-picker dialog during
    automation runs.

    Returns:
        Path to the ``~/.jobpilot-ai/chrome-mahamudul`` directory.
    """
    return Path.home() / ".jobpilot-ai" / "chrome-mahamudul"


def _prepare_automation_profile(source_user_data: str, profile_name: str) -> str:
    """Copy the chosen Chrome profile into a dedicated automation user-data folder.

    Args:
        source_user_data: Path to the source Chrome ``User Data`` directory.
        profile_name: Chrome profile folder name (e.g. ``"Default"``).

    Returns:
        Absolute path to the automation user-data root directory.

    Raises:
        FileNotFoundError: If the source profile folder does not exist.
    """
    src_profile = Path(source_user_data) / profile_name
    if not src_profile.is_dir():
        raise FileNotFoundError(f'Chrome profile folder not found: {src_profile}')

    auto_root = _automation_profile_dir()
    dest_default = auto_root / "Default"
    src_cookie = src_profile / "Network" / "Cookies"
    dest_cookie = dest_default / "Network" / "Cookies"
    src_local_state = Path(source_user_data) / "Local State"
    dest_local_state = auto_root / "Local State"

    src_newer = (
        src_cookie.exists()
        and dest_cookie.exists()
        and src_cookie.stat().st_mtime > dest_cookie.stat().st_mtime
    )
    needs_copy = (
        not dest_default.is_dir()
        or not dest_cookie.exists()
        or not dest_local_state.exists()
        or src_newer
    )

    if needs_copy:
        print_lg(f'Syncing Chrome profile "{profile_name}" into JobPilot AI automation folder...')
        auto_root.mkdir(parents=True, exist_ok=True)
        if dest_default.exists():
            shutil.rmtree(dest_default, ignore_errors=True)
        shutil.copytree(src_profile, dest_default)
        # Local State holds the cookie encryption key — required for saved sessions
        if src_local_state.is_file():
            shutil.copy2(src_local_state, auto_root / "Local State")
        print_lg("Profile sync complete.")

    return str(auto_root)


def _find_chrome_executable() -> str:
    """Locate the Google Chrome executable on Windows.

    Returns:
        Absolute path to ``chrome.exe``.

    Raises:
        FileNotFoundError: If Chrome is not installed in any known location.
    """
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError("Google Chrome executable not found.")


def _kill_chrome_processes() -> None:
    """Terminate Chrome and chromedriver processes that may lock the profile.

    No-op on non-Windows platforms.
    """
    if not sys.platform.startswith("win"):
        return
    for proc in ("chrome.exe", "chromedriver.exe"):
        subprocess.run(
            ["taskkill", "/F", "/IM", proc, "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    time.sleep(2)


def _wait_for_debug_port(port: int, timeout: int = 60) -> bool:
    """Wait until Chrome's remote-debugging port accepts TCP connections.

    Args:
        port: Remote debugging port number.
        timeout: Maximum seconds to wait before giving up.

    Returns:
        ``True`` if the port became reachable; ``False`` on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _start_chrome_with_profile(profile_dir: str, port: int) -> None:
    """Launch Chrome with a dedicated user-data dir and remote debugging enabled.

    Args:
        profile_dir: Chrome ``--user-data-dir`` path.
        port: Remote debugging port to expose.

    Raises:
        FileNotFoundError: If Chrome executable cannot be found.
        TimeoutError: If the debugging port does not open in time.
    """
    global _chrome_process

    chrome_exe = _find_chrome_executable()
    cmd = [
        chrome_exe,
        f"--remote-debugging-port={port}",
        f'--user-data-dir={profile_dir}',
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-popup-blocking",
        "https://www.linkedin.com/feed/",
    ]
    if run_in_background:
        cmd.append("--headless=new")
    if disable_extensions:
        cmd.append("--disable-extensions")

    print_lg(f"Launching Chrome with JobPilot AI profile on port {port}")
    _chrome_process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_for_debug_port(port):
        raise TimeoutError(f"Chrome did not open debugging port {port} in time.")
    time.sleep(8)


def _attach_to_chrome(port: int) -> WebDriver:
    """Attach Selenium to an already running Chrome instance.

    Args:
        port: Remote debugging port Chrome is listening on.

    Returns:
        A Selenium ``WebDriver`` connected to the running browser.
    """
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    return webdriver.Chrome(options=opts)


def _launch_stealth_temp(temp_dir: str) -> WebDriver:
    """Launch undetected Chrome with a temporary guest profile.

    Args:
        temp_dir: Temporary user-data directory path.

    Returns:
        An undetected-chromedriver ``WebDriver`` instance.
    """
    import undetected_chromedriver as uc

    opts = uc.ChromeOptions()
    if run_in_background:
        opts.add_argument("--headless")
    if disable_extensions:
        opts.add_argument("--disable-extensions")
    opts.add_argument("--no-first-run")
    opts.add_argument("--start-maximized")

    version = _get_chrome_major_version()
    kwargs: dict[str, object] = {"options": opts, "user_data_dir": temp_dir}
    if version:
        print_lg(f"Detected Chrome version: {version}")
        kwargs["version_main"] = version
    print_lg("Launching Chrome (stealth guest profile)...")
    return uc.Chrome(**kwargs)


def _get_chrome_major_version() -> int | None:
    """Return installed Chrome major version (e.g. 148), or None if unknown.

    Returns:
        Major version integer, or ``None`` when detection fails.
    """
    try:
        import winreg

        reg_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon"),
        ]
        for hive, subkey in reg_paths:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                    return int(str(version).split(".")[0])
            except OSError:
                continue
    except Exception:
        pass
    return None


def create_chrome_session(
    force_guest: bool = False,
) -> tuple[Options, WebDriver, ActionChains, WebDriverWait]:
    """Create and return a configured Chrome WebDriver session.

    Args:
        force_guest: When ``True``, skip the saved profile and open a guest
            session even if a profile is configured.

    Returns:
        A 4-tuple of ``(options, driver, actions, wait)``.
    """
    global _debug_port

    make_directories([
        file_name,
        failed_file_name,
        logs_folder_path + "/screenshots",
        default_resume_path,
        generated_resume_path + "/temp",
        get_default_temp_profile(),
    ])

    print_lg("NOTE: Close all Chrome windows before starting.")

    profile_dir = (chrome_user_data_dir.strip() or find_default_profile_directory() or "")
    profile_name = (chrome_profile_directory or "").strip()
    use_saved_profile = bool(profile_dir and profile_name and not safe_mode and not force_guest)

    if use_saved_profile:
        automation_dir = _prepare_automation_profile(profile_dir, profile_name)
        _start_chrome_with_profile(automation_dir, _debug_port)
        drv = _attach_to_chrome(_debug_port)
        opts = Options()
    elif stealth_mode:
        temp_dir = get_default_temp_profile()
        print_lg(f"Opening temporary guest profile: {temp_dir}")
        drv = _launch_stealth_temp(temp_dir)
        opts = drv.options if hasattr(drv, "options") else Options()
    else:
        temp_dir = get_default_temp_profile()
        opts = Options()
        opts.add_argument(f"--user-data-dir={temp_dir}")
        opts.add_argument("--no-first-run")
        opts.add_argument("--start-maximized")
        print_lg(f"Opening temporary profile: {temp_dir}")
        drv = webdriver.Chrome(options=opts)

    try:
        drv.maximize_window()
    except Exception:
        pass

    drv.set_page_load_timeout(page_load_timeout)
    drv.implicitly_wait(implicit_wait)
    w = WebDriverWait(drv, implicit_wait)
    act = ActionChains(drv)
    return opts, drv, act, w


def init_session() -> None:
    """Launch Chrome and populate module-level session globals.

    Retries once on failure, then falls back to a guest profile when a saved
    profile was configured. Exits the process if all attempts fail.

    Raises:
        SystemExit: If Chrome cannot be opened after all retry and fallback
            attempts.
    """
    global options, driver, actions, wait, _initialized

    if _initialized and driver is not None:
        return

    _kill_chrome_processes()

    mode_label = "guest (stealth)" if safe_mode else f'saved profile "{chrome_profile_directory}"'
    print_lg(f"Chrome mode: {mode_label}")

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            options, driver, actions, wait = create_chrome_session()
            _initialized = True
            return
        except Exception as e:
            last_error = e
            critical_error_log(f"Chrome session attempt {attempt + 1} failed", e)
            _kill_chrome_processes()
            time.sleep(3)

    if not safe_mode:
        print_lg("Saved profile failed — falling back to guest Chrome + auto login.")
        try:
            options, driver, actions, wait = create_chrome_session(force_guest=True)
            _initialized = True
            return
        except Exception as fallback_err:
            last_error = fallback_err
            critical_error_log("Guest fallback also failed", fallback_err)

    msg = (
        "Could not open Chrome.\n\n"
        "1. Close ALL Chrome windows\n"
        "2. Run start_jobpilotai.bat again\n"
        "3. If it persists, set stealth_mode = False in config/settings.py"
    )
    print_lg(msg)
    from pyautogui import alert
    alert(msg, "Error Opening Chrome")
    raise SystemExit(1) from last_error


def get_session() -> tuple[
    WebDriver | None,
    WebDriverWait | None,
    ActionChains | None,
    Options | None,
]:
    """Return the active browser session, initialising Chrome if needed.

    Returns:
        A 4-tuple of ``(driver, wait, actions, options)``.
    """
    init_session()
    return driver, wait, actions, options
