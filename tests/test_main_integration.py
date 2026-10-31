import csv
import sys
from pathlib import Path
from unittest.mock import patch

from main import main, process_directory, write_reports
from taxonomy import TaxonomyFetchError


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
)


def test_batch_writes_actual_contributions_and_invalid_mapping(tmp_path: Path) -> None:
    results, error = process_directory(ROOT / "manuscripts", roles=ROLES)
    assert error is None
    output_path, report_path = write_reports(results, tmp_path)

    with output_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {"file", "author", "credit_role"} == set(rows[0])
    assert {"file": "merged_01.docx", "author": "Jane Doe", "credit_role": "Conceptualization"} in rows
    assert {"file": "merged_18.docx", "author": "Gus Hall", "credit_role": "INVALID"} in rows
    assert not any(row["file"] == "merged_12.docx" for row in rows)

    with report_path.open(encoding="utf-8", newline="") as stream:
        report = list(csv.DictReader(stream))
    invalid_row = next(row for row in report if row["test_id"] == "document:merged_12.docx")
    assert invalid_row["actual"] == "invalid document handled"
    assert invalid_row["status"] == "PASS"
    assert invalid_row["validation_status"] == "ISSUES"
    assert "invalid_document" in invalid_row["diagnostics"]

    missing_row = next(row for row in report if row["test_id"] == "document:merged_11.docx")
    assert missing_row["status"] == "PASS"
    assert missing_row["validation_status"] == "ISSUES"
    assert "missing_contribution_section" in missing_row["diagnostics"]


def test_taxonomy_failure_does_not_stop_document_reading(tmp_path: Path) -> None:
    with patch("main.fetch_official_taxonomy", side_effect=TaxonomyFetchError("network unavailable")):
        results, error = process_directory(ROOT / "manuscripts", roles=None)
    assert error == "network unavailable"
    assert len(results) == 20
    assert any(result.source.name == "merged_12.docx" for result in results)
    assert any(item.code == "taxonomy_unavailable" for item in results[0].diagnostics)
    output_path, report_path = write_reports(results[:1], tmp_path, error)
    assert output_path.exists()
    with report_path.open(encoding="utf-8", newline="") as stream:
        report = list(csv.DictReader(stream))
    assert report[0]["status"] == "FAIL"
    assert report[0]["validation_status"] == "ISSUES"


def test_cli_returns_nonzero_when_taxonomy_fetch_fails(tmp_path: Path) -> None:
    with patch("main.fetch_official_taxonomy", side_effect=TaxonomyFetchError("network unavailable")):
        with patch.object(sys, "argv", ["main.py", str(ROOT / "manuscripts"), "--output-dir", str(tmp_path)]):
            assert main() == 2
    with (tmp_path / "test_report.csv").open(encoding="utf-8", newline="") as stream:
        report = list(csv.DictReader(stream))
    assert report[0]["status"] == "FAIL"
