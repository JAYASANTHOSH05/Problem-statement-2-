from pathlib import Path

import pytest

from credit_normalizer import map_contribution_phrase, normalize_role
from docx_reader import read_docx
from taxonomy import Taxonomy


ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)
TAXONOMY = Taxonomy(ROLES, {role: "description" for role in ROLES})
ROOT = Path(__file__).resolve().parents[1]


def test_explicit_labels_normalize_against_supplied_taxonomy() -> None:
    assert normalize_role("FORMAL ANALYSIS", TAXONOMY) == "Formal analysis"
    assert normalize_role("Writing - original draft", TAXONOMY) == "Writing – original draft"
    assert normalize_role("Writing – review and editing", TAXONOMY) == "Writing – review & editing"


@pytest.mark.parametrize("role", ROLES)
def test_all_official_labels_normalize_with_case_whitespace_and_punctuation(role: str) -> None:
    variant = f"  {role.upper().replace('–', '-').replace('&', 'and')}  "
    assert normalize_role(variant, TAXONOMY) == role


def test_maps_multiple_high_confidence_narrative_roles() -> None:
    assert map_contribution_phrase("designed the study and analyzed the data", TAXONOMY) == (
        "Conceptualization", "Formal analysis"
    )
    assert map_contribution_phrase("Created the figures and edited the final text", TAXONOMY) == (
        "Visualization", "Writing – review & editing"
    )


def test_actual_manuscript_phrases_map_or_remain_unmapped() -> None:
    content, diagnostics = read_docx(ROOT / "manuscripts" / "merged_18.docx")
    assert diagnostics == [] and content is not None
    statement = next(block.text for block in content.body if "performed the statistical analysis" in block.text)
    assert map_contribution_phrase(statement, TAXONOMY) == ("Formal analysis",)
    assert map_contribution_phrase("made the tea", TAXONOMY) == ()


def test_role_not_present_in_supplied_taxonomy_is_not_guessed() -> None:
    limited = Taxonomy(("Software",), {"Software": "description"})
    assert map_contribution_phrase("conceived the study", limited) == ()


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("conceived the project", "Conceptualization"),
        ("analyzed the data", "Formal analysis"),
        ("collected the data", "Investigation"),
        ("acquired funding", "Funding acquisition"),
        ("administered the project", "Project administration"),
        ("provided resources", "Resources"),
        ("developed the analysis code", "Software"),
        ("checked results", "Validation"),
        ("supervised the work", "Supervision"),
        ("created the figures", "Visualization"),
        ("wrote the original draft", "Writing – original draft"),
        ("reviewed and edited the manuscript", "Writing – review & editing"),
    ],
)
def test_each_phrase_mapping_rule(phrase: str, expected: str) -> None:
    assert map_contribution_phrase(phrase, TAXONOMY) == (expected,)


@pytest.mark.parametrize("phrase", ["made the tea", "peer review", "helped with the project", ""])
def test_unknown_or_unrelated_phrases_are_not_mapped(phrase: str) -> None:
    assert map_contribution_phrase(phrase, TAXONOMY) == ()
