from pathlib import Path

import pytest

from author_parser import author_variants, extract_authors, match_author, normalize_token
from docx_reader import read_docx
from models import Author, TextBlock


ROOT = Path(__file__).resolve().parents[1]


def roster(filename: str) -> list[Author]:
    content, diagnostics = read_docx(ROOT / "manuscripts" / filename)
    assert diagnostics == []
    assert content is not None
    return extract_authors(content.body)


def test_extracts_full_name_roster_from_actual_manuscript() -> None:
    authors = roster("merged_20.docx")
    assert [author.display_name for author in authors] == ["Hana Sato", "Ivan Petrov", "Julia Costa"]


@pytest.mark.parametrize(
    ("token", "expected"),
    [("J.D.", "Jane Doe"), ("JD", "Jane Doe"), ("Jane Doe", "Jane Doe"), ("Anil Bose2*", "Anil Bose")],
)
def test_matches_full_names_dotted_and_undotted_initials(token: str, expected: str) -> None:
    authors = roster("merged_01.docx")
    match = match_author(token, authors)
    assert match is not None
    assert match.display_name == expected


def test_grouped_author_document_has_matchable_undotted_initials() -> None:
    authors = roster("merged_07.docx")
    assert match_author("AB", authors).display_name == "Anil Bose"
    assert match_author("CD", authors).display_name == "Carla Diaz"
    assert match_author("EF", authors).display_name == "Erin Fox"


def test_header_footer_identifiers_that_are_not_in_roster_remain_unmatched() -> None:
    authors = roster("merged_13.docx")
    assert [author.display_name for author in authors] == ["Lena Petrova", "Hassan Novak", "Vikram Ali"]
    assert match_author("J.D.", authors) is None
    assert match_author("A.B.", authors) is None


def test_honorifics_and_affiliation_markers_do_not_change_identity() -> None:
    author = Author(
        display_name="Jane Doe",
        normalized_name=normalize_token("Jane Doe"),
        variants=author_variants("Jane Doe"),
    )
    assert normalize_token("Dr. Jane Doe1*") == "janedoe"
    assert match_author("Prof. Jane Doe2†", [author]) is author


def test_similar_initials_are_ambiguous_and_not_guessed() -> None:
    john = Author("John Doe", "johndoe", author_variants("John Doe"))
    jane = Author("Jane Davis", "janedavis", author_variants("Jane Davis"))
    assert match_author("J.D.", [john, jane]) is None


def test_missing_author_token_returns_none() -> None:
    authors = roster("merged_02.docx")
    assert match_author("Unknown Person", authors) is None


def test_empty_author_token_never_matches_a_single_author() -> None:
    author = Author("Jane Doe", "janedoe", author_variants("Jane Doe"))
    assert match_author("", [author]) is None
    assert match_author("***", [author]) is None


def test_no_plausible_author_line_returns_empty_roster() -> None:
    body = [
        TextBlock("A study title", "body:paragraph:0"),
        TextBlock("Corresponding author: Jane Doe (doe@example.org)", "body:paragraph:1"),
        TextBlock("Abstract", "body:paragraph:2"),
    ]
    assert extract_authors(body) == []
