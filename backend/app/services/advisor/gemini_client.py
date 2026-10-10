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
    key, model = _config()
    try:
        from google import genai
        from google.genai import types
    except Exception as e:                                         # the package is not installed
        raise AdvisorUnavailable(f"google-genai is not installed: {e}") from e

    last_error: Exception | None = None
    for _attempt in range(2):                                      # first try + one retry
        try:
            client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))
            response = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=TEMPERATURE))
            text = (getattr(response, "text", None) or "").strip()
            if not text:
                raise AdvisorUnavailable("The model returned an empty answer")
            return text
        except AdvisorUnavailable as e:
            last_error = e
        except Exception as e:                                     # quota, network, timeout, bad key ...
            last_error = e
    raise AdvisorUnavailable(f"Gemini request failed: {type(last_error).__name__}: {last_error}") from last_error
