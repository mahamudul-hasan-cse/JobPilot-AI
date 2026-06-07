# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Preflight checks before JobPilot AI starts.

Validates configuration and verifies that required Python packages are
installed before the main application launches.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

REQUIRED_PACKAGES: tuple[str, ...] = (
    "selenium",
    "pyautogui",
    "undetected_chromedriver",
    "google.generativeai",
)


def main() -> int:
    """Run configuration and dependency checks for JobPilot AI.

    Validates project configuration, then attempts to import each package
    listed in :data:`REQUIRED_PACKAGES`.

    Returns:
        ``0`` when all checks pass; ``1`` when one or more packages are
        missing.
    """
    from modules.validator import validate_config

    validate_config()
    print("Config OK")

    missing_packages: list[str] = []
    for package_name in REQUIRED_PACKAGES:
        try:
            __import__(package_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        print("Missing Python packages:", ", ".join(missing_packages))
        print(f"Python executable: {sys.executable}")
        print("Fix: pip install -r requirements.txt")
        return 1

    print("Dependencies OK")
    print(f"Python: {sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
