"""Spec 5.2 and 5.5: the one place for text cleaning, the match key and sentence splitting."""
import re
import unicodedata

INVISIBLE = "­​‌‍⁠﻿"
EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
PHONE = r"(?:\+|\b00)\d{2}[\d\s/().-]{7,}\d|\b0\d{2}[\s/]\d{3}[\s/]?\d{2}\s?\d{2}\b"
CONTACT_RE = re.compile(f"{EMAIL}|{PHONE}")
AI_ADDRESSED = re.compile(  # text addressed to an AI system (spec section 4)
    r"ignore (?:all |any )?(?:previous|prior|above) instructions|system prompt|disregard (?:all |the )?(?:previous|prior|above)"
    r"|you are (?:an? )?(?:ai|language model|assistant|chatbot)\b|as an ai\b", re.I)
HYPHENS = re.compile(r"[‐-―−'’`´-]")


def clean_text(text: str) -> str:
    text = CONTACT_RE.sub("", unicodedata.normalize("NFKC", text).translate({ord(c): None for c in INVISIBLE}))
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    assert not any(c in text for c in INVISIBLE) and not CONTACT_RE.search(text)
    return text


def match_key(text: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(HYPHENS.sub(" ", folded.lower()).split())


def sentences(text: str) -> list[str]:
    parts = (s.strip() for line in text.splitlines() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜÀ-Ý0-9\"“])", line))
    return [s for s in parts if len(s.split()) >= 3]


def words(text: str) -> int:
    return len(text.split())
