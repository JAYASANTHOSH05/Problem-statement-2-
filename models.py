"""Shared, intentionally small data model for manuscript processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity = Severity.WARNING
    location: str | None = None


@dataclass(frozen=True)
class TextBlock:
    """A textual unit extracted from a DOCX part."""

    text: str
    location: str  # e.g. body:paragraph:42 or header1:paragraph:0
    kind: str = "paragraph"
    cells: tuple[str, ...] = ()
    source_text: str | None = None


@dataclass
class DocumentContent:
    source: Path
    body: list[TextBlock] = field(default_factory=list)
    tables: list[TextBlock] = field(default_factory=list)
    headers: list[TextBlock] = field(default_factory=list)
    footers: list[TextBlock] = field(default_factory=list)


@dataclass(frozen=True)
class Author:
    display_name: str
    normalized_name: str
    variants: frozenset[str]


@dataclass(frozen=True)
class Contribution:
    """Common parser output; do not require every input to be perfectly mapped."""

    author_token: str
    role: str | None
    source_text: str
    location: str
    degree: str | None = None


@dataclass
class DocumentResult:
    source: Path
    authors: list[Author] = field(default_factory=list)
    contributions: list[Contribution] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

