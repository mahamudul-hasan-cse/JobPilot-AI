# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""JobPilot AI — Entry Point.

Run this file to start the bot:

    python main.py

The bot will:
  1. Validate all config files.
  2. Open a Chrome browser window.
  3. Log into LinkedIn.
  4. Search for jobs and automatically apply.
  5. Log results to CSV files in ``all excels/``.
"""

from typing import Any

import os
import pyautogui
from datetime import datetime

from selenium.common.exceptions import (
    NoSuchWindowException,
    InvalidSessionIdException,
    WebDriverException,
)

from typing import Any

from modules.validator import validate_config
from modules.browser.session import init_session
import modules.browser.session as browser
from modules.auth import ensure_linkedin_login
from modules.helpers import print_lg, critical_error_log, buffer, sleep
from modules.jobs.applier import apply_to_jobs, get_summary

from config.secrets import (
    username, password,
    use_AI, ai_provider,
    use_relevance_scoring, ai_relevance_threshold,
)
from config.questions import default_resume_path
from config.settings import (
    run_non_stop, alternate_sortby, cycle_date_posted,
    stop_date_cycle_at_24hr, run_in_background,
)
from config.search import search_terms

pyautogui.FAILSAFE = False

# ---------------------------------------------------------------------------
# Globals adjusted at runtime
# ---------------------------------------------------------------------------
_current_date_posted: str = ""
_current_sort_by: str = ""


def _run_cycle(total_runs: int, ai_client: Any, linkedin_tab: str) -> int:
    """Execute one full application cycle across all configured search terms.

    Args:
        total_runs: The current run counter (shown in logs).
        ai_client: Active AI client, or ``None`` if AI is disabled.
        linkedin_tab: Browser window handle for the LinkedIn tab.

    Returns:
        Incremented run counter.
    """
    summary = get_summary()
    if summary["daily_limit_reached"]:
        return total_runs

    print_lg("\n" + "#" * 120)
    print_lg(f"Date/Time    : {datetime.now()}")
    print_lg(f"Cycle number : {total_runs}")

    browser.driver.switch_to.window(linkedin_tab)
    apply_to_jobs(search_terms, ai_client=ai_client, linkedin_tab=linkedin_tab)
    print_lg("#" * 120 + "\n")

    summary = get_summary()
    if run_non_stop and not summary["daily_limit_reached"]:
        print_lg("Sleeping 10 minutes before next cycle...")
        sleep(300)
        print_lg("Almost ready — resuming in ~5 min...")
        sleep(300)

    buffer(3)
    return total_runs + 1


def main() -> None:
    """Bootstrap JobPilot AI and run the application loop."""
    global _current_date_posted, _current_sort_by

    total_runs = 1
    linkedin_tab: str = ""
    ai_client = None

    try:
        # ------------------------------------------------------------------ #
        # 1. Validate config
        # ------------------------------------------------------------------ #
        validate_config()

        from modules.ai.scoring import reset_ai_quota_circuit
        reset_ai_quota_circuit()

        # ------------------------------------------------------------------ #
        # 2. Open Chrome (lazy init — after config is valid)
        # ------------------------------------------------------------------ #
        init_session()

        # ------------------------------------------------------------------ #
        # 3. Check resume exists
        # ------------------------------------------------------------------ #
        if not os.path.exists(default_resume_path):
            pyautogui.alert(
                f'Default resume not found at:\n  "{default_resume_path}"\n\n'
                "Update default_resume_path in config/questions.py, or place your resume at that path.\n\n"
                "For now, the bot will use your previously uploaded resume on LinkedIn.",
                "Missing Resume",
                "OK",
            )
            from modules.jobs import applier as _applier_mod
            _applier_mod._use_new_resume = False

        # ------------------------------------------------------------------ #
        # 4. Login to LinkedIn
        # ------------------------------------------------------------------ #
        ensure_linkedin_login(username, password)

        linkedin_tab = browser.driver.current_window_handle

        # ------------------------------------------------------------------ #
        # 5. Initialise AI client
        # ------------------------------------------------------------------ #
        if use_AI:
            from modules.ai.client_factory import create_ai_client
            ai_client = create_ai_client(ai_provider)
            if ai_client is None:
                pyautogui.alert(
                    f"Failed to create {ai_provider} AI client.\n"
                    "Check your API key and model name in config/secrets.py.\n\n"
                    "The bot will continue WITHOUT AI features.",
                    "AI Client Error",
                    "OK",
                )

            if use_relevance_scoring:
                print_lg(
                    f"AI Relevance Scoring ENABLED — threshold: {ai_relevance_threshold}/100"
                )
            from config.questions import use_resume_tailoring
            if use_resume_tailoring:
                print_lg("AI Resume Tailoring ENABLED — cover letters will be tailored per job.")

        # ------------------------------------------------------------------ #
        # 6. Read initial filter settings from config
        # ------------------------------------------------------------------ #
        import config.search as _search_cfg
        _current_date_posted = _search_cfg.date_posted
        _current_sort_by = _search_cfg.sort_by

        # ------------------------------------------------------------------ #
        # 7. Run
        # ------------------------------------------------------------------ #
        total_runs = _run_cycle(total_runs, ai_client, linkedin_tab)

        while run_non_stop:
            # Cycle date_posted filter
            if cycle_date_posted:
                _date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                current_idx = _date_options.index(_current_date_posted) if _current_date_posted in _date_options else -1
                if stop_date_cycle_at_24hr:
                    _current_date_posted = _date_options[
                        current_idx + 1 if current_idx + 1 < len(_date_options) else -1
                    ]
                else:
                    _current_date_posted = _date_options[
                        0 if current_idx + 1 >= len(_date_options) else current_idx + 1
                    ]
                _search_cfg.date_posted = _current_date_posted

            # Alternate sort_by
            if alternate_sortby:
                _search_cfg.sort_by = "Most recent" if _current_sort_by == "Most relevant" else "Most relevant"
                total_runs = _run_cycle(total_runs, ai_client, linkedin_tab)
                _current_sort_by = _search_cfg.sort_by
                _search_cfg.sort_by = "Most recent" if _current_sort_by == "Most relevant" else "Most relevant"

            total_runs = _run_cycle(total_runs, ai_client, linkedin_tab)

            if get_summary()["daily_limit_reached"]:
                break

    except (NoSuchWindowException, InvalidSessionIdException) as e:
        print_lg("Browser closed or session invalid — exiting.", e)
    except WebDriverException as e:
        if "invalid session id" in str(e).lower() or "no such window" in str(e).lower():
            print_lg("Browser closed or session invalid — exiting.", e)
        else:
            critical_error_log("In JobPilot AI main()", e)
            pyautogui.alert(str(e), "Error — Closing JobPilot AI")
    except Exception as e:
        critical_error_log("In JobPilot AI main()", e)
        pyautogui.alert(str(e), "Error — Closing JobPilot AI")
    finally:
        # ------------------------------------------------------------------ #
        # 7. Summary
        # ------------------------------------------------------------------ #
        summary = get_summary()
        easy = summary["easy_applied"]
        ext = summary["external"]
        failed = summary["failed"]
        skipped = summary["skipped"]
        total = easy + ext

        summary_text = (
            f"Total runs          : {total_runs}\n"
            f"Easy Applied        : {easy}\n"
            f"External links saved: {ext}\n"
            f"------------------------------\n"
            f"Total               : {total}\n"
            f"Failed              : {failed}\n"
            f"Skipped (irrelevant): {skipped}\n"
        )
        print_lg("\n\nRun Summary\n" + "=" * 40)
        print_lg(summary_text)

        from modules.ai.scoring import is_ai_quota_exhausted
        if is_ai_quota_exhausted():
            print_lg(
                "NOTE: Gemini quota was exceeded during this run. "
                "AI scoring/Q&A was disabled for the remainder of the session."
            )

        # Close AI client
        if use_AI and ai_client:
            try:
                from modules.ai.client_factory import close_ai_client
                close_ai_client(ai_client, ai_provider)
            except Exception as e:
                print_lg("Could not close AI client.", e)

        # Final alert
        pyautogui.alert(
            f"JobPilot AI run complete.\n\n{summary_text}\n"
            "Check the 'all excels/' folder for detailed results.",
            "JobPilot AI — Done",
        )

        # Close browser
        try:
            if browser.driver:
                browser.driver.quit()
        except WebDriverException:
            print_lg("Browser already closed.")
        except Exception as e:
            critical_error_log("When quitting browser", e)


if __name__ == "__main__":
    main()
