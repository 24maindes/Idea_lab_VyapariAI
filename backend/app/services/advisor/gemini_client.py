"""
advisor/gemini_client.py - talks to Google's Gemini model with the google-genai SDK.

Settings come from the environment (never written in code):
    GEMINI_API_KEY   your key from https://aistudio.google.com
    GEMINI_MODEL     the model name, e.g. the current Gemini Flash model
temperature 0.2 (answers stay factual and repeatable), timeout 20 seconds, ONE retry.
Every problem (no key, quota, no internet, timeout, empty answer) becomes the same clean AdvisorUnavailable error,
so the caller can switch to the offline fallback.
"""
import os

TIMEOUT_SECONDS = 20
TEMPERATURE = 0.2


class AdvisorUnavailable(Exception):
    """The AI model cannot be used right now. The message says why (safe to log, not shown to the user as is)."""


def _config() -> tuple[str, str]:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    model = (os.getenv("GEMINI_MODEL") or "").strip()
    if not key:
        raise AdvisorUnavailable("GEMINI_API_KEY is not set")
    if not model:
        raise AdvisorUnavailable("GEMINI_MODEL is not set")
    return key, model


def generate(system_instruction: str, contents: list[dict]) -> str:
    """Return the model's answer text, or raise AdvisorUnavailable."""
    key, primary_model = _config()
    try:
        from google import genai
        from google.genai import types
    except Exception as e:                                         # the package is not installed
        raise AdvisorUnavailable(f"google-genai is not installed: {e}") from e

    models_to_try = [primary_model]
    for fallback_m in ("gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"):
        if fallback_m not in models_to_try:
            models_to_try.append(fallback_m)

    last_error: Exception | None = None
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))
    for m in models_to_try:
        for _attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=m, contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=TEMPERATURE))
                text = (getattr(response, "text", None) or "").strip()
                if text:
                    return text
            except Exception as e:
                last_error = e
                # If high demand or timeout on this model, break attempt loop to try next healthy model
                err_str = str(e).lower()
                if "503" in err_str or "unavailable" in err_str or "504" in err_str or "deadline" in err_str:
                    break
    raise AdvisorUnavailable(f"Gemini request failed: {type(last_error).__name__}: {last_error}") from last_error
