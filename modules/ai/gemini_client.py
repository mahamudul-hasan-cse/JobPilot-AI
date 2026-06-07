# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Google Gemini AI client for JobPilot AI."""

import re
import time
from typing import Any, Literal

import google.generativeai as genai
from pyautogui import confirm

from config.secrets import llm_api_key, llm_model
from config.settings import showAiErrorAlerts
from modules.ai.prompts import ai_answer_prompt, extract_skills_prompt
from modules.ai.scoring import (
    is_ai_quota_exhausted,
    is_quota_error,
    trip_ai_quota_circuit,
)
from modules.helpers import convert_to_json, critical_error_log, print_lg

_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


def gemini_get_models_list() -> list[str | Exception]:
    """List all Gemini models that support content generation.

    Returns:
        List of model name strings, or ``["error", exception]`` on failure.
    """
    try:
        print_lg("Fetching available Gemini models...")
        models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        print_lg("Available Gemini models:", models, pretty=True)
        return models
    except Exception as e:
        critical_error_log("Failed to list Gemini models.", e)
        return ["error", e]


def gemini_create_client() -> Any | None:
    """Configure the Gemini API key and return a GenerativeModel instance.

    Reads ``llm_api_key`` and ``llm_model`` from ``config/secrets.py``.

    Returns:
        A ``genai.GenerativeModel`` object, or ``None`` on failure.
    """
    try:
        print_lg("Configuring Gemini client...")
        if not llm_api_key or "YOUR_API_KEY" in llm_api_key:
            raise ValueError("Gemini API key is not set. Add it in config/secrets.py.")

        genai.configure(api_key=llm_api_key)
        model = genai.GenerativeModel(llm_model)
        print_lg("---- Gemini client ready ----")
        print_lg(f"Model : {llm_model}")
        return model
    except Exception as e:
        msg = "Failed to configure Gemini client. Check your API key and model name."
        critical_error_log(msg, e)
        if showAiErrorAlerts:
            choice = confirm(
                f"{msg}\n{e}",
                "Gemini Connection Error",
                ["Pause AI error alerts", "Continue"],
            )
            if choice == "Pause AI error alerts":
                import config.settings as _settings

                _settings.showAiErrorAlerts = False
        return None


def gemini_completion(
    model: Any,
    prompt: str,
    is_json: bool = False,
) -> dict | str:
    """Generate content from the Gemini model for a given prompt.

    Args:
        model: A ``genai.GenerativeModel`` instance.
        prompt: The prompt text to send to the model.
        is_json: If True, strip Markdown fencing and parse as JSON.

    Returns:
        Parsed dict if ``is_json=True``, otherwise a plain string.
        Returns ``{"error": ...}`` if the API call fails.
    """
    if not model:
        raise ValueError("Gemini client is not initialised.")

    if is_ai_quota_exhausted():
        return {"error": "AI quota circuit open — skipping Gemini call."}

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            print_lg("Calling Gemini API...")
            response = model.generate_content(
                prompt,
                safety_settings=_SAFETY_SETTINGS,
            )

            if not response.parts:
                raise ValueError(
                    "Gemini response was empty — possibly blocked by safety filters. "
                    f"Prompt was:\n{prompt}"
                )

            result = response.text

            if is_json:
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                return convert_to_json(result.strip())

            return result
        except Exception as e:
            last_error = e
            err = str(e)
            if is_quota_error(err):
                trip_ai_quota_circuit(err)
                return {"error": err}
            if "429" in err and attempt < 2:
                wait_match = re.search(r"retry in ([\d.]+)s", err, re.I)
                wait_secs = int(float(wait_match.group(1))) + 2 if wait_match else 20
                print_lg(f"Gemini rate limit — waiting {wait_secs}s before retry...")
                time.sleep(wait_secs)
                continue
            critical_error_log("Gemini completion failed.", e)
            return {"error": err}

    critical_error_log("Gemini completion failed after retries.", last_error)
    return {"error": str(last_error)}


def gemini_extract_skills(model: Any, job_description: str) -> dict:
    """Extract and categorise skills from a job description using Gemini.

    Args:
        model: Active ``genai.GenerativeModel`` instance.
        job_description: Full text of the LinkedIn job posting.

    Returns:
        Dict with skill categories, or ``{"error": ...}`` on failure.
    """
    try:
        print_lg("-- Extracting skills (Gemini)")
        prompt = (
            extract_skills_prompt.format(job_description)
            + "\n\nImportant: Respond with ONLY the JSON object, no markdown or extra text."
        )
        return gemini_completion(model, prompt, is_json=True)
    except Exception as e:
        critical_error_log("Gemini skill extraction failed.", e)
        return {"error": str(e)}


def gemini_answer_question(
    model: Any,
    question: str,
    options: list[str] | None = None,
    question_type: Literal[
        "text", "textarea", "single_select", "multiple_select"
    ] = "text",
    job_description: str | None = None,
    about_company: str | None = None,
    user_information_all: str | None = None,
) -> dict | str:
    """Generate a Gemini-powered answer for a job application form question.

    Args:
        model: Active ``genai.GenerativeModel`` instance.
        question: The label text of the form question.
        options: Valid options for select-type questions.
        question_type: One of ``'text'``, ``'textarea'``,
            ``'single_select'``, ``'multiple_select'``.
        job_description: Optional job posting text.
        about_company: Optional company description.
        user_information_all: User's full profile/resume text.

    Returns:
        AI-generated answer string, or ``{"error": ...}`` on failure.
    """
    try:
        print_lg(f"-- Answering question via Gemini: {question}")
        prompt = ai_answer_prompt.format(user_information_all or "", question)

        if options and question_type in {"single_select", "multiple_select"}:
            opts = "\n".join(f"- {o}" for o in options)
            prompt += f"\n\nOPTIONS:\n{opts}"
            if question_type == "single_select":
                prompt += "\n\nSelect exactly ONE option."
            else:
                prompt += "\n\nYou may select MULTIPLE options."

        if job_description:
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        if about_company:
            prompt += f"\n\nABOUT COMPANY:\n{about_company}"

        return gemini_completion(model, prompt)
    except Exception as e:
        critical_error_log("Gemini question answering failed.", e)
        return ""
