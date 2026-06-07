# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""Unified AI client factory for JobPilot AI.

Replaces scattered ``if ai_provider == "openai" / "deepseek" / "gemini"``
blocks with a single factory function and matching dispatchers for each
task type.
"""

from typing import Any, Literal

from modules.helpers import critical_error_log, print_lg


def _completion_json(client: Any, provider: str, prompt: str) -> dict | str:
    """Run a JSON-oriented completion for any supported provider.

    Args:
        client: Active AI client.
        provider: ``"openai"``, ``"deepseek"``, or ``"gemini"``.
        prompt: Full prompt text.

    Returns:
        Parsed dict or raw string from the model.
    """
    provider_key = provider.lower()
    if provider_key in {"openai", "deepseek"}:
        from config.secrets import llm_model

        request_params: dict[str, Any] = {
            "model": llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            request_params["response_format"] = {"type": "json_object"}
            completion = client.chat.completions.create(**request_params)
            return completion.choices[0].message.content
        except Exception:
            request_params.pop("response_format", None)
            completion = client.chat.completions.create(**request_params)
            return completion.choices[0].message.content

    if provider_key == "gemini":
        from modules.ai.gemini_client import gemini_completion

        return gemini_completion(client, prompt, is_json=True)

    raise ValueError(f"Unknown AI provider '{provider}' for JSON completion.")


def score_job_relevance(
    client: Any,
    provider: str,
    job_description: str,
    user_profile: str,
    job_id: str | None = None,
    fail_open: bool = True,
) -> dict[str, Any]:
    """Route job relevance scoring through the unified factory.

    Args:
        client: Active AI client.
        provider: Provider name.
        job_description: Job posting text.
        user_profile: User profile or resume text.
        job_id: Optional cache key.
        fail_open: Fail-open (100) vs fail-closed (0) on errors.

    Returns:
        Score result dict from :mod:`modules.ai.scoring`.
    """
    from modules.ai.scoring import ai_score_job_relevance

    return ai_score_job_relevance(
        client,
        job_description,
        user_profile,
        provider,
        job_id=job_id,
        fail_open=fail_open,
    )


def create_ai_client(provider: str) -> Any | None:
    """Create and return an AI client for the configured provider.

    Reads all connection details (URL, key, model) from
    ``config/secrets.py`` via the individual client modules.

    Args:
        provider: One of ``"openai"``, ``"deepseek"``, or ``"gemini"``.

    Returns:
        A ready-to-use client object appropriate for the provider, or
        ``None`` if creation fails.

    Raises:
        ValueError: If *provider* is not a recognised value.
    """
    normalized_provider = provider.lower().strip()
    print_lg(f"Initialising AI client for provider: '{normalized_provider}'")

    if normalized_provider == "openai":
        from modules.ai.openai_client import ai_create_openai_client

        return ai_create_openai_client()
    if normalized_provider == "deepseek":
        from modules.ai.deepseek_client import deepseek_create_client

        return deepseek_create_client()
    if normalized_provider == "gemini":
        from modules.ai.gemini_client import gemini_create_client

        return gemini_create_client()

    raise ValueError(
        f"Unknown AI provider '{provider}'. "
        "Valid options: 'openai', 'deepseek', 'gemini'."
    )


def close_ai_client(client: Any, provider: str) -> None:
    """Gracefully close the client if the provider requires explicit teardown.

    OpenAI and DeepSeek clients use the OpenAI SDK and require an explicit
    ``close()`` call. Gemini clients are stateless and need no cleanup.

    Args:
        client: The active client object to close.
        provider: Provider name (determines which close function to use).
    """
    if client is None:
        return
    try:
        provider_key = provider.lower()
        if provider_key in {"openai", "deepseek"}:
            from modules.ai.openai_client import ai_close_openai_client

            ai_close_openai_client(client)
        print_lg(f"AI client for '{provider}' closed.")
    except Exception as exc:
        critical_error_log(f"Failed to close AI client for '{provider}'.", exc)


def extract_skills(client: Any, provider: str, job_description: str) -> dict:
    """Route a skill-extraction request to the correct AI provider.

    Args:
        client: Active AI client.
        provider: Provider name.
        job_description: Full job posting text.

    Returns:
        Dict with skill categories, or ``{}`` on failure.
    """
    from modules.ai.scoring import is_ai_quota_exhausted

    if is_ai_quota_exhausted():
        return {}
    try:
        provider_key = provider.lower()
        if provider_key == "openai":
            from modules.ai.openai_client import ai_extract_skills

            return ai_extract_skills(client, job_description)
        if provider_key == "deepseek":
            from modules.ai.deepseek_client import deepseek_extract_skills

            return deepseek_extract_skills(client, job_description)
        if provider_key == "gemini":
            from modules.ai.gemini_client import gemini_extract_skills

            return gemini_extract_skills(client, job_description)
        print_lg(f"Unknown provider '{provider}' for skill extraction.")
        return {}
    except Exception as exc:
        critical_error_log("Skill extraction via factory failed.", exc)
        return {}


def answer_question(
    client: Any,
    provider: str,
    question: str,
    question_type: Literal[
        "text", "textarea", "single_select", "multiple_select"
    ] = "text",
    options: list[str] | None = None,
    job_description: str | None = None,
    about_company: str | None = None,
    user_information_all: str | None = None,
) -> str:
    """Route a form Q&A request to the correct AI provider.

    Args:
        client: Active AI client.
        provider: Provider name.
        question: The form question label text.
        question_type: Type of form field.
        options: Answer options for select fields.
        job_description: Optional job posting context.
        about_company: Optional company context.
        user_information_all: User profile or resume text.

    Returns:
        AI-generated answer string, or ``""`` on failure.
    """
    from modules.ai.scoring import is_ai_quota_exhausted

    if is_ai_quota_exhausted():
        return ""
    try:
        provider_key = provider.lower()
        if provider_key == "openai":
            from modules.ai.openai_client import ai_answer_question

            return ai_answer_question(
                client,
                question,
                options,
                question_type,
                job_description,
                about_company,
                user_information_all,
            )
        if provider_key == "deepseek":
            from modules.ai.deepseek_client import deepseek_answer_question

            return deepseek_answer_question(
                client,
                question,
                options,
                question_type,
                job_description,
                about_company,
                user_information_all,
            )
        if provider_key == "gemini":
            from modules.ai.gemini_client import gemini_answer_question

            return gemini_answer_question(
                client,
                question,
                options,
                question_type,
                job_description,
                about_company,
                user_information_all,
            )
        print_lg(f"Unknown provider '{provider}' for Q&A.")
        return ""
    except Exception as exc:
        critical_error_log("Q&A via factory failed.", exc)
        return ""
