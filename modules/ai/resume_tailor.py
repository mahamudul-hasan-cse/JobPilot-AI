# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""AI resume tailoring for JobPilot AI.

Generates a job-specific cover letter for each Easy Apply application by
combining the user's base resume text with the job description. The
tailored cover letter replaces the static ``cover_letter`` setting in
``config/questions.py`` whenever the feature is enabled.

Configuration (``config/questions.py``):
    use_resume_tailoring: Enable or disable this feature.
    base_resume_text: Plain-text copy of the user's resume.

This feature requires ``use_AI = True`` in ``config/secrets.py``.
"""

from typing import Any

from modules.ai.prompts import resume_tailoring_prompt
from modules.helpers import critical_error_log, print_lg

_MIN_COVER_LETTER_LENGTH = 20


def ai_tailor_cover_letter(
    client: Any,
    job_description: str,
    base_resume_text: str,
    company: str,
    job_title: str,
    provider: str,
) -> str:
    """Generate a tailored cover letter for a specific job.

    Sends the user's resume text and the full job description to the
    configured AI provider and requests a concise, personalised cover
    letter (three paragraphs, under 250 words).

    Falls back gracefully to an empty string on any failure so the bot
    can continue with the static ``cover_letter`` config value.

    Args:
        client: Active AI client (OpenAI, DeepSeek, or Gemini instance).
        job_description: Full text of the LinkedIn job posting.
        base_resume_text: User's resume as plain text from
            ``config/questions.base_resume_text``.
        company: Company name for personalisation in the letter.
        job_title: Job title for personalisation in the letter.
        provider: AI provider name (``"openai"``, ``"deepseek"``, or
            ``"gemini"``).

    Returns:
        The AI-generated cover letter body as a plain string, or ``""`` if
        the request fails (caller should fall back to the static
        ``cover_letter`` config value).
    """
    print_lg(f"-- Tailoring cover letter for '{job_title}' at '{company}'")
    try:
        prompt = resume_tailoring_prompt.format(
            company=company,
            job_title=job_title,
            resume=base_resume_text,
            job_description=job_description,
        )

        provider_key = provider.lower()

        if provider_key in {"openai", "deepseek"}:
            cover_letter = _tailor_via_openai_sdk(client, prompt)
        elif provider_key == "gemini":
            cover_letter = _tailor_via_gemini(client, prompt)
        else:
            print_lg(
                f"Unknown provider '{provider}' for resume tailoring — skipping."
            )
            return ""

        if (
            cover_letter
            and isinstance(cover_letter, str)
            and len(cover_letter.strip()) > _MIN_COVER_LETTER_LENGTH
        ):
            print_lg(
                f"Tailored cover letter generated ({len(cover_letter)} chars)."
            )
            return cover_letter.strip()

        print_lg(
            "AI returned an empty or too-short cover letter — using static fallback."
        )
        return ""

    except Exception as exc:
        critical_error_log(
            "Resume tailoring failed — using static cover_letter.",
            exc,
        )
        return ""


def _tailor_via_openai_sdk(client: Any, prompt: str) -> str:
    """Send the tailoring prompt to an OpenAI-compatible endpoint.

    Args:
        client: An ``openai.OpenAI`` or DeepSeek-compatible client.
        prompt: Fully formatted prompt string.

    Returns:
        Model response text, or an empty string when streaming yields no
        content.
    """
    from config.secrets import llm_model, stream_output

    messages = [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model=llm_model,
        messages=messages,
        stream=stream_output,
    )
    if stream_output:
        response_text = ""
        for chunk in completion:
            token = chunk.choices[0].delta.content
            if token:
                response_text += token
        return response_text
    content = completion.choices[0].message.content
    return content or ""


def _tailor_via_gemini(client: Any, prompt: str) -> str:
    """Send the tailoring prompt to the Gemini API.

    Args:
        client: A ``genai.GenerativeModel`` instance.
        prompt: Fully formatted prompt string.

    Returns:
        Model response text.
    """
    from modules.ai.gemini_client import gemini_completion

    result = gemini_completion(client, prompt, is_json=False)
    if isinstance(result, dict):
        return str(result.get("error", ""))
    return str(result)
