from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from docx_reader import read_docx
from main import process_directory, write_reports
from models import DocumentResult
from taxonomy import TaxonomyFetchError, fetch_official_taxonomy


def _docx(path: Path, document_xml: str | None) -> None:
    with ZipFile(path, "w") as archive:
        if document_xml is not None:
            archive.writestr("word/document.xml", document_xml)


def test_empty_directory_returns_no_results(tmp_path: Path) -> None:
    results, error = process_directory(tmp_path, roles=("Software",))
    assert results == []
    assert error is None


@pytest.mark.parametrize(
    ("document_xml", "message"),
    [
        (None, "missing"),
        ("<w:document", "invalid WordprocessingML"),
    ],
)
def test_missing_or_malformed_document_xml_is_invalid(tmp_path: Path, document_xml: str | None, message: str) -> None:
    path = tmp_path / "bad.docx"
    _docx(path, document_xml)
    content, diagnostics = read_docx(path)
    assert content is None
    assert diagnostics[0].code == "invalid_document"
    assert message in diagnostics[0].message


def test_multiple_invalid_documents_do_not_stop_batch(tmp_path: Path) -> None:
    (tmp_path / "broken.docx").write_text("not a zip", encoding="utf-8")
    _docx(tmp_path / "missing.docx", None)
    _docx(tmp_path / "valid.DOCX", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
    results, error = process_directory(tmp_path, roles=("Software",))
    assert error is None
    assert [result.source.name for result in results] == ["broken.docx", "missing.docx", "valid.DOCX"]
    assert sum(any(item.code == "invalid_document" for item in result.diagnostics) for result in results) == 2
    assert not any(
        item.code == "invalid_document"
        for item in next(result for result in results if result.source.name == "valid.DOCX").diagnostics
    )


def test_taxonomy_http_failure_is_reported() -> None:
    class Response:
        status = 503

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with patch("taxonomy.urlopen", return_value=Response()):
        with pytest.raises(TaxonomyFetchError, match="HTTP 503"):
            fetch_official_taxonomy()


def test_csv_write_failure_propagates(tmp_path: Path) -> None:
    with patch("pathlib.Path.open", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            write_reports([DocumentResult(source=Path("one.docx"))], tmp_path)
