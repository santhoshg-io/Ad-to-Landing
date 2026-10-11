import re
import difflib
from typing import Dict, Any, Union

def normalize_text_for_search(text: str) -> str:
    """Normalize text by stripping punctuation, normalizing whitespace and lowercasing."""
    if not text:
        return ""
    cleaned = re.sub(r"[\r\n\t]+", " ", str(text))
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def verify_quote_in_landing_page(quote: str, raw_full_text: Union[str, Dict[str, Any]], hero_text: str = "") -> Dict[str, Any]:
    """
    Programmatic hallucination detection.
    Verifies if the LLM's cited `page_quote` actually exists in the source text.
    Also detects if the quote is situated Above-The-Fold (Hero) or buried below.
    Safely handles both string text and parsed_page dictionary inputs.
    """
    # Safe handling if a parsed_page dict is passed directly as second argument
    if isinstance(raw_full_text, dict):
        hero_text = str(raw_full_text.get("hero_text", "") or "")
        full_text_str = str(raw_full_text.get("raw_full_text") or raw_full_text.get("raw_clean_text") or "")
    else:
        full_text_str = str(raw_full_text or "")
        hero_text = str(hero_text or "")

    if not quote or str(quote).strip() == "":
        return {
            "status": "EMPTY",
            "is_above_the_fold": False,
            "match_ratio": 0.0,
            "details": "No quote provided by auditor."
        }

    stripped_quote = str(quote).strip()

    # Case 1: Check if the LLM explicitly declared that the claim is absent/omitted (e.g. NONE)
    absence_patterns = [
        r"^\[?none\]?$",
        r"^none$",
        r"^n/?a$",
        r"\[?not (found|present|mentioned|included|available).*\]?",
        r"\[?absent.*\]?"
    ]
    for pattern in absence_patterns:
        if re.match(pattern, stripped_quote, re.IGNORECASE):
            return {
                "status": "OMISSION_NOTED",
                "is_above_the_fold": False,
                "match_ratio": 0.0,
                "details": "Auditor confirmed claim is completely absent from the landing page ('NONE')."
            }

    # Case 2: Exact verbatim substring match
    if stripped_quote in full_text_str:
        is_hero = bool(hero_text and stripped_quote in hero_text)
        return {
            "status": "VERIFIED",
            "is_above_the_fold": is_hero,
            "match_ratio": 1.0,
            "details": "Exact verbatim quote verified in source landing page."
        }

    # Case 3: Normalized substring match
    norm_quote = normalize_text_for_search(stripped_quote)
    norm_raw = normalize_text_for_search(full_text_str)
    norm_hero = normalize_text_for_search(hero_text)

    if len(norm_quote) > 6 and norm_quote in norm_raw:
        is_hero = bool(norm_hero and norm_quote in norm_hero)
        return {
            "status": "VERIFIED",
            "is_above_the_fold": is_hero,
            "match_ratio": 0.95,
            "details": "Normalized quote verified (matched with slight whitespace/punctuation variation)."
        }

    # Compute fuzzy overlap ratio for unverified/hallucinated quotes
    words = norm_quote.split()
    if words and len(words) >= 3:
        found_words = sum(1 for w in words if w in norm_raw)
        token_ratio = found_words / len(words)
    else:
        token_ratio = 0.0

    return {
        "status": "HALLUCINATED",
        "is_above_the_fold": False,
        "match_ratio": round(token_ratio, 2),
        "details": "HALLUCINATION WARNING: This quoted text does NOT exist verbatim anywhere in the landing page!"
    }
