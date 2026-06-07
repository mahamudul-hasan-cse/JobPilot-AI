# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Configuration validator for JobPilot AI.

Validates all settings in the ``config/`` directory at startup.
Raises ``TypeError`` or ``ValueError`` with clear, actionable messages
if any value is missing, wrong type, or out of bounds.
"""

_validation_file: str = ""


# ---------------------------------------------------------------------------
# Primitive type checkers
# ---------------------------------------------------------------------------

def check_int(var: int, var_name: str, min_value: int = 0) -> bool:
    """Assert that *var* is an ``int`` >= *min_value*.

    Args:
        var: The variable to validate.
        var_name: Name used in the error message.
        min_value: Minimum allowed integer value.

    Returns:
        ``True`` on success.

    Raises:
        TypeError: If *var* is not an ``int``.
        ValueError: If *var* is less than *min_value*.
    """
    if not isinstance(var, int):
        raise TypeError(
            f'"{var_name}" in "{_validation_file}" must be an Integer.\n'
            f'Received {repr(var)} (type: {type(var).__name__}).\n'
            f'Fix: set `{var_name} = 10` (no quotes around the number).'
        )
    if var < min_value:
        raise ValueError(
            f'"{var_name}" in "{_validation_file}" must be >= {min_value}. '
            f'Received {var}.'
        )
    return True


def check_boolean(var: bool, var_name: str) -> bool:
    """Assert that *var* is a Python ``bool`` (``True`` or ``False``).

    Args:
        var: The variable to validate.
        var_name: Name used in the error message.

    Returns:
        ``True`` on success.

    Raises:
        ValueError: If *var* is not exactly ``True`` or ``False``.
    """
    if var is True or var is False:
        return True
    raise ValueError(
        f'"{var_name}" in "{_validation_file}" must be True or False (case-sensitive).\n'
        f'Received {repr(var)} (type: {type(var).__name__}).\n'
        f'Fix: set `{var_name} = True` (capital T, no quotes).'
    )


def check_string(
    var: str,
    var_name: str,
    options: list[str] | None = None,
    min_length: int = 0,
) -> bool:
    """Assert that *var* is a ``str``, optionally constrained.

    Args:
        var: The variable to validate.
        var_name: Name used in the error message.
        options: If provided, *var* must be one of these values.
        min_length: Minimum required string length.

    Returns:
        ``True`` on success.

    Raises:
        TypeError: If *var* is not a string.
        ValueError: If length or options constraints are violated.
    """
    if not isinstance(var, str):
        raise TypeError(f'"{var_name}" in "{_validation_file}" must be a string. Received {type(var).__name__}.')
    if min_length > 0 and len(var) < min_length:
        raise ValueError(f'"{var_name}" in "{_validation_file}" must be at least {min_length} characters long.')
    if options and var not in options:
        raise ValueError(f'"{var_name}" in "{_validation_file}" must be one of {options}. Received {repr(var)}.')
    return True


def check_list(
    var: list[str],
    var_name: str,
    options: list[str] | None = None,
    min_length: int = 0,
) -> bool:
    """Assert that *var* is a ``list`` of strings, optionally constrained.

    Args:
        var: The variable to validate.
        var_name: Name used in the error message.
        options: If provided, every element must be one of these values.
        min_length: Minimum required list length.

    Returns:
        ``True`` on success.

    Raises:
        TypeError: If *var* is not a list, or contains non-string elements.
        ValueError: If length or option constraints are violated.
    """
    if not isinstance(var, list):
        raise TypeError(f'"{var_name}" in "{_validation_file}" must be a list.')
    if len(var) < min_length:
        raise ValueError(f'"{var_name}" in "{_validation_file}" must have at least {min_length} element(s).')
    for elem in var:
        if not isinstance(elem, str):
            raise TypeError(f'All elements of "{var_name}" in "{_validation_file}" must be strings.')
        if options and elem not in options:
            raise ValueError(
                f'"{elem}" in "{var_name}" is not a valid option. '
                f'Allowed values: {options}'
            )
    return True


# ---------------------------------------------------------------------------
# Per-file validators
# ---------------------------------------------------------------------------

from config.personals import *  # noqa: E402, F403


def validate_personals() -> None:
    """Validate all variables in ``config/personals.py``.

    Raises:
        TypeError / ValueError: On any invalid value.
    """
    global _validation_file
    _validation_file = "config/personals.py"

    check_string(first_name, "first_name", min_length=1)
    check_string(middle_name, "middle_name")
    check_string(last_name, "last_name", min_length=1)
    check_string(phone_number, "phone_number", min_length=10)
    check_string(current_city, "current_city")
    check_string(street, "street")
    check_string(state, "state")
    check_string(zipcode, "zipcode")
    check_string(country, "country")
    check_string(ethnicity, "ethnicity", [
        "Decline", "Hispanic/Latino", "American Indian or Alaska Native",
        "Asian", "Black or African American",
        "Native Hawaiian or Other Pacific Islander", "White", "Other",
    ])
    check_string(gender, "gender", ["Male", "Female", "Other", "Decline", ""])
    check_string(disability_status, "disability_status", ["Yes", "No", "Decline"])
    check_string(veteran_status, "veteran_status", ["Yes", "No", "Decline"])


from config.questions import *  # noqa: E402, F403


def validate_questions() -> None:
    """Validate all variables in ``config/questions.py``.

    Raises:
        TypeError / ValueError: On any invalid value.
    """
    global _validation_file
    _validation_file = "config/questions.py"

    check_string(default_resume_path, "default_resume_path")
    check_string(years_of_experience, "years_of_experience")
    check_string(require_visa, "require_visa", ["Yes", "No"])
    check_string(website, "website")
    check_string(linkedIn, "linkedIn")
    check_int(desired_salary, "desired_salary")
    check_string(us_citizenship, "us_citizenship", [
        "U.S. Citizen/Permanent Resident",
        "Non-citizen allowed to work for any employer",
        "Non-citizen allowed to work for current employer",
        "Non-citizen seeking work authorization",
        "Canadian Citizen/Permanent Resident",
        "Other",
    ])
    check_string(linkedin_headline, "linkedin_headline")
    check_int(notice_period, "notice_period")
    check_int(current_ctc, "current_ctc")
    check_string(linkedin_summary, "linkedin_summary")
    check_string(cover_letter, "cover_letter")
    check_string(recent_employer, "recent_employer")
    check_string(confidence_level, "confidence_level")
    check_boolean(pause_before_submit, "pause_before_submit")
    check_boolean(pause_at_failed_question, "pause_at_failed_question")
    check_boolean(overwrite_previous_answers, "overwrite_previous_answers")

    # JobPilot AI new keys
    check_boolean(use_resume_tailoring, "use_resume_tailoring")
    check_string(base_resume_text, "base_resume_text")


from config.search import *  # noqa: E402, F403


def validate_search() -> None:
    """Validate all variables in ``config/search.py``.

    Raises:
        TypeError / ValueError: On any invalid value.
    """
    global _validation_file
    _validation_file = "config/search.py"

    check_list(search_terms, "search_terms", min_length=1)
    check_string(search_location, "search_location")
    check_int(switch_number, "switch_number", 1)
    check_boolean(randomize_search_order, "randomize_search_order")
    check_string(sort_by, "sort_by", ["", "Most recent", "Most relevant"])
    check_string(date_posted, "date_posted", ["", "Any time", "Past month", "Past week", "Past 24 hours"])
    check_string(salary, "salary")
    check_boolean(easy_apply_only, "easy_apply_only")
    check_list(experience_level, "experience_level", [
        "Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive",
    ])
    check_list(job_type, "job_type", [
        "Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other",
    ])
    check_list(on_site, "on_site", ["On-site", "Remote", "Hybrid"])
    check_list(companies, "companies")
    check_list(location, "location")
    check_list(industry, "industry")
    check_list(job_function, "job_function")
    check_list(job_titles, "job_titles")
    check_list(benefits, "benefits")
    check_list(commitments, "commitments")
    check_boolean(under_10_applicants, "under_10_applicants")
    check_boolean(in_your_network, "in_your_network")
    check_boolean(fair_chance_employer, "fair_chance_employer")
    check_boolean(pause_after_filters, "pause_after_filters")
    check_list(about_company_bad_words, "about_company_bad_words")
    check_list(about_company_good_words, "about_company_good_words")
    check_list(bad_words, "bad_words")
    check_boolean(security_clearance, "security_clearance")
    check_boolean(did_masters, "did_masters")
    check_int(current_experience, "current_experience", -1)


from config.secrets import *  # noqa: E402, F403


def validate_secrets() -> None:
    """Validate all variables in ``config/secrets.py``.

    Raises:
        TypeError / ValueError: On any invalid value.
    """
    global _validation_file
    _validation_file = "config/secrets.py"

    check_string(username, "username", min_length=5)
    check_string(password, "password", min_length=5)
    check_boolean(use_AI, "use_AI")
    if ai_provider != "gemini":
        check_string(llm_api_url, "llm_api_url", min_length=5)
    else:
        check_string(llm_api_url, "llm_api_url")
    check_string(llm_api_key, "llm_api_key")
    check_boolean(stream_output, "stream_output")
    check_string(ai_provider, "ai_provider", ["openai", "deepseek", "gemini"])

    if ai_provider == "deepseek":
        check_string(llm_model, "llm_model", ["deepseek-chat", "deepseek-reasoner"])
    else:
        check_string(llm_model, "llm_model")

    # JobPilot AI new keys
    check_boolean(use_relevance_scoring, "use_relevance_scoring")
    check_int(ai_relevance_threshold, "ai_relevance_threshold", 0)
    if ai_relevance_threshold > 100:
        raise ValueError(
            '"ai_relevance_threshold" in "config/secrets.py" must be between 0 and 100. '
            f'Received {ai_relevance_threshold}.'
        )
    check_boolean(strict_relevance_scoring, "strict_relevance_scoring")


from config.settings import *  # noqa: E402, F403


def validate_settings() -> None:
    """Validate all variables in ``config/settings.py``.

    Raises:
        TypeError / ValueError: On any invalid value.
    """
    global _validation_file
    _validation_file = "config/settings.py"

    check_boolean(close_tabs, "close_tabs")
    check_boolean(follow_companies, "follow_companies")
    check_boolean(run_non_stop, "run_non_stop")
    check_boolean(alternate_sortby, "alternate_sortby")
    check_boolean(cycle_date_posted, "cycle_date_posted")
    check_boolean(stop_date_cycle_at_24hr, "stop_date_cycle_at_24hr")
    check_string(file_name, "file_name", min_length=1)
    check_string(failed_file_name, "failed_file_name", min_length=1)
    check_string(logs_folder_path, "logs_folder_path", min_length=1)
    check_int(click_gap, "click_gap", 0)
    check_boolean(run_in_background, "run_in_background")
    check_boolean(disable_extensions, "disable_extensions")
    check_boolean(safe_mode, "safe_mode")
    check_boolean(smooth_scroll, "smooth_scroll")
    check_boolean(keep_screen_awake, "keep_screen_awake")
    check_boolean(stealth_mode, "stealth_mode")
    check_string(chrome_user_data_dir, "chrome_user_data_dir")
    check_string(chrome_profile_directory, "chrome_profile_directory")


def validate_config() -> bool:
    """Run all per-file validators.

    Call this once at startup before opening Chrome.

    Returns:
        ``True`` if all config values are valid.

    Raises:
        TypeError / ValueError: Propagated from any individual validator
            on the first validation failure encountered.
    """
    validate_personals()
    validate_questions()
    validate_search()
    validate_secrets()
    validate_settings()
    return True
