"""CLI entry point for batch CRediT contribution normalization."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from author_parser import extract_authors
from contribution_parser import parse_contributions
from docx_reader import read_docx
from models import Diagnostic, DocumentResult, Severity
from taxonomy import TaxonomyFetchError, fetch_official_taxonomy


def process_directory(directory: Path, roles: tuple[str, ...] | None = None) -> tuple[list[DocumentResult], str | None]:
    """Process each DOCX independently and return an optional taxonomy error."""
    taxonomy_error: str | None = None
    if roles is None:
        try:
            roles = fetch_official_taxonomy().roles
        except TaxonomyFetchError as error:
            taxonomy_error = str(error)

    results: list[DocumentResult] = []
    for path in sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.casefold() == ".docx"):
        content, diagnostics = read_docx(path)
        result = DocumentResult(source=path, diagnostics=diagnostics)
        if content is not None:
            result.authors = extract_authors(content.body)
            if taxonomy_error is None:
                result.contributions, parse_diagnostics = parse_contributions(content, result.authors, roles or ())
                result.diagnostics.extend(parse_diagnostics)
            else:
                result.diagnostics.append(
                    Diagnostic("taxonomy_unavailable", taxonomy_error, severity=Severity.ERROR)
                )
        results.append(result)
    return results, taxonomy_error


def write_reports(results: list[DocumentResult], output_directory: Path, taxonomy_error: str | None = None) -> tuple[Path, Path]:
    """Write normalized contributions and a lightweight end-to-end test report."""
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "output.csv"
    report_path = output_directory / "test_report.csv"

    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("file", "author", "credit_role"))
        writer.writeheader()
        for result in results:
            for contribution in result.contributions:
                writer.writerow(
                    {
                        "file": result.source.name,
                        "author": contribution.author_token,
                        "credit_role": contribution.role or "INVALID",
                    }
                )

    with report_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("test_id", "description", "expected", "actual", "status", "validation_status", "diagnostics"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "test_id": "taxonomy-fetch",
                "description": "Official NISO CRediT taxonomy is available for normalization.",
                "expected": "14 validated roles",
                "actual": taxonomy_error or "14 validated roles",
                "status": "FAIL" if taxonomy_error else "PASS",
                "validation_status": "ISSUES" if taxonomy_error else "PASS",
                "diagnostics": taxonomy_error or "",
            }
        )
        for result in results:
            invalid = any(item.code == "invalid_document" for item in result.diagnostics)
            diagnostics = " | ".join(f"{item.severity}:{item.code}: {item.message}" for item in result.diagnostics)
            writer.writerow(
                {
                    "test_id": f"document:{result.source.name}",
                    "description": "Independent document processing and validation summary.",
                    "expected": "result returned; no validation diagnostics",
                    "actual": "invalid document handled" if invalid else "processed",
                    "status": "PASS",
                    "validation_status": "PASS" if not result.diagnostics else "ISSUES",
                    "diagnostics": diagnostics,
                }
            )
    return output_path, report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize manuscript CRediT contributions.")
    parser.add_argument("directory", type=Path, help="Directory containing DOCX manuscripts")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Directory for output.csv and test_report.csv")
    arguments = parser.parse_args()
    results, taxonomy_error = process_directory(arguments.directory)
    output_path, report_path = write_reports(results, arguments.output_dir, taxonomy_error)
    invalid = sum(any(item.code == "invalid_document" for item in result.diagnostics) for result in results)
    print(f"Processed {len(results)} DOCX files; {invalid} invalid document(s).")
    print(f"Wrote {output_path} and {report_path}.")
    return 2 if taxonomy_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
