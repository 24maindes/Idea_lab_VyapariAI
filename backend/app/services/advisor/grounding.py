"""
advisor/grounding.py - the HALLUCINATION CHECK.

An answer is "grounded" when every PRICE-LIKE number in it can be found in the context we gave the model
(within 1 %). Price-like = a number after "Rs" / "₹" or before "/kg", "/litre", "/packet", "/box" (also "per kg").
Other numbers (days, percentages, quantities) are not checked here; the prompt rules cover them.

If the check fails, the router asks the model once more with a stricter instruction, and if that also fails it
returns the offline template answer (which only uses real numbers) and writes the failure to a log file.
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path

TOLERANCE = 0.01                                             # 1 %
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_NUM = r"(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_AFTER_RS = re.compile(r"(?:rs\.?|₹|inr|रु\.?|रुपये|रुपए)\s*" + _NUM, re.IGNORECASE)
_BEFORE_UNIT = re.compile(_NUM + r"\s*(?:/|per\s+)\s*(?:kg|litre|liter|l|packet|box)\b", re.IGNORECASE)


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def price_numbers(answer: str) -> list[float]:
    """All price-like numbers in an answer (Devanagari digits are converted first)."""
    text = answer.translate(_DEVANAGARI_DIGITS)
    found = [_to_float(m) for m in _AFTER_RS.findall(text)] + [_to_float(m) for m in _BEFORE_UNIT.findall(text)]
    return found


_PRICE_KEY = re.compile(r"price|savings|value|recommended|rangelow|rangehigh|cost|floor|target|low$|high$", re.IGNORECASE)


def context_price_numbers(context: dict) -> list[float]:
    """
    The numbers in the context that ARE prices or rupee amounts: numeric values stored under price-like keys
    (lastPurchasePrice, marketPrice, avgPrice, recommended, rangeLow ...) plus numbers written as "Rs 58" or "42/kg"
    inside text. Quantities, days and percentages are NOT included, so a made-up price cannot pass just because the
    same digits appear somewhere else (for example "5 days").
    """
    out: list[float] = []

    def walk(x, key=""):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            if _PRICE_KEY.search(key):
                out.append(float(x))
        elif isinstance(x, str):
            out.extend(price_numbers(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v, key)

    walk(context)
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(abs(b) * TOLERANCE, 0.005)


def ungrounded_numbers(answer: str, context: dict) -> list[float]:
    """Price-like numbers of the answer that do NOT appear in the context. Empty list = grounded."""
    known = context_price_numbers(context)
    return sorted({n for n in price_numbers(answer) if not any(_close(n, k) for k in known)})


def log_failure(question: str, answer: str, bad: list[float], attempt: int, final: bool) -> None:
    """Append a line to logs/advisor_grounding.log (never raises)."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "advisor_grounding.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "attempt": attempt, "usedFallbackAfterThis": final,
                                "question": question[:300], "answer": answer[:600], "ungroundedNumbers": bad}, ensure_ascii=False) + "\n")
    except Exception:
        logging.getLogger("vyapari.advisor").exception("could not write the grounding log")


# ---------------------------------------------------------------- input safety
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ROLE_MARKERS = re.compile(r"(?im)^\s*(system|assistant|model|developer)\s*:")


def sanitize(text: str, limit: int = 500) -> str:
    """Clean user text before it goes into the prompt or the history: no control characters, no fake role lines."""
    text = _CONTROL.sub("", text or "")
    text = _ROLE_MARKERS.sub(lambda m: m.group(1) + " -", text)       # "system: do X" can no longer look like a role line
    text = text.replace("```", "'''")
    return re.sub(r"[ \t]+", " ", text).strip()[:limit]


# ---------------------------------------------------------------- scope (medical / legal / beyond the forecast)
OUT_OF_SCOPE = ["doctor", "medicine", "medical", "diabetes", "diabetic", "disease", "illness", "tablet", "symptom", "treatment", "cancer", "pregnan",
                "lawyer", "legal advice", "court", "lawsuit", "sue ", "police case", "tax notice", "gst notice",
                "डॉक्टर", "दवा", "दवाई", "बीमारी", "मधुमेह", "इलाज", "वकील", "कोर्ट", "कानूनी", "औषध", "आजार", "उपचार", "न्यायालय", "कायदेशीर", "डायबिटीज", "डायबेटीस", "dawai", "dawa", "ilaj", "bimari", "vakil", "kayda"]
BEYOND_HORIZON = ["next year", "next month", "next 6 months", "six months", "in a year", "after a year", "long term", "अगले साल", "अगले महीने", "पुढच्या वर्षी", "पुढच्या महिन्यात",
                  "agle saal", "agle mahine", "next saal"]


def is_out_of_scope(message: str) -> bool:
    low = message.lower() + " "
    return any(w in low for w in OUT_OF_SCOPE)


def asks_beyond_horizon(message: str) -> bool:
    low = message.lower()
    return any(w in low for w in BEYOND_HORIZON)
