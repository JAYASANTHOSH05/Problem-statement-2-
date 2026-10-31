import csv
from collections import Counter
from pathlib import Path

from main import process_directory, write_reports


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden_output.csv"
ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_all_manuscripts_match_golden_output(tmp_path: Path) -> None:
    results, taxonomy_error = process_directory(ROOT / "manuscripts", roles=ROLES)
    output_path, _ = write_reports(results, tmp_path, taxonomy_error)
    actual = _read_rows(output_path)
    expected = _read_rows(FIXTURE)

    assert len(results) == 20
    invalid = next(result for result in results if result.source.name == "merged_12.docx")
    assert any(item.code == "invalid_document" for item in invalid.diagnostics)
    assert len(actual) == len(set(tuple(row.items()) for row in actual)), "duplicate output rows"

    missing = Counter(tuple(row.items()) for row in expected) - Counter(tuple(row.items()) for row in actual)
    extra = Counter(tuple(row.items()) for row in actual) - Counter(tuple(row.items()) for row in expected)
    assert not missing, f"missing rows: {list(missing.elements())}"
    assert not extra, f"extra rows: {list(extra.elements())}"
    assert actual == expected
