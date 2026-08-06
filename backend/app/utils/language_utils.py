"""Robust multilingual language detection.

Combines Unicode script detection (very reliable for Indic languages) with
statistical detectors (langid / langdetect) for Latin-script languages.

The existing pipeline relied only on ``langdetect``/``langid`` over a small
sample, which mislabeled Hindi text (garbled by OCR) as e.g. ``sq``.
Detecting the script first makes Indic-language detection reliable.
"""
from __future__ import annotations
import re
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Unicode script ranges (start, end) as (lo, hi) tuples.
_DEVANAGARI = (0x0900, 0x097F)   # Hindi, Marathi, Sanskrit, Nepali
_GUJARATI = (0x0A80, 0x0AFF)     # Gujarati
_BENGALI = (0x0980, 0x09FF)      # Bengali, Assamese
_GURMUKHI = (0x0A00, 0x0A7F)     # Punjabi
_TAMIL = (0x0B80, 0x0BFF)
_TELUGU = (0x0C00, 0x0C7F)
_KANNADA = (0x0C80, 0x0CFF)
_MALAYALAM = (0x0D00, 0x0D7F)
_ORIYA = (0x0B00, 0x0B7F)
_ARABIC = (0x0600, 0x06FF)
_CYRILLIC = (0x0400, 0x04FF)
_GREEK = (0x0370, 0x03FF)
_THAI = (0x0E00, 0x0E7F)
_CJK = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF)]
_LATIN = [(0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F), (0x1E00, 0x1EFF)]

# Script -> default language name (full name used in generated content).
SCRIPT_TO_LANGUAGE = {
    "devanagari": "Hindi",
    "gujarati": "Gujarati",
    "bengali": "Bengali",
    "gurmukhi": "Punjabi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "kannada": "Kannada",
    "malayalam": "Malayalam",
    "oriya": "Odia",
    "arabic": "Arabic",
    "cyrillic": "Russian",
    "greek": "Greek",
    "thai": "Thai",
    "cjk": "Chinese",
}

# ISO-639-1 code -> full language name.
_CODE_TO_NAME = {
    "hi": "Hindi",
    "mr": "Marathi",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "or": "Odia",
    "ar": "Arabic",
    "ru": "Russian",
    "el": "Greek",
    "th": "Thai",
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
}

# Weak/ambiguous codes that should not override a script-based result and
# are often returned for garbled/garbage OCR text.
_WEAK_CODES = {"sq", "so", "tl", "et", "lv", "lt", "sl", "hr", "bs", "id",
               "ms", "vi", "cs", "sk", "hu", "ro", "bg", "uk", "af", "sw"}

# Marathi-specific visual markers (Devanagari conjuncts/suffixes) to
# distinguish Hindi from Marathi when possible.
_MARATHI_MARKERS = ["ला", "चा", "ची", "चे", "नी", "मध्ये", "आहे", "आहेत", "व "]

# Language codes that should be ignored entirely (garbage/ambiguous).
_IGNORE_CODES = _WEAK_CODES | {"so", "tl"}


def _in_ranges(char: str, ranges) -> bool:
    cp = ord(char)
    if isinstance(ranges, tuple) and len(ranges) == 2 and isinstance(ranges[0], int):
        return ranges[0] <= cp <= ranges[1]
    for lo, hi in ranges:
        if lo <= cp <= hi:
            return True
    return False


def detect_script(text: str) -> Optional[str]:
    """Return the dominant script of ``text`` (e.g. 'devanagari', 'latin')."""
    if not text:
        return None

    counts: dict[str, int] = {}
    for ch in text:
        if ch.isspace():
            continue
        if _in_ranges(ch, _DEVANAGARI):
            counts["devanagari"] = counts.get("devanagari", 0) + 1
        elif _in_ranges(ch, _GUJARATI):
            counts["gujarati"] = counts.get("gujarati", 0) + 1
        elif _in_ranges(ch, _BENGALI):
            counts["bengali"] = counts.get("bengali", 0) + 1
        elif _in_ranges(ch, _GURMUKHI):
            counts["gurmukhi"] = counts.get("gurmukhi", 0) + 1
        elif _in_ranges(ch, _TAMIL):
            counts["tamil"] = counts.get("tamil", 0) + 1
        elif _in_ranges(ch, _TELUGU):
            counts["telugu"] = counts.get("telugu", 0) + 1
        elif _in_ranges(ch, _KANNADA):
            counts["kannada"] = counts.get("kannada", 0) + 1
        elif _in_ranges(ch, _MALAYALAM):
            counts["malayalam"] = counts.get("malayalam", 0) + 1
        elif _in_ranges(ch, _ORIYA):
            counts["oriya"] = counts.get("oriya", 0) + 1
        elif _in_ranges(ch, _ARABIC):
            counts["arabic"] = counts.get("arabic", 0) + 1
        elif _in_ranges(ch, _CYRILLIC):
            counts["cyrillic"] = counts.get("cyrillic", 0) + 1
        elif _in_ranges(ch, _GREEK):
            counts["greek"] = counts.get("greek", 0) + 1
        elif _in_ranges(ch, _THAI):
            counts["thai"] = counts.get("thai", 0) + 1
        elif _in_ranges(ch, _CJK):
            counts["cjk"] = counts.get("cjk", 0) + 1
        elif _in_ranges(ch, _LATIN):
            counts["latin"] = counts.get("latin", 0) + 1

    if not counts:
        return None
    return max(counts, key=counts.get)


def _sample_text(text: str, sample_size: int = 800, max_samples: int = 6) -> list[str]:
    """Split text into several non-overlapping samples for detection."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    samples = []
    step = max(sample_size, len(text) // max_samples) if text else sample_size
    for i in range(0, len(text), step):
        samples.append(text[i:i + sample_size])
        if len(samples) >= max_samples:
            break
    return samples if samples else [text]


def _classify_latin_text(text: str) -> Optional[str]:
    """Statistical classification for Latin-script text."""
    candidates: list[str] = []

    # langdetect
    try:
        from langdetect import detect as ld_detect
        from langdetect.lang_detect_exception import LangDetectException
        code = ld_detect(text)
        if code and code not in _IGNORE_CODES:
            candidates.append(code)
    except (LangDetectException, Exception):
        pass

    # langid
    try:
        import langid
        code, _ = langid.classify(text)
        if code and code not in _IGNORE_CODES:
            candidates.append(code)
    except Exception:
        pass

    if not candidates:
        return None

    # Majority vote
    from collections import Counter
    top = Counter(candidates).most_common(1)[0][0]
    return _CODE_TO_NAME.get(top, top)


def detect_language(text: str) -> str:
    """Detect the language of ``text``, defaulting to English on failure."""
    if not text or not text.strip():
        return "English"

    samples = _sample_text(text)

    # 1. Script-based detection (most reliable for Indic languages).
    script_counts: dict[str, int] = {}
    for s in samples:
        script = detect_script(s)
        if script:
            script_counts[script] = script_counts.get(script, 0) + 1

    if script_counts:
        dominant = max(script_counts, key=script_counts.get)

        # Non-Latin scripts map directly to a language.
        if dominant in SCRIPT_TO_LANGUAGE:
            lang = SCRIPT_TO_LANGUAGE[dominant]

            # Refine Devanagari: distinguish Hindi vs Marathi.
            if dominant == "devanagari":
                joined = " ".join(samples)
                if any(m in joined for m in _MARATHI_MARKERS):
                    return "Marathi"
            return lang

        # Latin script: use statistical detectors.
        if dominant == "latin":
            detected = _classify_latin_text(text)
            if detected:
                return detected

    # 2. Fallback: statistical detection over the whole text.
    detected = _classify_latin_text(text)
    if detected:
        return detected

    logger.warning("lang_detect_fallback_english", char_count=len(text))
    return "English"


def language_code_to_name(code: str) -> str:
    """Map an ISO-639-1 code to a full language name."""
    if not code:
        return "English"
    return _CODE_TO_NAME.get(code.lower(), code)


def is_non_latin_script(text: str) -> bool:
    """Return True if the dominant script of ``text`` is non-Latin."""
    script = detect_script(text)
    return script is not None and script != "latin"
