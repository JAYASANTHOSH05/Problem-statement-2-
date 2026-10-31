"""Retrieve and validate the official NISO CRediT taxonomy."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
from urllib.error import URLError
from urllib.request import Request, urlopen


OFFICIAL_TAXONOMY_URL = "https://credit.niso.org/contributor-roles-defined/"
EXPECTED_ROLE_COUNT = 14
OFFICIAL_ROLE_NAMES = frozenset(
    {
        "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
        "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
        "Visualization", "Writing – original draft", "Writing – review & editing",
    }
)


class TaxonomyFetchError(RuntimeError):
    """The official taxonomy could not be retrieved or parsed safely."""


@dataclass(frozen=True)
class Taxonomy:
    roles: tuple[str, ...]
    descriptions: dict[str, str]
    source_url: str = OFFICIAL_TAXONOMY_URL

    def validate(self) -> None:
        if len(self.roles) != EXPECTED_ROLE_COUNT:
            raise ValueError(f"Expected {EXPECTED_ROLE_COUNT} CRediT roles, got {len(self.roles)}")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("CRediT taxonomy contains duplicate role names")
        if set(self.roles) != OFFICIAL_ROLE_NAMES:
            raise ValueError("CRediT taxonomy contains invalid role names")
        if set(self.descriptions) != set(self.roles) or not all(self.descriptions.values()):
            raise ValueError("Each CRediT role must have one non-empty description")


class _RoleDescriptorParser(HTMLParser):
    """Collect anchor-led role descriptor paragraphs from the NISO page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._paragraph_parts: list[str] | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._role: str | None = None
        self.entries: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._paragraph_parts = []
            self._role = None
        elif tag == "a" and self._paragraph_parts is not None:
            self._anchor_href = dict(attrs).get("href")
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._paragraph_parts is not None:
            self._paragraph_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._paragraph_parts is not None:
            role = _clean("".join(self._anchor_text))
            # Role links point to individual role resources, unlike navigation links.
            if self._anchor_href and "/contributor-roles/" in self._anchor_href and role:
                self._role = role
            self._anchor_href = None
            self._anchor_text = []
        elif tag == "p":
            if self._paragraph_parts is not None and self._role is not None:
                paragraph = _clean("".join(self._paragraph_parts))
                description = _description_after_role(paragraph, self._role)
                if description:
                    self.entries.append((self._role, description))
            self._paragraph_parts = None
            self._role = None


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _description_after_role(paragraph: str, role: str) -> str:
    remainder = paragraph[len(role):].strip()
    return re.sub(r"^[\s–—-]+", "", remainder).strip()


def _parse_taxonomy(html: str) -> Taxonomy:
    parser = _RoleDescriptorParser()
    parser.feed(html)
    parser.close()
    descriptions = dict(parser.entries)
    taxonomy = Taxonomy(tuple(descriptions), descriptions)
    taxonomy.validate()
    return taxonomy


def fetch_official_taxonomy(timeout_seconds: float = 10.0) -> Taxonomy:
    """Fetch all roles and descriptors from the official NISO CRediT page.

    The network response is parsed and validated rather than being replaced with
    a bundled role list. ``TaxonomyFetchError`` gives callers one stable error
    type for network, encoding, and invalid-response failures.
    """
    request = Request(OFFICIAL_TAXONOMY_URL, headers={"User-Agent": "credit-normalizer/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise TaxonomyFetchError(f"NISO returned HTTP {response.status}")
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset)
        taxonomy = _parse_taxonomy(html)
    except (OSError, URLError, UnicodeDecodeError, ValueError, TypeError) as error:
        raise TaxonomyFetchError(f"Unable to retrieve valid NISO CRediT taxonomy: {error}") from error
    return taxonomy
