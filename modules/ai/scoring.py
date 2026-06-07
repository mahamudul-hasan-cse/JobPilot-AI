# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""AI job relevance scoring for JobPilot AI.

Scores how well a job posting matches the user's profile using the
configured AI provider. Includes a per-run cache and a quota circuit
breaker to skip AI calls when API limits are exceeded.
"""

from typing import Any

from modules.ai.prompts import job_scoring_prompt
from modules.helpers import convert_to_json, critical_error_log, print_lg

_MAX_TEXT_LENGTH = 4000

# Per-run cache: job_id -> score result
_score_cache: dict[str, dict[str, Any]] = {}

# Session flag: when True, all AI calls are skipped for the rest of the run
_quota_circuit_open = False


def is_ai_quota_exhausted() -> bool:
    """Return whether the quota circuit breaker has tripped for this session.

    Returns:
        ``True`` when AI calls should be skipped for the remainder of the run.
    """
    return _quota_circuit_open


def reset_ai_quota_circuit() -> None:
    """Reset the quota circuit breaker.

    Call once at the start of each bot run.
    """
    global _quota_circuit_open
    _quota_circuit_open = False


def trip_ai_quota_circuit(error: str = "") -> None:
    """Trip the quota circuit breaker and log a warning.

    Args:
        error: Optional API error detail to include in the log output.
    """
    global _quota_circuit_open
    if _quota_circuit_open:
        return
    _quota_circuit_open = True
    print_lg(
        "WARNING: Gemini API quota exceeded (429). "
        "Disabling all AI calls for the rest of this session. "
        "Continuing to apply without AI scoring."
    )
    if error:
        print_lg(f"Quota error detail: {error[:400]}")


def is_quota_error(message: str) -> bool:
    """Return whether a message indicates Gemini quota or rate-limit exhaustion.

    Args:
        message: Raw error text from an API response or exception.

    Returns:
        ``True`` when the message matches known quota-exhaustion patterns.
    """
    normalized_message = (message or "").lower()
    return (
        "429" in message
        or "quota exceeded" in normalized_message
        or "quota_value" in normalized_message
        or "generate_content_free_tier_requests" in normalized_message
        or "rate limit" in normalized_message
    )


def clear_score_cache() -> None:
    """Clear the in-memory relevance score cache.

    Call at the start of each run to avoid stale scores across sessions.
    """
    _score_cache.clear()


def _truncate(text: str, max_len: int = _MAX_TEXT_LENGTH) -> str:
    """Truncate long text for API calls.

    Args:
        text: Input string to trim.
        max_len: Maximum allowed character length.

    Returns:
        The original text when within limits, otherwise a truncated copy
        ending with ``"..."``.
    """
    cleaned_text = (text or "").strip()
    if len(cleaned_text) <= max_len:
        return cleaned_text
    return cleaned_text[: max_len - 3] + "..."


def _quota_bypass_result() -> dict[str, Any]:
    """Build a score result used when AI quota is exhausted.

    Returns:
        A fail-open score dict that allows applications to continue.
    """
    return {
        "score": 100,
        "reason": "AI quota exhausted — applying without relevance scoring.",
        "matched_skills": [],
        "missing_skills": [],
    }


def _parse_score_response(
    raw: str | dict[str, Any],
    fail_open: bool = True,
) -> dict[str, Any]:
    """Parse AI JSON into a validated score dict.

    Args:
        raw: Model response as a JSON string or already-parsed dict.
        fail_open: When ``True``, use score 100 on parse failure; otherwise 0.

    Returns:
        Normalized dict with ``score``, ``reason``, ``matched_skills``, and
        ``missing_skills`` keys.
    """
    fallback_score = 100 if fail_open else 0
    fallback_reason = (
        "Scoring unavailable — applying anyway."
        if fail_open
        else "Scoring failed — skipped (strict mode)."
    )
    fallback: dict[str, Any] = {
        "score": fallback_score,
        "reason": fallback_reason,
        "matched_skills": [],
        "missing_skills": [],
    }

    if isinstance(raw, str):
        if is_quota_error(raw):
            trip_ai_quota_circuit(raw)
            return _quota_bypass_result()
        raw = convert_to_json(raw)

    if not isinstance(raw, dict) or "error" in raw:
        if isinstance(raw, dict):
            error_text = str(raw.get("error", raw))
        else:
            error_text = str(raw)
        if is_quota_error(error_text):
            trip_ai_quota_circuit(error_text)
            return _quota_bypass_result()
        print_lg(
            f"Could not parse relevance score — using fallback "
            f"(score={fallback_score})."
        )
        return fallback

    score = raw.get("score", fallback_score)
    try:
        score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score = fallback_score

    return {
        "score": score,
        "reason": str(raw.get("reason", "")),
        "matched_skills": raw.get("matched_skills", []),
        "missing_skills": raw.get("missing_skills", []),
    }


def ai_score_job_relevance(
    client: Any,
    job_description: str,
    user_profile: str,
    provider: str,
    job_id: str | None = None,
    fail_open: bool = True,
) -> dict[str, Any]:
    """Score how well a job matches the user's profile using AI.

    Args:
        client: Active AI client.
        job_description: Full job posting text.
        user_profile: User profile or resume text.
        provider: AI provider name.
        job_id: Optional job ID for caching within a run.
        fail_open: If ``True``, return score 100 on failure; else score 0.

    Returns:
        Dict with ``score``, ``reason``, ``matched_skills``, and
        ``missing_skills`` keys.
    """
    if is_ai_quota_exhausted():
        result = _quota_bypass_result()
        if job_id:
            _score_cache[job_id] = result
        return result

    if job_id and job_id in _score_cache:
        print_lg(f"Using cached relevance score for job {job_id}.")
        return _score_cache[job_id]

    print_lg("-- Scoring job relevance via AI")
    try:
        profile = _truncate(user_profile)
        description = _truncate(job_description)
        prompt = job_scoring_prompt.format(profile, description)
        prompt += "\n\nReturn ONLY the JSON object. No markdown, no extra text."

        from modules.ai.client_factory import _completion_json

        raw_response = _completion_json(client, provider, prompt)
        result = _parse_score_response(raw_response, fail_open=fail_open)
        print_lg(
            f"Relevance score: {result['score']}/100 | {result['reason']}"
        )

        if job_id:
            _score_cache[job_id] = result
        return result

    except Exception as exc:
        error_message = str(exc)
        if is_quota_error(error_message):
            trip_ai_quota_circuit(error_message)
            result = _quota_bypass_result()
        else:
            critical_error_log("Job relevance scoring failed.", exc)
            result = _parse_score_response(
                {"error": error_message},
                fail_open=fail_open,
            )
        if job_id:
            _score_cache[job_id] = result
        return result
