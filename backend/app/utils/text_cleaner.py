"""OCR / encoding cleanup for extracted document text.

Removes broken Unicode, encoding artifacts, random symbols, mixed-script
noise, and invalid OCR words — while preserving scientific notation
(chemical formulas, subscripts, superscripts, Greek letters, equations).

This runs BEFORE chunking / indexing so that garbage never flows into RAG
or the generated teacher package.
"""
from __future__ import annotations
import re
import unicodedata

# ─────────────────────────── Control / replacement chars ───────────────────────────

# Unassigned / private-use / replacement codepoints that indicate OCR breakdown.
_BAD_CATEGORIES = {"Cn", "Co", "Cs", "Cc"}
_REPLACEMENT_CHAR = "\ufffd"

# Common OCR artifacts seen when a ligature map goes wrong.
_OCR_ARTIFACT_PATTERNS = [
    # Odd sequences like  %Ï ,  xzafFk ,  var%Ïkoh  (broken Devanagari)
    re.compile(r"[%\u00d7\u00f7\u00c7\u00e7\u00d1\u00f1\u00c9\u00e9][\u00c0-\u024f]{1,3}"),
    # Runs of mixed thin diacritics
    re.compile(r"[\u0300-\u036f]{3,}"),
    # Mojibake: repeated Â/Ã before Latin
    re.compile(r"(?:[\u00c2\u00c3\u00c4\u00c5]){2,}"),
]

# Whitelisted scripts that are meaningful in scientific/educational content.
_VALID_SCRIPT_RANGES = [
    (0x0020, 0x007E),   # Basic Latin
    (0x00A0, 0x00FF),   # Latin-1 supplement
    (0x0100, 0x024F),   # Latin extended
    (0x0370, 0x03FF),   # Greek/ Coptic
    (0x0400, 0x04FF),   # Cyrillic
    (0x0500, 0x052F),   # Cyrillic supplement
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0900, 0x097F),   # Devanagari
    (0x0980, 0x09FF),   # Bengali
    (0x0A00, 0x0A7F),   # Gurmukhi
    (0x0A80, 0x0AFF),   # Gujarati
    (0x0B00, 0x0B7F),   # Oriya
    (0x0B80, 0x0BFF),   # Tamil
    (0x0C00, 0x0C7F),   # Telugu
    (0x0C80, 0x0CFF),   # Kannada
    (0x0D00, 0x0D7F),   # Malayalam
    (0x0E00, 0x0E7F),   # Thai
    (0x1E00, 0x1EFF),   # Latin extended additional
    (0x2000, 0x206F),   # General punctuation
    (0x2070, 0x209F),   # Superscripts/subscripts
    (0x20A0, 0x20CF),   # Currency symbols
    (0x2100, 0x214F),   # Letterlike symbols (incl. ⁻ ²)
    (0x2150, 0x218F),   # Number forms
    (0x2190, 0x21FF),   # Arrows
    (0x2200, 0x22FF),   # Mathematical operators
    (0x2300, 0x23FF),   # Miscellaneous technical
    (0x25A0, 0x25FF),   # Geometric shapes
    (0x2600, 0x26FF),   # Misc symbols
    (0x27C0, 0x27EF),   # Misc math symbols-A
    (0x2980, 0x29FF),   # Misc math symbols-B
    (0x2B30, 0x2B4F),   # Arrows supplemental
    (0x3000, 0x303F),   # CJK punctuation
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0x4E00, 0x9FFF),   # CJK unified
    (0xAC00, 0xD7AF),   # Hangul
    (0xFB00, 0xFB06),   # Latin ligatures
    (0xFF00, 0xFFEF),   # Fullwidth/halfwidth forms
]

# Characters that are almost never valid in natural text.
_HARMFUL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _char_in_valid_ranges(cp: int) -> bool:
    for lo, hi in _VALID_SCRIPT_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def _is_meaningful_char(ch: str) -> bool:
    """Return True if a char is a letter, digit, combining mark, or valid symbol."""
    if ch.isspace():
        return True
    cat = unicodedata.category(ch)
    if cat.startswith(("L", "N", "M")):
        return True
    if cat in {"Pd", "Po", "Ps", "Pe", "Pi", "Pf", "Sc", "Sm", "Sk"}:
        return True
    return False


def clean_text(text: str) -> str:
    """Remove OCR garbage and encoding artifacts while preserving content."""
    if not text:
        return ""

    # 1. Normalize Unicode (NFKC folds ligatures, fullwidth forms, etc.).
    text = unicodedata.normalize("NFKC", text)

    # 2. Strip harmful control characters.
    text = _HARMFUL.sub(" ", text)

    # 3. Remove replacement characters and invalid codepoints.
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == _REPLACEMENT_CHAR:
            continue
        cat = unicodedata.category(ch)
        if cat in _BAD_CATEGORIES:
            continue
        if not _char_in_valid_ranges(cp):
            continue
        out.append(ch)
    text = "".join(out)

    # 4. Remove common OCR artifact patterns.
    for pattern in _OCR_ARTIFACT_PATTERNS:
        text = pattern.sub(" ", text)

    # 5. Collapse leftover whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def _latin_ratio(text: str) -> float:
    """Ratio of Latin letters to total letters (used for quality scoring)."""
    total = 0
    latin = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            total += 1
            if "latin" in unicodedata.name(ch, "").lower():
                latin += 1
    return (latin / total) if total else 1.0


def _devanagari_ratio(text: str) -> float:
    total = 0
    dev = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            total += 1
            if 0x0900 <= ord(ch) <= 0x097F:
                dev += 1
    return (dev / total) if total else 0.0


def _suspicious_symbol_ratio(text: str) -> float:
    """Ratio of non-letter, non-digit, non-space, non-punct symbols."""
    if not text:
        return 0.0
    count = 0
    meaningful = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(("L", "N", "Z")):
            meaningful += 1
        elif cat in {"Sm", "Po", "Pd", "Ps", "Pe", "Sc", "Sk"}:
            meaningful += 1
        else:
            count += 1
    total = meaningful + count
    return (count / total) if total else 0.0


def assess_ocr_quality(text: str) -> dict:
    """Score the quality of extracted text on a 0–1 scale.

    Returns a dict with keys: ``score``, ``latin_ratio``, ``symbol_ratio``,
    ``replacement_chars``, ``word_length_ok``, ``nonempty``.
    """
    if not text or not text.strip():
        return {"score": 0.0, "latin_ratio": 0.0, "symbol_ratio": 1.0,
                "replacement_chars": 0, "word_length_ok": False, "nonempty": False}

    words = re.findall(r"\S+", text)
    if not words:
        return {"score": 0.0, "latin_ratio": _latin_ratio(text),
                "symbol_ratio": 1.0, "replacement_chars": 0,
                "word_length_ok": False, "nonempty": False}

    # Fraction of words that look like valid (length 2-30) words.
    ok_words = sum(1 for w in words if 2 <= len(w) <= 30)
    word_length_ok = ok_words / len(words)

    latin_ratio = _latin_ratio(text)
    dev_ratio = _devanagari_ratio(text)
    symbol_ratio = _suspicious_symbol_ratio(text)
    replacement_chars = text.count(_REPLACEMENT_CHAR)

    # Score: prioritize having a clear dominant script and readable words.
    script_dominance = max(latin_ratio, dev_ratio)
    score = (
        0.5 * min(word_length_ok, 1.0)
        + 0.3 * script_dominance
        - 0.3 * symbol_ratio
        - 0.2 * min(1.0, replacement_chars / max(len(text), 1))
    )
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 3),
        "latin_ratio": round(latin_ratio, 3),
        "symbol_ratio": round(symbol_ratio, 3),
        "replacement_chars": replacement_chars,
        "word_length_ok": round(word_length_ok, 3),
        "nonempty": True,
    }
