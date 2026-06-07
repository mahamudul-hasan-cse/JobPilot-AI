# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""OpenAI (and OpenAI-compatible) AI client for JobPilot AI.

Supports any API that follows the OpenAI chat-completions spec, including
local models served by Ollama, LM Studio, llama.cpp, or Jan.
"""

from typing import Any, Literal

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.model import Model
from pyautogui import confirm

from config.secrets import (
    llm_api_key,
    llm_api_url,
    llm_model,
    llm_spec,
    stream_output,
    use_AI,
)
from config.settings import showAiErrorAlerts
from modules.ai.prompts import (
    ai_answer_prompt,
    extract_skills_prompt,
    extract_skills_response_format,
)
from modules.helpers import convert_to_json, critical_error_log, print_lg

_API_CHECK_INSTRUCTIONS = """
Troubleshooting steps:
1. Verify your API URL, key, and model name in config/secrets.py.
2. If using a local LLM, confirm the server is running.
3. Check that the selected model is loaded and ready.

ERROR:
"""


def _ai_error_alert(
    message: str,
    error: Exception,
    title: str = "AI Connection Error",
) -> None:
    """Show a user-facing alert for AI errors and log them.

    Args:
        message: Human-readable description of what went wrong.
        error: The caught exception.
        title: Title for the PyAutoGUI alert dialog.
    """
    global showAiErrorAlerts
    if showAiErrorAlerts:
        choice = confirm(
            f"{message}\n{error}\n",
            title,
            ["Pause AI error alerts", "Continue"],
        )
        if choice == "Pause AI error alerts":
            showAiErrorAlerts = False
    critical_error_log(message, error)


def _check_response_error(response: ChatCompletion | ChatCompletionChunk) -> None:
    """Raise a ValueError if the API response contains an error field.

    Args:
        response: A ChatCompletion or streaming chunk from the OpenAI API.

    Raises:
        ValueError: If the response carries an ``error`` in ``model_extra``.
    """
    if response.model_extra and response.model_extra.get("error"):
        raise ValueError(f"API error: {response.model_extra['error']}")


def _model_supports_temperature(model_name: str) -> bool:
    """Return True if *model_name* supports the temperature parameter.

    Args:
        model_name: The model identifier string.

    Returns:
        True for known GPT models that accept temperature; False otherwise.
    """
    return model_name in {
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
    }


def ai_create_openai_client() -> OpenAI | None:
    """Create and validate an OpenAI (or OpenAI-compatible) client.

    Reads connection details from ``config/secrets.py`` and verifies that
    the configured model is available on the endpoint.

    Returns:
        A ready-to-use ``OpenAI`` client, or ``None`` if creation fails.
    """
    try:
        print_lg("Creating OpenAI client...")
        if not use_AI:
            raise ValueError("AI is disabled. Set use_AI = True in config/secrets.py.")

        client = OpenAI(base_url=llm_api_url, api_key=llm_api_key)

        models = ai_get_models_list(client)
        if "error" in models:
            raise ValueError(str(models[1]))
        if not models:
            raise ValueError("No models are available at the configured endpoint.")
        if llm_model not in {m.id for m in models}:
            raise ValueError(f"Model '{llm_model}' not found at {llm_api_url}.")

        print_lg("---- OpenAI client ready ----")
        print_lg(f"Endpoint : {llm_api_url}")
        print_lg(f"Model    : {llm_model}")
        return client
    except Exception as e:
        _ai_error_alert(f"Failed to create OpenAI client.{_API_CHECK_INSTRUCTIONS}", e)
        return None


def ai_close_openai_client(client: OpenAI) -> None:
    """Close and clean up an OpenAI client connection.

    Args:
        client: The ``OpenAI`` client to close.
    """
    try:
        if client:
            print_lg("Closing OpenAI client...")
            client.close()
    except Exception as e:
        _ai_error_alert("Failed to close OpenAI client.", e)


def ai_get_models_list(client: OpenAI) -> list[Model] | list[str | Exception]:
    """Retrieve the list of models available at the configured endpoint.

    Args:
        client: An active ``OpenAI`` client.

    Returns:
        A list of ``Model`` objects, or ``["error", exception]`` on failure.
    """
    try:
        print_lg("Fetching available models...")
        if not client:
            raise ValueError("Client is not initialised.")
        models = client.models.list()
        _check_response_error(models)
        print_lg("Available models:", [m.id for m in models.data], pretty=True)
        return models.data
    except Exception as e:
        critical_error_log("Failed to retrieve models list.", e)
        return ["error", e]


def ai_completion(
    client: OpenAI,
    messages: list[dict[str, str]],
    response_format: dict[str, Any] | None = None,
    temperature: float = 0,
    stream: bool = stream_output,
) -> dict | str:
    """Send a chat-completion request and return the model's reply.

    Args:
        client: Active ``OpenAI`` client.
        messages: Conversation history as ``[{"role": ..., "content": ...}]``.
        response_format: Optional JSON schema for structured output.
        temperature: Sampling temperature (0 = deterministic).
        stream: Whether to stream the response token by token.

    Returns:
        Parsed dict if ``response_format`` was supplied, otherwise a string.

    Raises:
        ValueError: If the client is not initialised or the API returns an error.
    """
    if not client:
        raise ValueError("OpenAI client is not initialised.")

    params: dict[str, Any] = {
        "model": llm_model,
        "messages": messages,
        "stream": stream,
    }
    if _model_supports_temperature(llm_model):
        params["temperature"] = temperature
    if response_format and llm_spec in {"openai", "openai-like"}:
        params["response_format"] = response_format

    completion = client.chat.completions.create(**params)
    result = ""

    if stream:
        print_lg("-- Streaming started")
        for chunk in completion:
            _check_response_error(chunk)
            token = chunk.choices[0].delta.content
            if token is not None:
                result += token
            print_lg(token, end="", flush=True)
        print_lg("\n-- Streaming complete")
    else:
        _check_response_error(completion)
        result = completion.choices[0].message.content

    if response_format:
        result = convert_to_json(result)

    print_lg("\nAI response:\n")
    print_lg(result, pretty=bool(response_format))
    return result


def ai_extract_skills(
    client: OpenAI,
    job_description: str,
    stream: bool = stream_output,
) -> dict:
    """Extract and categorise skills from a job description.

    Args:
        client: Active ``OpenAI`` client.
        job_description: Full text of the LinkedIn job posting.
        stream: Whether to stream the response.

    Returns:
        Dict with keys ``tech_stack``, ``technical_skills``, ``other_skills``,
        ``required_skills``, ``nice_to_have`` — each a list of strings.
    """
    print_lg("-- Extracting skills from job description (OpenAI)")
    try:
        prompt = extract_skills_prompt.format(job_description)
        messages = [{"role": "user", "content": prompt}]
        return ai_completion(
            client,
            messages,
            response_format=extract_skills_response_format,
            stream=stream,
        )
    except Exception as e:
        _ai_error_alert(f"Failed to extract skills.{_API_CHECK_INSTRUCTIONS}", e)
        return {}


def ai_answer_question(
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
) -> str:
    """Generate an AI answer for a form question.

    Args:
        client: Active ``OpenAI`` client.
        question: The label text of the form question.
        options: List of valid options (for select-type questions).
        question_type: One of ``'text'``, ``'textarea'``,
            ``'single_select'``, ``'multiple_select'``.
        job_description: Optional job posting text for additional context.
        about_company: Optional company description for additional context.
        user_information_all: User's full profile/resume text.
        stream: Whether to stream the response.

    Returns:
        AI-generated answer string.
    """
    print_lg("-- Answering question via AI (OpenAI)")
    try:
        prompt = ai_answer_prompt.format(user_information_all or "N/A", question)
        if job_description and job_description != "Unknown":
            prompt += f"\n\nJob Description:\n{job_description}"
        if about_company and about_company != "Unknown":
            prompt += f"\n\nAbout the Company:\n{about_company}"

        messages = [{"role": "user", "content": prompt}]
        return ai_completion(client, messages, stream=stream)
    except Exception as e:
        _ai_error_alert(f"Failed to answer question.{_API_CHECK_INSTRUCTIONS}", e)
        return ""
