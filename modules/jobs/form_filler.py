# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Easy Apply form-filling engine for JobPilot AI.

Handles all form field types encountered in LinkedIn Easy Apply modals:
select dropdowns, radio buttons, text inputs, textareas, and checkboxes.

Integrates with:
- AI Q&A answering (OpenAI / DeepSeek / Gemini) for unknown questions.
- AI resume tailoring to generate a job-specific cover letter.
"""

import os

from random import randint
from time import sleep
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

import modules.browser.session as browser
from modules.browser.interactions import try_xp
from modules.helpers import print_lg

from config.personals import (
    gender, disability_status, veteran_status,
    phone_number, street, state, zipcode, country,
    current_city, first_name, middle_name, last_name,
)
from config.questions import (
    years_of_experience, require_visa, website, linkedIn, us_citizenship,
    desired_salary, current_ctc, notice_period,
    linkedin_headline, linkedin_summary, cover_letter,
    recent_employer, confidence_level, overwrite_previous_answers,
    user_information_all,
    use_resume_tailoring, base_resume_text,
)

QuestionRecord = tuple[Any, ...]


def upload_resume(modal: WebElement, resume_path: str) -> tuple[bool, str]:
    """Upload a resume file into the Easy Apply modal's file input field.

    Args:
        modal: The Easy Apply modal ``WebElement``.
        resume_path: Absolute or relative path to the resume PDF.

    Returns:
        A 2-tuple of ``(success: bool, filename: str)``.
        ``success`` is False if no file input is found or the upload fails.
    """
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume_path))
        return True, os.path.basename(resume_path)
    except Exception:
        return False, "Previous resume"


def answer_common_questions(label: str, answer: str) -> str:
    """Apply config-driven overrides for common application questions.

    Checks the question label for keywords like ``"sponsorship"`` or
    ``"visa"`` and returns the appropriate config value.

    Args:
        label: Lowercase question label text.
        answer: The default answer to potentially override.

    Returns:
        The (possibly overridden) answer string.
    """
    if "sponsorship" in label or "visa" in label:
        return require_visa
    return answer


def answer_questions(
    modal: WebElement,
    questions_list: set[QuestionRecord],
    work_location: str,
    job_description: str | None = None,
    company: str = "",
    title: str = "",
    ai_client: Any = None,
    ai_provider: str = "",
) -> set[QuestionRecord]:
    """Fill every form field visible in the current Easy Apply modal step.

    Iterates all ``div[data-test-form-element]`` elements and handles each
    field type:  ``<select>``, radio ``<fieldset>``, ``<input type="text">``,
    ``<textarea>``, and ``<input type="checkbox">``.

    Unknown text/textarea questions are answered by the AI if configured,
    otherwise recorded as randomly answered.

    Args:
        modal: The Easy Apply modal ``WebElement``.
        questions_list: Running set of ``(label, answer, type, prev_answer)``
            tuples — accumulated across all modal steps.
        work_location: Work location of the current job (used for city/state fields).
        job_description: Full job description text (AI context).
        company: Company name (used for resume tailoring personalisation).
        title: Job title (used for resume tailoring personalisation).
        ai_client: Active AI client, or ``None`` if AI is disabled.
        ai_provider: Provider name string (``"openai"``, ``"deepseek"``,
            ``"gemini"``).

    Returns:
        Updated ``questions_list`` set with all answers from this modal step.
    """
    from config.secrets import use_AI

    randomly_answered: set[tuple[str, str]] = set()
    full_name = (
        f"{first_name} {middle_name} {last_name}".strip()
        if middle_name
        else f"{first_name} {last_name}"
    )

    # Pre-compute salary/notice variants
    desired_salary_str = str(desired_salary)
    if desired_salary_str.isdigit():
        desired_salary_monthly = str(round(int(desired_salary_str) / 12, 2))
    else:
        desired_salary_monthly = desired_salary_str
    current_ctc_str = str(current_ctc)
    if current_ctc_str.isdigit():
        current_ctc_monthly = str(round(int(current_ctc_str) / 12, 2))
    else:
        current_ctc_monthly = current_ctc_str
    notice_str = str(notice_period)
    notice_months = str(int(notice_str) // 30) if notice_str.isdigit() else notice_str
    notice_weeks = str(int(notice_str) // 7) if notice_str.isdigit() else notice_str

    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")

    for question_element in all_questions:

        # ------------------------------------------------------------------ #
        # SELECT (dropdown)
        # ------------------------------------------------------------------ #
        select_el = try_xp(question_element, ".//select", click=False)
        if select_el:
            label_org = "Unknown"
            try:
                lbl = question_element.find_element(By.TAG_NAME, "label")
                label_org = lbl.find_element(By.TAG_NAME, "span").text
            except Exception:
                pass

            label = label_org.lower()
            select = Select(select_el)
            selected_option = select.first_selected_option.text
            options_text: list[str] = []
            options_display = '"List of phone country codes"'

            if label != "phone country code":
                options_text = [o.text for o in select.options]
                options_display = "".join(f' "{o}",' for o in options_text)

            prev_answer = selected_option
            answer = "Yes"

            if overwrite_previous_answers or selected_option == "Select an option":
                if "email" in label or "phone" in label:
                    answer = prev_answer
                elif "gender" in label or "sex" in label:
                    answer = gender
                elif "disability" in label:
                    answer = disability_status
                elif "proficiency" in label:
                    answer = "Professional"
                elif any(w in label for w in ["location", "city", "state", "country"]):
                    if "country" in label:
                        answer = country
                    elif "state" in label:
                        answer = state
                    elif "city" in label:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else:
                    answer = answer_common_questions(label, answer)

                try:
                    select.select_by_visible_text(answer)
                except NoSuchElementException:
                    phrases: list[str] = []
                    if answer == "Decline":
                        phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                    elif "yes" in answer.lower():
                        phrases = ["Yes", "Agree", "I do", "I have"]
                    elif "no" in answer.lower():
                        phrases = ["No", "Disagree", "I don't", "I do not"]
                    else:
                        phrases = [answer, answer.lower(), answer.upper()]

                    found = False
                    for phrase in phrases:
                        for opt in options_text:
                            if phrase.lower() in opt.lower() or opt.lower() in phrase.lower():
                                select.select_by_visible_text(opt)
                                answer = opt
                                found = True
                                break
                        if found:
                            break

                    if not found:
                        print_lg(
                            f'No option matched "{answer}" for "{label_org}" — answering randomly.'
                        )
                        select.select_by_index(randint(1, len(select.options) - 1))
                        answer = select.first_selected_option.text
                        randomly_answered.add((f"{label_org} [ {options_display} ]", "select"))

            questions_list.add((
                f"{label_org} [ {options_display} ]",
                answer,
                "select",
                prev_answer,
            ))
            continue

        # ------------------------------------------------------------------ #
        # RADIO
        # ------------------------------------------------------------------ #
        radio = try_xp(
            question_element,
            './/fieldset[@data-test-form-builder-radio-button-form-component="true"]',
            click=False,
        )
        if radio:
            prev_answer = None
            lbl = try_xp(
                radio,
                './/span[@data-test-form-builder-radio-button-form-component__title]',
                click=False,
            )
            try:
                from modules.browser.interactions import find_by_class
                lbl = find_by_class(lbl, "visually-hidden", 2.0)
            except Exception:
                pass
            label_org = lbl.text if lbl else "Unknown"
            label = label_org.lower()
            answer = "Yes"

            label_display = label_org + " [ "
            options = radio.find_elements(By.TAG_NAME, "input")
            options_labels: list[str] = []

            for opt in options:
                opt_id = opt.get_attribute("id")
                opt_label = try_xp(radio, f'.//label[@for="{opt_id}"]', click=False)
                options_labels.append(
                    f'"{opt_label.text if opt_label else "Unknown"}"<{opt.get_attribute("value")}>'
                )
                if opt.is_selected():
                    prev_answer = options_labels[-1]
                label_display += f" {options_labels[-1]},"

            if overwrite_previous_answers or prev_answer is None:
                if "citizenship" in label or "employment eligibility" in label:
                    answer = us_citizenship
                elif "veteran" in label or "protected" in label:
                    answer = veteran_status
                elif "disability" in label or "handicapped" in label:
                    answer = disability_status
                else:
                    answer = answer_common_questions(label, answer)

                found_option = try_xp(radio, f".//label[normalize-space()='{answer}']", click=False)
                if found_option:
                    browser.actions.move_to_element(found_option).click().perform()
                else:
                    phrases = (
                        ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                        if answer == "Decline"
                        else [answer]
                    )
                    ele = options[0]
                    answer = options_labels[0]
                    for phrase in phrases:
                        for i, opt_label in enumerate(options_labels):
                            if phrase in opt_label:
                                ele = options[i]
                                answer = (
                                    f"Decline ({opt_label})" if len(phrases) > 1 else opt_label
                                )
                                found_option = True
                                break
                        if found_option:
                            break
                    browser.actions.move_to_element(ele).click().perform()
                    if not found_option:
                        randomly_answered.add((label_display + " ]", "radio"))
            else:
                answer = prev_answer

            questions_list.add((label_display + " ]", answer, "radio", prev_answer))
            continue

        # ------------------------------------------------------------------ #
        # TEXT INPUT
        # ------------------------------------------------------------------ #
        text_el = try_xp(question_element, ".//input[@type='text']", click=False)
        if text_el:
            do_actions = False
            lbl = try_xp(question_element, ".//label[@for]", click=False)
            try:
                lbl = lbl.find_element(By.CLASS_NAME, "visually-hidden")
            except Exception:
                pass
            label_org = lbl.text if lbl else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_el.get_attribute("value")

            if not prev_answer or overwrite_previous_answers:
                if "experience" in label or "years" in label:
                    answer = years_of_experience
                elif "phone" in label or "mobile" in label:
                    answer = phone_number
                elif "street" in label:
                    answer = street
                elif "city" in label or "location" in label or "address" in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif "signature" in label:
                    answer = full_name
                elif "name" in label:
                    if "full" in label:
                        answer = full_name
                    elif "first" in label and "last" not in label:
                        answer = first_name
                    elif "middle" in label and "last" not in label:
                        answer = middle_name
                    elif "last" in label and "first" not in label:
                        answer = last_name
                    elif "employer" in label:
                        answer = recent_employer
                    else:
                        answer = full_name
                elif "notice" in label:
                    if "month" in label:
                        answer = notice_months
                    elif "week" in label:
                        answer = notice_weeks
                    else:
                        answer = notice_str
                elif any(w in label for w in ["salary", "compensation", "ctc", "pay"]):
                    if "current" in label or "present" in label:
                        answer = current_ctc_monthly if "month" in label else current_ctc_str
                    else:
                        answer = desired_salary_monthly if "month" in label else desired_salary_str
                elif "linkedin" in label:
                    answer = linkedIn
                elif any(w in label for w in ["website", "blog", "portfolio", "link"]):
                    answer = website
                elif "scale of 1-10" in label:
                    answer = confidence_level
                elif "headline" in label:
                    answer = linkedin_headline
                elif any(w in label for w in ["hear", "come across"]) and "this" in label:
                    answer = "LinkedIn job search"
                elif "state" in label or "province" in label:
                    answer = state
                elif "zip" in label or "postal" in label or "code" in label:
                    answer = zipcode
                elif "country" in label:
                    answer = country
                else:
                    answer = answer_common_questions(label, answer)

                if not answer:
                    if use_AI and ai_client:
                        try:
                            from modules.ai.client_factory import answer_question as _ai_answer
                            ai_result = _ai_answer(
                                ai_client, ai_provider, label_org, "text",
                                job_description=job_description,
                                user_information_all=user_information_all,
                            )
                            if ai_result and isinstance(ai_result, str):
                                answer = ai_result
                                print_lg(f'AI answered "{label_org}": "{answer}"')
                            else:
                                randomly_answered.add((label_org, "text"))
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("AI failed to answer text question.", e)
                            randomly_answered.add((label_org, "text"))
                            answer = years_of_experience
                    else:
                        randomly_answered.add((label_org, "text"))
                        answer = years_of_experience

                text_el.clear()
                text_el.send_keys(answer)
                if do_actions:
                    sleep(2)
                    from selenium.webdriver.common.keys import Keys
                    browser.actions.send_keys(Keys.ARROW_DOWN)
                    browser.actions.send_keys(Keys.ENTER).perform()

            questions_list.add((label, text_el.get_attribute("value"), "text", prev_answer))
            continue

        # ------------------------------------------------------------------ #
        # TEXTAREA
        # ------------------------------------------------------------------ #
        textarea_el = try_xp(question_element, ".//textarea", click=False)
        if textarea_el:
            lbl = try_xp(question_element, ".//label[@for]", click=False)
            label_org = lbl.text if lbl else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = textarea_el.get_attribute("value")

            if not prev_answer or overwrite_previous_answers:
                if "summary" in label:
                    answer = linkedin_summary
                elif "cover" in label:
                    # AI Resume Tailoring — generate a job-specific cover letter
                    if (
                        use_resume_tailoring
                        and use_AI
                        and ai_client
                        and base_resume_text.strip()
                        and job_description
                        and company
                        and title
                    ):
                        try:
                            from modules.ai.resume_tailor import ai_tailor_cover_letter
                            tailored = ai_tailor_cover_letter(
                                client=ai_client,
                                job_description=job_description,
                                base_resume_text=base_resume_text,
                                company=company,
                                job_title=title,
                                provider=ai_provider,
                            )
                            answer = tailored if tailored else cover_letter
                        except Exception as e:
                            print_lg("Resume tailoring failed — using static cover letter.", e)
                            answer = cover_letter
                    else:
                        answer = cover_letter

                if not answer:
                    if use_AI and ai_client:
                        try:
                            from modules.ai.client_factory import answer_question as _ai_answer
                            ai_result = _ai_answer(
                                ai_client, ai_provider, label_org, "textarea",
                                job_description=job_description,
                                user_information_all=user_information_all,
                            )
                            if ai_result and isinstance(ai_result, str):
                                answer = ai_result
                                print_lg(f'AI answered textarea "{label_org}"')
                            else:
                                randomly_answered.add((label_org, "textarea"))
                        except Exception as e:
                            print_lg("AI failed to answer textarea question.", e)
                            randomly_answered.add((label_org, "textarea"))
                    else:
                        randomly_answered.add((label_org, "textarea"))

                textarea_el.clear()
                textarea_el.send_keys(answer)

            questions_list.add((label, textarea_el.get_attribute("value"), "textarea", prev_answer))
            continue

        # ------------------------------------------------------------------ #
        # CHECKBOX
        # ------------------------------------------------------------------ #
        checkbox_el = try_xp(question_element, ".//input[@type='checkbox']", click=False)
        if checkbox_el:
            lbl = try_xp(question_element, ".//span[@class='visually-hidden']", click=False)
            label_org = lbl.text if lbl else "Unknown"
            label = label_org.lower()
            answer_label = try_xp(question_element, ".//label[@for]", click=False)
            answer_text = answer_label.text if answer_label else "Unknown"
            prev_answer = checkbox_el.is_selected()

            if not prev_answer:
                try:
                    browser.actions.move_to_element(checkbox_el).click().perform()
                    checked = True
                except Exception as e:
                    print_lg("Checkbox click failed.", e)
                    checked = False
            else:
                checked = prev_answer

            questions_list.add((f"{label} ([X] {answer_text})", checked, "checkbox", prev_answer))
            continue

    # Click any "Today" date button if present
    try_xp(browser.driver, "//button[contains(@aria-label, 'This is today')]")

    # Log randomly answered questions for review
    if randomly_answered:
        print_lg("The following questions were answered randomly or left for AI:")
        for q in randomly_answered:
            print_lg(f"  {q}")

    return questions_list

