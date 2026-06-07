# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""DeepSeek AI client for JobPilot AI.

Uses the OpenAI-compatible API provided by DeepSeek.
"""

from typing import Any, Literal

from openai import OpenAI
from pyautogui import confirm

from config.secrets import llm_api_key, llm_api_url, llm_model, stream_output
from config.settings import showAiErrorAlerts
from modules.ai.prompts import ai_answer_prompt, deepseek_extract_skills_prompt
from modules.helpers import convert_to_json, critical_error_log, print_lg

_DEEPSEEK_MODELS_WITH_TEMPERATURE = {"deepseek-chat", "deepseek-reasoner"}


def _deepseek_error_alert(message: str, error: Exception) -> None:
    """Show a user-facing alert for DeepSeek errors and log them.

    Args:
        message: Description of the failure.
        error: Caught exception.
    """
    global showAiErrorAlerts
    critical_error_log(message, error)
    if showAiErrorAlerts:
        choice = confirm(
            f"{message}\n{error}",
            "DeepSeek Connection Error",
            ["Pause AI error alerts", "Continue"],
        )
        if choice == "Pause AI error alerts":
            showAiErrorAlerts = False


def deepseek_create_client() -> OpenAI | None:
    """Create an OpenAI-compatible client pointed at the DeepSeek endpoint.

    Reads ``llm_api_url`` and ``llm_api_key`` from ``config/secrets.py``.

    Returns:
        Configured ``OpenAI`` client for DeepSeek, or ``None`` on failure.
    """
    try:
        print_lg("Creating DeepSeek client...")
        base_url = llm_api_url.rstrip("/")
        client = OpenAI(base_url=base_url, api_key=llm_api_key)
        print_lg("---- DeepSeek client ready ----")
        print_lg(f"Endpoint : {base_url}")
        print_lg(f"Model    : {llm_model}")
        return client
    except Exception as e:
        _deepseek_error_alert("Failed to create DeepSeek client.", e)
        return None


def deepseek_completion(
    client: OpenAI,
    messages: list[dict[str, str]],
    response_format: dict[str, Any] | None = None,
    temperature: float = 0,
    stream: bool = stream_output,
) -> dict | str:
    """Send a chat-completion request to the DeepSeek API.

    Args:
        client: Active DeepSeek client (OpenAI-compatible).
        messages: Conversation as ``[{"role": ..., "content": ...}]``.
        response_format: Optional JSON response format dict.
        temperature: Sampling temperature (only applied to supported models).
        stream: Whether to stream tokens.

    Returns:
        Parsed dict if ``response_format`` is set, otherwise a plain string.

    Raises:
        ValueError: If the client is None or the API returns an error.
    """
    if not client:
        raise ValueError("DeepSeek client is not initialised.")

    params: dict[str, Any] = {
        "model": llm_model,
        "messages": messages,
        "stream": stream,
        "timeout": 30,
    }
    if llm_model in _DEEPSEEK_MODELS_WITH_TEMPERATURE:
        params["temperature"] = temperature
    if response_format:
        params["response_format"] = response_format

    try:
        print_lg(
            f"Calling DeepSeek API | model={llm_model} | messages={len(messages)}"
        )
        completion = client.chat.completions.create(**params)
        result = ""

        if stream:
            print_lg("-- Streaming started")
            for chunk in completion:
                if chunk.model_extra and chunk.model_extra.get("error"):
                    raise ValueError(
                        f"DeepSeek stream error: {chunk.model_extra['error']}"
                    )
                token = chunk.choices[0].delta.content
                if token is not None:
                    result += token
                print_lg(token, end="", flush=True)
            print_lg("\n-- Streaming complete")
        else:
            if completion.model_extra and completion.model_extra.get("error"):
                raise ValueError(f"DeepSeek error: {completion.model_extra['error']}")
            result = completion.choices[0].message.content

        if response_format:
            result = convert_to_json(result)

        print_lg("\nDeepSeek response:\n")
        print_lg(result, pretty=bool(response_format))
        return result
    except Exception as e:
        raise ValueError(f"DeepSeek API error: {e}") from e


def deepseek_extract_skills(
    client: OpenAI,
    job_description: str,
    stream: bool = stream_output,
) -> dict:
    """Extract and categorise skills from a job description using DeepSeek.

    Args:
        client: Active DeepSeek client.
        job_description: Full text of the LinkedIn job posting.
        stream: Whether to stream the response.

    Returns:
        Dict with skill categories, or ``{"error": ...}`` on failure.
    """
    try:
        print_lg("-- Extracting skills from job description (DeepSeek)")
        prompt = deepseek_extract_skills_prompt.format(job_description)
        messages = [{"role": "user", "content": prompt}]
        result = deepseek_completion(
            client=client,
            messages=messages,
            response_format={"type": "json_object"},
            stream=stream,
        )
        if isinstance(result, str):
            result = convert_to_json(result)
        return result
    except Exception as e:
        critical_error_log("DeepSeek skill extraction failed.", e)
        return {"error": str(e)}


def deepseek_answer_question(
    client: OpenAI,
    question: str,
    options: list[str] | None = None,
    question_type: Literal[
        "text", "textarea", "single_select", "multiple_select"
    ] = "text",
    job_description: str | None = None,
    about_company: str | None = None,
    user_information_all: str | None = None,
    stream: bool = stream_output,
) -> dict | str:
    """Generate a DeepSeek-powered answer for a form question.

    Args:
        client: Active DeepSeek client.
        question: The label text of the form question.
        options: Valid options for select-type questions.
        question_type: One of ``'text'``, ``'textarea'``,
            ``'single_select'``, ``'multiple_select'``.
        job_description: Optional job posting text.
        about_company: Optional company description.
        user_information_all: User's full profile/resume text.
        stream: Whether to stream the response.

    Returns:
        AI-generated answer string, or ``{"error": ...}`` on failure.
    """
    try:
        print_lg(f"-- Answering question via DeepSeek: {question}")
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

        messages = [{"role": "user", "content": prompt}]
        return deepseek_completion(
            client=client,
            messages=messages,
            temperature=0.1,
            stream=stream,
        )
    except Exception as e:
        critical_error_log("DeepSeek question answering failed.", e)
        return ""
