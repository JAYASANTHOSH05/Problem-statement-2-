from pathlib import Path

from author_parser import author_variants, extract_authors
from contribution_parser import parse_contributions
from docx_reader import read_docx
from models import Author, DocumentContent, TextBlock


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)


def _parse(filename: str):
    document, diagnostics = read_docx(ROOT / "manuscripts" / filename)
    assert diagnostics == [] and document is not None
    contributions, diagnostics = parse_contributions(document, extract_authors(document.body), ROLES)
    return document, contributions, diagnostics


def test_body_table_and_inline_contributions_preserve_original_source_and_location() -> None:
    for filename in ("merged_01.docx", "merged_08.docx", "merged_09.docx"):
        document, contributions, _ = _parse(filename)
        source_by_location = {block.location: block.text for block in [*document.body, *document.tables]}
        assert contributions
        assert all(item.source_text == source_by_location[item.location] for item in contributions)

    _, contributions, _ = _parse("merged_09.docx")
    assert {(item.author_token, item.role, item.location) for item in contributions} == {
        ("Sara Khan", "Conceptualization", "body:paragraph:37"),
        ("Leo Moreau", "Writing – review & editing", "body:paragraph:37"),
    }


def test_degrees_remain_attached_to_the_correct_author_and_role() -> None:
    _, contributions, diagnostics = _parse("merged_16.docx")
    assert {(item.author_token, item.role, item.degree) for item in contributions} == {
        ("Anil Bose", "Conceptualization", "lead"),
        ("Anil Bose", "Methodology", "equal"),
        ("Jane Doe", "Writing – original draft", "supporting"),
    }
    assert diagnostics == []


def test_matching_header_and_footer_contributions_keep_full_original_text() -> None:
    jane = Author("Jane Doe", "janedoe", author_variants("Jane Doe"))
    document = DocumentContent(
        Path("synthetic.docx"),
        headers=[TextBlock("Contributors: J.D.: Software", "header1:paragraph:0")],
        footers=[TextBlock("Author Contributions: Jane Doe: Validation", "footer1:paragraph:0")],
    )
    contributions, diagnostics = parse_contributions(document, [jane], ROLES)
    assert {(item.role, item.source_text, item.location) for item in contributions} == {
        ("Software", "Contributors: J.D.: Software", "header1:paragraph:0"),
        ("Validation", "Author Contributions: Jane Doe: Validation", "footer1:paragraph:0"),
    }
    assert diagnostics == []


def test_references_do_not_create_contributions_and_unmatched_diagnostics_are_located() -> None:
    document, contributions, diagnostics = _parse("merged_13.docx")
    reference = next(block for block in document.body if "Author Contributions: a practical guide" in block.text)
    assert contributions == []
    assert all(item.location != reference.location for item in diagnostics)
    unmatched = [item for item in diagnostics if item.code == "ambiguous_author_attribution"]
    assert {(item.location, "J.D." in item.message, "A.B." in item.message) for item in unmatched} == {
        ("header1:paragraph:0", True, False), ("footer1:paragraph:0", False, True)
    }


def test_unknown_structured_role_has_exact_source_and_diagnostic() -> None:
    jane = Author("Jane Doe", "janedoe", author_variants("Jane Doe"))
    text = "J.D.: Peer review."
    document = DocumentContent(Path("synthetic.docx"), body=[
        TextBlock("Author Contributions", "body:paragraph:0"), TextBlock(text, "body:paragraph:1"),
    ])
    contributions, diagnostics = parse_contributions(document, [jane], ROLES)
    assert [(item.author_token, item.role, item.source_text, item.location) for item in contributions] == [
        ("Jane Doe", None, text, "body:paragraph:1")
    ]
    assert [(item.code, item.location) for item in diagnostics if item.code == "unmapped_contribution"] == [
        ("unmapped_contribution", "body:paragraph:1")
    ]
