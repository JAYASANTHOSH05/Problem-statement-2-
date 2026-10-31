"""Detect and normalize CRediT contribution statements conservatively."""

from __future__ import annotations

import re

from author_parser import match_author
from credit_normalizer import map_contribution_phrase, normalize_role
from models import Author, Contribution, Diagnostic, DocumentContent, TextBlock


HEADING_ALIASES = frozenset({"author contributions", "author contributions statement", "contributors", "credit taxonomy"})
_DEFAULT_CREDIT_ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)
_END_HEADINGS = frozenset({"acknowledgements", "funding", "conflict of interest", "data availability", "references"})
_INLINE_PATTERN = re.compile(r"^\s*(?:author\s+)?contributions?\s*:\s*(.+)$", re.IGNORECASE)
_HEADER_PATTERN = re.compile(r"(?:author\s+contributions?|contributors?)\s*:\s*(.+)$", re.IGNORECASE)
_STRUCTURED_LABEL = re.compile(
    r"(?P<label>(?:(?:Dr|Prof)\.\s+)?(?:[A-Z](?:\.[A-Z])+\.?|[A-Z]{2,4}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\d*[*†�]?)\s*(?::|[-–—�])"
)
_PARENTHESIZED_ENTRY = re.compile(
    r"(?P<label>(?:(?:Dr|Prof)\.\s+)?(?:[A-Z](?:\.[A-Z])+\.?|[A-Z]{2,4}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\d*[*†�]?)\s*\((?P<payload>[^)]*)\)"
)
_DEGREE_PATTERN = re.compile(r"\s*[-–—�]\s*(lead|equal|supporting)\s*$", re.IGNORECASE)
_NARRATIVE_ACTION = re.compile(
    r"\b(conceived|designed|analy[sz]ed|collected|wrote|performed|supervised|reviewed|edited|acquired|administered|developed|checked|created|provided|made)\b",
    re.IGNORECASE,
)


def parse_contributions(document: DocumentContent, authors: list[Author], official_roles: tuple[str, ...]) -> tuple[list[Contribution], list[Diagnostic]]:
    """Parse supported formats without inferring unknown author identities."""
    roles = official_roles or _DEFAULT_CREDIT_ROLES
    contributions: list[Contribution] = []
    diagnostics: list[Diagnostic] = []
    blocks, body_found = _body_contribution_blocks(document.body)
    for block in blocks:
        _parse_block(block, authors, roles, contributions, diagnostics)
    if body_found:
        for row in document.tables:
            _parse_table_row(row, authors, roles, contributions, diagnostics)

    candidate_found = body_found
    for block in [*document.headers, *document.footers]:
        match = _HEADER_PATTERN.search(block.text)
        if match:
            candidate_found = True
            _parse_block(TextBlock(match.group(1), block.location, block.kind, block.cells, block.text), authors, roles, contributions, diagnostics)

    if not candidate_found:
        diagnostics.append(Diagnostic("missing_contribution_section", "No contribution statement was found."))
    elif not contributions:
        diagnostics.append(Diagnostic("no_recognized_contributions", "A contribution statement was found but no author-role association was recognized."))

    credited = {item.author_token for item in contributions if item.role is not None}
    for author in authors:
        if author.display_name not in credited:
            diagnostics.append(Diagnostic("missing_author_attribution", f"No recognized contribution was associated with roster author {author.display_name!r}."))
    return contributions, diagnostics


def _body_contribution_blocks(body: list[TextBlock]) -> tuple[list[TextBlock], bool]:
    blocks: list[TextBlock] = []
    found = False
    index = 0
    while index < len(body):
        block = body[index]
        inline = _INLINE_PATTERN.match(block.text.strip())
        if inline:
            blocks.append(TextBlock(inline.group(1), block.location, block.kind, block.cells, block.text))
            found = True
        elif _heading_key(block.text) in HEADING_ALIASES:
            found = True
            index += 1
            while index < len(body) and _heading_key(body[index].text) not in _END_HEADINGS:
                blocks.append(body[index])
                index += 1
            continue
        index += 1
    return blocks, found


def _heading_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("–", "-").strip().casefold())


def _parse_table_row(block: TextBlock, authors: list[Author], roles: tuple[str, ...], contributions: list[Contribution], diagnostics: list[Diagnostic]) -> None:
    if len(block.cells) < 2:
        return
    author = match_author(block.cells[0], authors)
    if author is not None:
        _add_roles(author, block.cells[1], block, roles, contributions, diagnostics)
    elif _contains_known_role(block.cells[1], roles):
        diagnostics.append(Diagnostic("ambiguous_author_attribution", f"Could not unambiguously match contributor token {block.cells[0]!r} to the author roster.", location=block.location))


def _parse_block(block: TextBlock, authors: list[Author], roles: tuple[str, ...], contributions: list[Contribution], diagnostics: list[Diagnostic]) -> None:
    if re.match(r"^\s*all authors\s+contributed\b", block.text, re.IGNORECASE):
        for author in _resolve_author_tokens("all authors", authors, block, diagnostics):
            _add_role_mentions(author, block.text, block, roles, contributions)
        return
    parenthesized_entries = list(_PARENTHESIZED_ENTRY.finditer(block.text))
    if parenthesized_entries:
        for entry in parenthesized_entries:
            for author in _resolve_author_tokens(entry.group("label"), authors, block, diagnostics):
                _add_roles(author, entry.group("payload"), block, roles, contributions, diagnostics)
        return
    labels = list(_STRUCTURED_LABEL.finditer(block.text))
    if labels:
        for current, following in zip(labels, [*labels[1:], None]):
            end = following.start() if following else len(block.text)
            payload = block.text[current.end():end].strip(" .;")
            for author in _resolve_author_tokens(current.group("label"), authors, block, diagnostics):
                if not _add_roles(author, payload, block, roles, contributions, diagnostics):
                    _add_narrative_roles(author, payload, block, roles, contributions)
        return
    _parse_narrative(block, authors, roles, contributions, diagnostics)


def _parse_narrative(block: TextBlock, authors: list[Author], roles: tuple[str, ...], contributions: list[Contribution], diagnostics: list[Diagnostic]) -> None:
    # Do not split after the final dot of dotted initials such as ``S.K.``.
    for clause in re.split(r";\s+|(?<![A-Z])\.\s+", block.text):
        action = _NARRATIVE_ACTION.search(clause)
        if not action:
            continue
        prefix = clause[:action.start()].strip(" :,-")
        for author in _resolve_author_tokens(prefix, authors, block, diagnostics):
            if not _add_narrative_roles(author, clause[action.start():], block, roles, contributions):
                _append_unique(contributions, Contribution(author.display_name, None, _source_text(block), block.location))
                diagnostics.append(Diagnostic("unmapped_contribution", f"Could not map contribution activity for {author.display_name!r}.", location=block.location))


def _resolve_author_tokens(token: str, authors: list[Author], block: TextBlock, diagnostics: list[Diagnostic]) -> list[Author]:
    token = token.strip()
    if token.casefold() == "all authors":
        if authors:
            return authors
        diagnostics.append(Diagnostic("ambiguous_author_attribution", "'All authors' has no extracted roster.", location=block.location))
        return []
    names = [part.strip() for part in re.split(r"\s*(?:,|&|\band\b)\s*", token, flags=re.IGNORECASE) if part.strip()]
    matched: list[Author] = []
    for name in names:
        author = match_author(name, authors)
        if author is None:
            diagnostics.append(Diagnostic("ambiguous_author_attribution", f"Could not unambiguously match contributor token {name!r} to the author roster.", location=block.location))
        elif author not in matched:
            matched.append(author)
    return matched


def _add_roles(author: Author, payload: str, block: TextBlock, roles: tuple[str, ...], contributions: list[Contribution], diagnostics: list[Diagnostic]) -> bool:
    added = False
    for item in re.split(r"\s*(?:,|;)\s*", payload.strip("() ")):
        if not item:
            continue
        degree_match = _DEGREE_PATTERN.search(item)
        degree = degree_match.group(1).casefold() if degree_match else None
        role_text = item[:degree_match.start()] if degree_match else item
        role = normalize_role(role_text, roles)
        if role:
            _append_unique(contributions, Contribution(author.display_name, role, _source_text(block), block.location, degree))
        else:
            mapped = map_contribution_phrase(role_text, roles)
            if mapped:
                for mapped_role in mapped:
                    _append_unique(contributions, Contribution(author.display_name, mapped_role, _source_text(block), block.location, degree))
            else:
                _append_unique(contributions, Contribution(author.display_name, None, _source_text(block), block.location, degree))
                diagnostics.append(Diagnostic("unmapped_contribution", f"Could not map structured role {role_text!r} for {author.display_name!r}.", location=block.location))
        added = True
    return added


def _add_narrative_roles(author: Author, payload: str, block: TextBlock, roles: tuple[str, ...], contributions: list[Contribution]) -> bool:
    mapped = map_contribution_phrase(payload, roles)
    for role in mapped:
        _append_unique(contributions, Contribution(author.display_name, role, _source_text(block), block.location))
    return bool(mapped)


def _add_role_mentions(author: Author, payload: str, block: TextBlock, roles: tuple[str, ...], contributions: list[Contribution]) -> bool:
    """Extract explicit role names from grouped wording such as ``All authors``."""
    added = False
    for role in roles:
        if role == "Writing – original draft":
            present = re.search(r"\bwriting(?:\s+of)?\s+(?:the\s+)?original draft\b", payload, re.IGNORECASE)
        elif role == "Writing – review & editing":
            present = re.search(r"\bwriting\s*[-–—�]?\s*review\s*(?:&|and)\s*editing\b", payload, re.IGNORECASE)
        else:
            present = re.search(rf"\b{re.escape(role)}\b", payload, re.IGNORECASE)
        if present:
            _append_unique(contributions, Contribution(author.display_name, role, _source_text(block), block.location))
            added = True
    return added


def _append_unique(contributions: list[Contribution], contribution: Contribution) -> None:
    if contribution not in contributions:
        contributions.append(contribution)


def _source_text(block: TextBlock) -> str:
    return block.source_text or block.text


def _contains_known_role(payload: str, roles: tuple[str, ...]) -> bool:
    for item in re.split(r"\s*(?:,|;)\s*", payload.strip("() ")):
        degree_match = _DEGREE_PATTERN.search(item)
        role_text = item[:degree_match.start()] if degree_match else item
        if normalize_role(role_text, roles):
            return True
    return False
