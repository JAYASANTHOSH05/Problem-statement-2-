"""Conservative author-roster extraction and matching helpers."""

from __future__ import annotations

import re

from models import Author, TextBlock


_HONORIFICS = frozenset({"dr", "prof", "professor", "mr", "mrs", "ms"})
_FRONT_MATTER_REJECTIONS = re.compile(
    r"\b(abstract|corresponding|author contributions?|contributors?|"
    r"department|faculty|school|institute|university|received|accepted|"
    r"keywords|article history|funding|acknowledg)\b|@",
    re.IGNORECASE,
)


def _name_words(value: str) -> list[str]:
    """Return name words after removing titles and affiliation-style markers."""
    words = re.findall(r"[A-Za-z]+", value)
    while words and words[0].casefold() in _HONORIFICS:
        words.pop(0)
    return words


def _clean_display_name(value: str) -> str:
    words = _name_words(value)
    return " ".join(words)


def normalize_token(value: str) -> str:
    """Normalize a name or initials for comparison without inferring identity."""
    return "".join(word.casefold() for word in _name_words(value))


def author_variants(display_name: str) -> frozenset[str]:
    """Return conservative full-name and initial forms for a known roster author."""
    words = _name_words(display_name)
    variants = {"".join(word.casefold() for word in words)}
    if len(words) >= 2:
        variants.add("".join(word[0].casefold() for word in words))
        # Middle names are often omitted in contribution statements.
        variants.add((words[0][0] + words[-1][0]).casefold())
    return frozenset(variant for variant in variants if variant)


def extract_authors(body: list[TextBlock]) -> list[Author]:
    """Extract the first plausible author line from manuscript front matter.

    The manuscripts place the title first and the roster immediately after it.
    This function only accepts comma/semicolon/``and`` separated full names; it
    deliberately does not treat affiliations, email lines, or contribution text
    as author lists.
    """
    for block in body[1:12]:
        if _FRONT_MATTER_REJECTIONS.search(block.text):
            continue
        names = _split_author_line(block.text)
        if names:
            return [
                Author(
                    display_name=name,
                    normalized_name=normalize_token(name),
                    variants=author_variants(name),
                )
                for name in names
            ]
    return []


def _split_author_line(value: str) -> list[str]:
    """Return a roster only when every comma-separated item is a plausible name."""
    if not value or "@" in value:
        return []
    candidates = re.split(r"\s*(?:,|;|\band\b)\s*", value, flags=re.IGNORECASE)
    names = [_clean_display_name(candidate) for candidate in candidates if candidate.strip()]
    if not names or not all(_is_plausible_name(name) for name in names):
        return []
    return names


def _is_plausible_name(value: str) -> bool:
    words = value.split()
    return 2 <= len(words) <= 4 and all(word[0].isupper() for word in words)


def match_author(token: str, authors: list[Author]) -> Author | None:
    """Match only an unambiguous known roster variant; otherwise return ``None``."""
    key = normalize_token(token)
    if not key:
        return None
    matches = [author for author in authors if key in author.variants]
    return matches[0] if len(matches) == 1 else None

