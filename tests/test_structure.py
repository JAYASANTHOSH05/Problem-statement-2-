from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from author_parser import Author, author_variants, match_author, normalize_token
from docx_reader import read_docx
from main import process_directory
from taxonomy import EXPECTED_ROLE_COUNT, OFFICIAL_TAXONOMY_URL


ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_required_modules_exist(self) -> None:
        for name in (
            "main.py",
            "docx_reader.py",
            "author_parser.py",
            "contribution_parser.py",
            "credit_normalizer.py",
            "taxonomy.py",
            "models.py",
            "requirements.txt",
            "README.md",
            "run.sh",
        ):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_author_matching_is_unambiguous(self) -> None:
        jane = Author("Jane Doe", normalize_token("Jane Doe"), author_variants("Jane Doe"))
        self.assertIs(match_author("J.D.", [jane]), jane)
        self.assertIsNone(match_author("A.B.", [jane]))

    def test_invalid_docx_is_reported(self) -> None:
        content, diagnostics = read_docx(ROOT / "manuscripts" / "merged_12.docx")
        self.assertIsNone(content)
        self.assertEqual(diagnostics[0].code, "invalid_document")

    def test_reader_extracts_body_table_header_and_footer(self) -> None:
        content, diagnostics = read_docx(ROOT / "manuscripts" / "merged_13.docx")
        self.assertEqual(diagnostics, [])
        self.assertIsNotNone(content)
        assert content is not None
        self.assertTrue(any(block.text == "Acknowledgements" for block in content.body))
        self.assertTrue(any(block.kind == "table_row" and block.cells for block in content.tables))
        self.assertTrue(any("Author Contributions: J.D.: Software" in block.text for block in content.headers))
        self.assertTrue(any("Contributors: A.B.: Conceptualization" in block.text for block in content.footers))
        self.assertTrue(all(block.location.startswith("body:") for block in content.body))
        self.assertTrue(all(block.location.startswith("body:table:") for block in content.tables))

    def test_table_cells_are_preserved(self) -> None:
        content, diagnostics = read_docx(ROOT / "manuscripts" / "merged_08.docx")
        self.assertEqual(diagnostics, [])
        assert content is not None
        contribution_row = next(block for block in content.tables if block.cells[0] == "K.L.")
        self.assertEqual(contribution_row.cells, ("K.L.", "Software, Validation"))
        self.assertEqual(contribution_row.location, "body:table:1:row:0")

    def test_empty_valid_document_returns_empty_collections(self) -> None:
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body/></w:document>'
        )
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "empty.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
            content, diagnostics = read_docx(path)
        self.assertEqual(diagnostics, [])
        self.assertIsNotNone(content)
        assert content is not None
        self.assertEqual(content.body, [])
        self.assertEqual(content.tables, [])
        self.assertEqual(content.headers, [])
        self.assertEqual(content.footers, [])

    def test_batch_continues_after_corrupted_document(self) -> None:
        results, _ = process_directory(ROOT / "manuscripts", roles=("Software",))
        self.assertEqual(len(results), 20)
        invalid = [result for result in results if result.source.name == "merged_12.docx"]
        self.assertEqual(invalid[0].diagnostics[0].code, "invalid_document")
        self.assertTrue(any(result.source.name == "merged_13.docx" for result in results))

    def test_taxonomy_contract_is_explicit(self) -> None:
        self.assertEqual(EXPECTED_ROLE_COUNT, 14)
        self.assertTrue(OFFICIAL_TAXONOMY_URL.startswith("https://credit.niso.org/"))


if __name__ == "__main__":
    unittest.main()
