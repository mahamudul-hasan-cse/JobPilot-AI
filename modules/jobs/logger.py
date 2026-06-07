# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""CSV logging and screenshot utilities for JobPilot AI.

Handles reading applied-job IDs, writing success and failure rows to CSV,
and capturing debug screenshots.
"""

import csv
from datetime import datetime
from typing import Literal

import pyautogui
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import failed_file_name, file_name, logs_folder_path
from modules.helpers import print_lg, truncate_for_csv


def get_applied_job_ids() -> set[str]:
    """Read the set of already-applied job IDs from the history CSV.

    Returns:
        A set of job ID strings. Returns an empty set if the CSV file does
        not yet exist.
    """
    applied_job_ids: set[str] = set()
    try:
        with open(file_name, "r", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                if row:
                    applied_job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"History CSV '{file_name}' not found — starting fresh.")
    return applied_job_ids


def submitted_jobs(
    job_id: str,
    title: str,
    company: str,
    work_location: str,
    work_style: str,
    description: str,
    experience_required: int | Literal["Unknown", "Error in extraction"],
    skills: list[str] | str,
    hr_name: str,
    hr_link: str,
    resume: str,
    reposted: bool,
    date_listed: datetime | str,
    date_applied: datetime | str,
    job_link: str,
    application_link: str,
    questions_list: set[tuple[str, str, str, str]] | None,
    connect_request: str,
    relevance_score: int | str = "N/A",
) -> None:
    """Append a successfully applied or collected job to the history CSV.

    Creates the CSV with headers on the first write. Truncates long fields
    to avoid exceeding the CSV field-size limit.

    Args:
        job_id: LinkedIn numeric job ID.
        title: Job title.
        company: Company name.
        work_location: Work location string.
        work_style: ``"Remote"``, ``"Hybrid"``, or ``"On-site"``.
        description: Full job description text.
        experience_required: Parsed years of experience, or a sentinel string.
        skills: Extracted skills dict or list, or a placeholder string.
        hr_name: Hiring manager name if found, else ``"Unknown"``.
        hr_link: Hiring manager LinkedIn URL, else ``"Unknown"``.
        resume: Path of the uploaded resume, or ``"Previous resume"``.
        reposted: ``True`` if the listing was marked as reposted.
        date_listed: Approximate posting date or ``"Unknown"``.
        date_applied: Application submission datetime or ``"Pending"``.
        job_link: Full LinkedIn job URL.
        application_link: External apply URL or ``"Easy Applied"``.
        questions_list: Set of ``(label, answer, type, prev)`` tuples.
        connect_request: Connection request status (``"In Development"``).
        relevance_score: AI-computed relevance score (0–100) or ``"N/A"``.
    """
    try:
        with open(file_name, mode="a", newline="", encoding="utf-8") as csv_file:
            fieldnames = [
                "Job ID",
                "Title",
                "Company",
                "Work Location",
                "Work Style",
                "About Job",
                "Experience required",
                "Skills required",
                "HR Name",
                "HR Link",
                "Resume",
                "Re-posted",
                "Date Posted",
                "Date Applied",
                "Job Link",
                "External Job link",
                "Questions Found",
                "Connect Request",
                "Relevance Score",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow(
                {
                    "Job ID": truncate_for_csv(job_id),
                    "Title": truncate_for_csv(title),
                    "Company": truncate_for_csv(company),
                    "Work Location": truncate_for_csv(work_location),
                    "Work Style": truncate_for_csv(work_style),
                    "About Job": truncate_for_csv(description),
                    "Experience required": truncate_for_csv(experience_required),
                    "Skills required": truncate_for_csv(skills),
                    "HR Name": truncate_for_csv(hr_name),
                    "HR Link": truncate_for_csv(hr_link),
                    "Resume": truncate_for_csv(resume),
                    "Re-posted": truncate_for_csv(reposted),
                    "Date Posted": truncate_for_csv(date_listed),
                    "Date Applied": truncate_for_csv(date_applied),
                    "Job Link": truncate_for_csv(job_link),
                    "External Job link": truncate_for_csv(application_link),
                    "Questions Found": truncate_for_csv(questions_list),
                    "Connect Request": truncate_for_csv(connect_request),
                    "Relevance Score": truncate_for_csv(relevance_score),
                }
            )
    except Exception as exc:
        print_lg("Failed to write to applied jobs CSV!", exc)
        pyautogui.alert(
            "Failed to update the applied-jobs spreadsheet!\n\n"
            "Possible causes:\n"
            "1. The file is currently open in another program.\n"
            "2. Write permission denied.\n"
            "3. File path not found.",
            "CSV Write Error",
        )


def failed_job(
    job_id: str,
    job_link: str,
    resume: str,
    date_listed: datetime | str,
    error: str,
    exception: Exception,
    application_link: str,
    screenshot_name: str,
) -> None:
    """Append a failed or skipped job to the failures CSV.

    Args:
        job_id: LinkedIn job ID.
        job_link: Full LinkedIn job URL.
        resume: Resume path that was attempted.
        date_listed: Approximate posting date.
        error: Short reason string (used as the Assumed Reason column).
        exception: The caught exception for stack trace logging.
        application_link: External URL if available, else ``"Skipped"``.
        screenshot_name: Filename of the debug screenshot, or
            ``"Not Available"``.
    """
    try:
        with open(failed_file_name, "a", newline="", encoding="utf-8") as csv_file:
            fieldnames = [
                "Job ID",
                "Job Link",
                "Resume Tried",
                "Date listed",
                "Date Tried",
                "Assumed Reason",
                "Stack Trace",
                "External Job link",
                "Screenshot Name",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow(
                {
                    "Job ID": truncate_for_csv(job_id),
                    "Job Link": truncate_for_csv(job_link),
                    "Resume Tried": truncate_for_csv(resume),
                    "Date listed": truncate_for_csv(date_listed),
                    "Date Tried": datetime.now(),
                    "Assumed Reason": truncate_for_csv(error),
                    "Stack Trace": truncate_for_csv(exception),
                    "External Job link": truncate_for_csv(application_link),
                    "Screenshot Name": truncate_for_csv(screenshot_name),
                }
            )
    except Exception as exc:
        print_lg("Failed to write to failed jobs CSV!", exc)
        pyautogui.alert(
            "Failed to update the failed-jobs spreadsheet!\n\n"
            "Possible causes:\n"
            "1. The file is currently open in another program.\n"
            "2. Write permission denied.\n"
            "3. File path not found.",
            "CSV Write Error",
        )


def screenshot(driver: WebDriver, job_id: str, failed_at: str) -> str:
    """Take a screenshot and save it to the logs/screenshots folder.

    The filename encodes the job ID, failure stage, and timestamp for easy
    identification during post-run debugging.

    Args:
        driver: Active WebDriver instance.
        job_id: LinkedIn job ID for the current job.
        failed_at: Short label describing where the failure occurred.

    Returns:
        The screenshot filename (without path), or ``"Screenshot failed"`` if
        the save operation raises an exception.
    """
    try:
        screenshot_name = f"{job_id} - {failed_at} - {datetime.now()}.png"
        screenshot_path = (
            logs_folder_path + "/screenshots/" + screenshot_name.replace(":", ".")
        ).replace("//", "/")
        driver.save_screenshot(screenshot_path)
        return screenshot_name
    except Exception as exc:
        print_lg("Failed to take screenshot.", exc)
        return "Screenshot failed"
