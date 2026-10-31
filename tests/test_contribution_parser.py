from pathlib import Path

from author_parser import author_variants, extract_authors, normalize_token
from contribution_parser import parse_contributions
from docx_reader import read_docx
from models import Author, Contribution, DocumentContent, TextBlock


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)


def parse(filename: str):
    content, diagnostics = read_docx(ROOT / "manuscripts" / filename)
    assert diagnostics == [] and content is not None
    return parse_contributions(content, extract_authors(content.body), ROLES)


def pairs(contributions):
    return {(item.author_token, item.role) for item in contributions}


def test_structured_text_extracts_multiple_roles_and_location() -> None:
    contributions, diagnostics = parse("merged_01.docx")
    assert pairs(contributions) == {
        ("Jane Doe", "Conceptualization"), ("Jane Doe", "Writing – original draft"),
        ("Anil Bose", "Methodology"), ("Anil Bose", "Software"),
    }
    assert all(item.location.startswith("body:paragraph:") for item in contributions)
    assert not diagnostics


def test_author_per_paragraph_and_table_formats() -> None:
    contributions, diagnostics = parse("merged_04.docx")
    assert ("Lena Berg", "Formal analysis") in pairs(contributions)
    assert ("Omar Nasser", "Resources") in pairs(contributions)
    assert not diagnostics

    contributions, diagnostics = parse("merged_08.docx")
    assert pairs(contributions) == {
        ("Kai Lund", "Software"), ("Kai Lund", "Validation"), ("Mira Nair", "Visualization"),
        ("Paul Quinn", "Methodology"), ("Paul Quinn", "Investigation"),
    }
    assert all(item.location.startswith("body:table:1:") for item in contributions)
    assert not diagnostics


def test_narrative_grouped_and_all_author_formats() -> None:
    contributions, diagnostics = parse("merged_07.docx")
    assert ("Anil Bose", "Writing – review & editing") in pairs(contributions)
    assert ("Carla Diaz", "Writing – review & editing") in pairs(contributions)
    assert ("Erin Fox", "Supervision") in pairs(contributions)
    assert not diagnostics

    contributions, diagnostics = parse("merged_17.docx")
    assert pairs(contributions) == {
        (author, role) for author in ("Jane Doe", "Anil Bose")
        for role in ("Conceptualization", "Investigation", "Writing – original draft")
    }
    assert not diagnostics


def test_inline_and_header_footer_formats() -> None:
    contributions, diagnostics = parse("merged_09.docx")
    assert ("Sara Khan", "Conceptualization") in pairs(contributions)
    assert ("Leo Moreau", "Writing – review & editing") in pairs(contributions)
    assert not diagnostics

    contributions, diagnostics = parse("merged_13.docx")
    assert contributions == []
    assert sum(item.code == "ambiguous_author_attribution" for item in diagnostics) == 2
    assert any(item.code == "no_recognized_contributions" for item in diagnostics)


def test_missing_unmapped_and_ambiguous_attribution_are_diagnostic() -> None:
    contributions, diagnostics = parse("merged_11.docx")
    assert contributions == []
    assert any(item.code == "missing_contribution_section" for item in diagnostics)

    contributions, diagnostics = parse("merged_18.docx")
    assert ("Erin Fox", "Formal analysis") in pairs(contributions)
    assert ("Gus Hall", None) in pairs(contributions)
    assert any(item.code == "unmapped_contribution" for item in diagnostics)

    authors = [
        Author("John Doe", "johndoe", author_variants("John Doe")),
        Author("Jane Davis", "janedavis", author_variants("Jane Davis")),
    ]
    document = DocumentContent(Path("synthetic.docx"), body=[
        TextBlock("Author Contributions", "body:paragraph:0"), TextBlock("J.D.: Software.", "body:paragraph:1"),
    ])
    contributions, diagnostics = parse_contributions(document, authors, ROLES)
    assert contributions == []
    assert any(item.code == "ambiguous_author_attribution" for item in diagnostics)


def test_unknown_author_in_role_table_is_flagged_without_guessing() -> None:
    authors = [Author("Jane Doe", "janedoe", author_variants("Jane Doe"))]
    document = DocumentContent(Path("synthetic.docx"), body=[TextBlock("Author Contributions", "body:paragraph:0")])
    document.tables = [TextBlock("X.Y.\tSoftware", "body:table:0:row:0", "table_row", ("X.Y.", "Software"))]
    contributions, diagnostics = parse_contributions(document, authors, ROLES)
    assert contributions == []
    assert any(item.code == "ambiguous_author_attribution" for item in diagnostics)


def test_parenthesized_roles_and_review_and_editing_variant() -> None:
    contributions, diagnostics = parse("merged_16.docx")
    assert pairs(contributions) == {
        ("Anil Bose", "Conceptualization"), ("Anil Bose", "Methodology"),
        ("Jane Doe", "Writing – original draft"),
    }
    assert {item.degree for item in contributions} == {"lead", "equal", "supporting"}
    assert not diagnostics

    contributions, _ = parse("merged_10.docx")
    assert ("Rita Tran", "Writing – review & editing") in pairs(contributions)


def test_structured_unknown_role_is_preserved_and_diagnostic() -> None:
    authors = [Author("Jane Doe", "janedoe", author_variants("Jane Doe"))]
    document = DocumentContent(Path("synthetic.docx"), body=[
        TextBlock("Author Contributions", "body:paragraph:0"),
        TextBlock("J.D.: Peer review.", "body:paragraph:1"),
    ])
    contributions, diagnostics = parse_contributions(document, authors, ROLES)
    assert contributions == [Contribution("Jane Doe", None, "J.D.: Peer review.", "body:paragraph:1")]
    assert any(item.code == "unmapped_contribution" and item.location == "body:paragraph:1" for item in diagnostics)
