"""Role-label normalization, separate from document parsing."""

from __future__ import annotations

import re

from collections.abc import Collection
from typing import Protocol


class _TaxonomyLike(Protocol):
    roles: tuple[str, ...]


_PHRASE_RULES = (
    (re.compile(r"\b(conceived|designed (?:the )?study)\b", re.IGNORECASE), "Conceptualization"),
    (re.compile(r"\b(analy[sz]ed|statistical analysis)\b", re.IGNORECASE), "Formal analysis"),
    (re.compile(r"\b(collected (?:the )?data|performed (?:the )?experiments?)\b", re.IGNORECASE), "Investigation"),
    (re.compile(r"\b(acquired funding|funding acquisition)\b", re.IGNORECASE), "Funding acquisition"),
    (re.compile(r"\b(administered (?:the )?project|project administration)\b", re.IGNORECASE), "Project administration"),
    (re.compile(r"\b(provided resources?)\b", re.IGNORECASE), "Resources"),
    (re.compile(r"\b(developed (?:the )?(?:analysis )?code|software development)\b", re.IGNORECASE), "Software"),
    (re.compile(r"\b(checked results?|validated)\b", re.IGNORECASE), "Validation"),
    (re.compile(r"\b(supervised)\b", re.IGNORECASE), "Supervision"),
    (re.compile(r"\b(created (?:the )?figures?|visuali[sz]ation)\b", re.IGNORECASE), "Visualization"),
    (re.compile(r"\b(wrote (?:the )?(?:initial |original )?draft|wrote the manuscript)\b", re.IGNORECASE), "Writing – original draft"),
    (re.compile(r"\b(reviewed|edited|wrote and edited)\b", re.IGNORECASE), "Writing – review & editing"),
)


def canonicalize_label(value: str) -> str:
    """Normalize case and dash variants before taxonomy validation."""
    value = value.replace("–", "-").replace("—", "-").replace("�", "-")
    value = value.replace("&", "and")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _role_collection(official_roles: Collection[str] | _TaxonomyLike) -> Collection[str]:
    return getattr(official_roles, "roles", official_roles)


def normalize_role(value: str, official_roles: Collection[str] | _TaxonomyLike) -> str | None:
    """Return an exact official role after presentation normalization.

    Narrative phrase mapping (for example, "made the tea") is deliberately not
    implemented here; unmapped phrases must remain visible to callers.
    """
    target = canonicalize_label(value)
    for role in _role_collection(official_roles):
        if canonicalize_label(role) == target:
            return role
    return None


def map_contribution_phrase(value: str, official_roles: Collection[str] | _TaxonomyLike) -> tuple[str, ...]:
    """Map high-confidence wording to roles present in the fetched taxonomy.

    Rule targets are role *names*, not a bundled taxonomy: a match is returned
    only when that name validates against the supplied NISO taxonomy. Unknown
    text returns an empty tuple, leaving the caller's original phrase intact.
    """
    mapped: list[str] = []
    for pattern, candidate in _PHRASE_RULES:
        if pattern.search(value):
            role = normalize_role(candidate, official_roles)
            if role is not None and role not in mapped:
                mapped.append(role)
    return tuple(mapped)

