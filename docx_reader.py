"""Low-level, read-only DOCX extraction using only the Python standard library."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from models import Diagnostic, DocumentContent, Severity, TextBlock


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NAMESPACE}}}"


def _paragraph_text(paragraph: ET.Element) -> str:
    """Extract visible paragraph text, preserving tabs and line breaks."""
    pieces: list[str] = []
    for element in paragraph.iter():
        if element.tag == W + "t":
            pieces.append(element.text or "")
        elif element.tag == W + "tab":
            pieces.append("\t")
        elif element.tag in {W + "br", W + "cr"}:
            pieces.append("\n")
    return "".join(pieces)


def _table_rows(table: ET.Element, location_prefix: str) -> list[TextBlock]:
    """Represent each table row as one common intermediate text block."""
    rows: list[TextBlock] = []
    for row_index, row in enumerate(table.findall("./w:tr", {"w": WORD_NAMESPACE})):
        cells: list[str] = []
        for cell in row.findall("./w:tc", {"w": WORD_NAMESPACE}):
            paragraphs = cell.findall("./w:p", {"w": WORD_NAMESPACE})
            cells.append("\n".join(_paragraph_text(paragraph) for paragraph in paragraphs))
        rows.append(
            TextBlock(
                text="\t".join(cells),
                cells=tuple(cells),
                kind="table_row",
                location=f"{location_prefix}:row:{row_index}",
            )
        )
    return rows


def _extract_part(root: ET.Element, location_prefix: str) -> tuple[list[TextBlock], list[TextBlock]]:
    """Extract direct paragraphs and table rows from a document-like XML part."""
    namespace = {"w": WORD_NAMESPACE}
    container = root.find("w:body", namespace) if root.tag == W + "document" else root
    if container is None:
        return [], []

    paragraphs: list[TextBlock] = []
    table_rows: list[TextBlock] = []
    paragraph_index = 0
    table_index = 0
    for child in container:
        if child.tag == W + "p":
            paragraphs.append(
                TextBlock(
                    text=_paragraph_text(child),
                    location=f"{location_prefix}:paragraph:{paragraph_index}",
                )
            )
            paragraph_index += 1
        elif child.tag == W + "tbl":
            table_rows.extend(_table_rows(child, f"{location_prefix}:table:{table_index}"))
            table_index += 1
    return paragraphs, table_rows


def read_docx(path: Path) -> tuple[DocumentContent | None, list[Diagnostic]]:
    """Read a DOCX while returning diagnostics instead of throwing batch-stopping errors.

    Main-document table rows are placed in ``DocumentContent.tables``. Header and
    footer paragraphs and table rows are placed in their respective collections.
    Empty but valid documents return an empty ``DocumentContent``.
    """
    try:
        with ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                raise BadZipFile("word/document.xml is missing")
            content = DocumentContent(source=path)
            body_root = ET.fromstring(archive.read("word/document.xml"))
            content.body, content.tables = _extract_part(body_root, "body")

            for part_name in sorted(name for name in archive.namelist() if name.startswith("word/header") and name.endswith(".xml")):
                root = ET.fromstring(archive.read(part_name))
                part_name_without_extension = Path(part_name).stem
                paragraphs, rows = _extract_part(root, part_name_without_extension)
                content.headers.extend(paragraphs)
                content.headers.extend(rows)

            for part_name in sorted(name for name in archive.namelist() if name.startswith("word/footer") and name.endswith(".xml")):
                root = ET.fromstring(archive.read(part_name))
                part_name_without_extension = Path(part_name).stem
                paragraphs, rows = _extract_part(root, part_name_without_extension)
                content.footers.extend(paragraphs)
                content.footers.extend(rows)
    except (BadZipFile, OSError) as error:
        return None, [
            Diagnostic(
                code="invalid_document",
                message=f"Not a valid DOCX/ZIP container: {error}",
                severity=Severity.ERROR,
            )
        ]
    except ET.ParseError as error:
        return None, [
            Diagnostic(
                code="invalid_document",
                message=f"DOCX contains invalid WordprocessingML: {error}",
                severity=Severity.ERROR,
            )
        ]

    return content, []

