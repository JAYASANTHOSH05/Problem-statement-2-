
# Quality Engineering Assessment

## Test Suite Documentation

**Project:** DOCX Manuscript Parsing and CRediT Contribution Extraction

## 1. Project Overview

The application processes Word documents (DOCX) and extracts author contribution information.

The main workflow is:

- Read DOCX manuscripts.
- Identify the authors.
- Extract contribution statements.
- Match authors with their respective contributions.
- Map contributions to the official 14-role CRediT taxonomy.
- Generate `output.csv` and `test_report.csv`.

The test suite verifies that each stage works correctly and that the application handles errors appropriately.

## 2. Test Files Overview

The project contains nine main test files:

| Test File | Purpose |
| --- | --- |
| `test_structure.py` | Tests DOCX reading and document structure. |
| `test_author_parser.py` | Tests author identification and matching. |
| `test_contribution_parser.py` | Tests contribution extraction. |
| `test_credit_normalizer.py` | Tests mapping contributions to CRediT roles. |
| `test_taxonomy.py` | Tests official CRediT taxonomy validation. |
| `test_extraction_accuracy.py` | Tests extraction accuracy and source preservation. |
| `test_failure_handling.py` | Tests error handling and failure scenarios. |
| `test_golden_output.py` | Compares generated output with expected output. |
| `test_main_integration.py` | Tests the complete application workflow. |

## 3. Detailed Test File Explanations

### 3.1 test_structure.py

**Purpose:**

Checks whether the application can correctly read Word documents and handle different document structures.

**Tests performed:**

- Checks whether the required project files and structure are present.
- Tests extraction of ordinary paragraphs from DOCX files.
- Tests extraction of content stored inside tables.
- Tests extraction of header and footer content.
- Checks whether source-location information is correctly identified, including table-cell locations.
- Tests how the application handles invalid or corrupted DOCX files.
- Tests how the application handles valid but empty DOCX files.
- Checks whether batch processing continues when one document is corrupted.

**Simple explanation:**

Before extracting authors and contributions, the application must first be able to read the Word document. This test file verifies that the document reader works correctly.

**Interview explanation:**

The `test_structure.py` file checks whether our application can correctly read DOCX paragraphs, tables, headers and footers. It also tests how the application handles empty or corrupted documents and whether batch processing continues when one document fails.

### 3.2 test_author_parser.py

**Purpose:**

Checks whether the application can identify manuscript authors and correctly match author references appearing in contribution statements.

**Tests performed:**

- Tests author roster extraction from an actual manuscript.
- Tests matching of complete author names.
- Tests author matching with dotted and undotted initials.
- Tests grouped initials representing multiple authors.
- Tests handling of honorifics and affiliation markers around author names.
- Checks whether ambiguous initials are handled without guessing.
- Tests identification of unknown author names.
- Checks that empty or punctuation-only author tokens are rejected.
- Tests whether the parser returns an empty author list when no valid author information is available.

### 3.3 test_contribution_parser.py

**Purpose:**

Checks whether the application can identify contribution statements from different manuscript formats and associate them with the correct authors.

**Tests performed:**

- Tests extraction of structured contribution statements.
- Tests contribution statements where each author's contribution appears in a separate paragraph.
- Tests extraction of contribution information stored in tables.
- Tests extraction of narrative contribution statements.
- Tests grouped-author contribution statements.
- Tests statements where all authors share a contribution.
- Tests inline contribution statements.
- Tests contribution information appearing in headers and footers.
- Tests extraction of multiple roles assigned to one author.
- Tests contribution roles written inside parentheses.
- Tests preservation of contribution degrees such as lead, equal and supporting.
- Tests handling of manuscripts with missing contribution sections.
- Tests detection of unmapped contribution statements.
- Tests handling of ambiguous author attribution.
- Tests identification of unknown authors appearing in tables.
- Checks that unknown structured roles are retained with their original source information and diagnostic messages instead of being silently discarded.

### 3.4 test_credit_normalizer.py

**Purpose:**

Checks whether contribution descriptions can be correctly mapped to the official CRediT taxonomy roles.

**Tests performed:**

- Tests recognition of all 14 official CRediT role labels.
- Tests handling of uppercase and lowercase variations.
- Tests handling of extra spaces and punctuation.
- Tests different dash and wording variations.
- Tests variations involving ampersands and the word "and".
- Tests semantic phrase-to-role mapping rules.
- Tests contribution statements containing multiple roles.
- Checks that unknown or unrelated phrases are rejected.
- Checks that empty contribution descriptions are rejected.
- Ensures the application does not guess a role when the contribution wording is insufficient.


### 3.5 test_taxonomy.py

**Purpose:**

Checks whether the application correctly retrieves and validates the official CRediT taxonomy.

**Tests performed:**

- Tests parsing of a simulated NISO taxonomy response containing role names and descriptions.
- Checks whether missing roles are detected.
- Checks whether duplicate roles are rejected.
- Checks whether unofficial role names are rejected.
- Checks whether empty role descriptions are rejected.
- Tests handling of malformed HTML.
- Tests handling of invalid role entries.
- Checks entries where a role does not have a description.
- Tests handling of network errors.
- Tests handling of invalid taxonomy responses.


### 3.6 test_extraction_accuracy.py

**Purpose:**

Checks whether the extracted information is accurate and whether the original source text and location are preserved.

**Tests performed:**

- Checks preservation of original source text and location for paragraph content.
- Checks preservation of source text and location for table content.
- Checks preservation of source text and location for inline contribution statements.
- Verifies exact author-to-role-to-location associations.
- Checks whether contribution-degree information remains associated with the correct contribution.
- Checks preservation of complete contribution statements from headers and footers.
- Tests protection against false matches caused by reference text.
- Checks whether unmatched-author diagnostics point to the correct source location.
- Checks whether unknown structured roles retain their original source text and generate the expected diagnostic.

### 3.7 test_failure_handling.py

**Purpose:**

Checks whether the application handles unexpected errors and invalid inputs correctly.

**Tests performed:**

- Tests behavior when the input directory is empty.
- Tests a DOCX archive that is missing `document.xml`.
- Tests malformed XML inside a DOCX file.
- Tests processing multiple invalid documents alongside a valid document.
- Tests discovery of files with uppercase `.DOCX` extensions.
- Simulates an HTTP 503 error during taxonomy retrieval.
- Simulates a CSV-writing failure.

### 3.8 test_golden_output.py

**Purpose:**

Checks whether the generated output matches a previously verified expected output.

**Tests performed:**

- Processes the complete set of 20 manuscript documents.
- Compares the generated `output.csv` with `tests/fixtures/golden_output.csv`.
- Detects missing records.
- Detects unexpected extra records.
- Detects duplicate records.
- Checks output ordering where ordering is part of the expected result.
- Checks whether the corrupted manuscript has the expected diagnostic.

### 3.9 test_main_integration.py

**Purpose:**

Checks whether all the major application components work together through the main application.

**Tests performed:**

- Tests batch processing through the main application.
- Checks whether both `output.csv` and `test_report.csv` are generated.
- Checks whether expected author-role records appear in the output.
- Checks whether unmappable contributions are represented as `INVALID` where expected.
- Checks whether corrupted documents are excluded from normalized contribution output.
- Tests whether document reading is still attempted when taxonomy retrieval fails.
- Checks whether the command-line interface returns exit code 2 when taxonomy retrieval fails.
- Checks whether the test report contains `status`, `validation_status` and diagnostic information.


## 4. Overall Test Execution Results

The following results were reported for the latest project test run.

| Metric | Result |
| --- | --- |
| Total test cases passed | 86 |
| Total test cases failed | 0 |
| Total manuscripts | 20 |
| Valid manuscripts | 19 |
| Corrupted manuscripts | 1 |
| Expected normalized output records | 67 |
| Golden-output comparison | Exact match |
| Duplicate records | 0 |
| Live NISO taxonomy retrieval | Successful |

Result: All 86 reported tests passed successfully. The generated output was reported to match the expected golden-output CSV exactly.

## 5. Mutation Testing

Mutation testing was configured using the `mutmut` tool.

The purpose of mutation testing is to check whether the test suite can detect deliberately introduced bugs in the application.

For example, if a developer changes a condition in the author-matching logic, mutation testing checks whether the existing tests detect that incorrect change.

**Project status:**

- Mutation testing was configured for selected application modules.
- Execution was blocked because WSL was not installed in the Windows environment.
- Mutation testing was therefore not executed.
- No mutation score or killed/survived mutant count is available.


## 6. Important Testing Terminology

| Term | Simple Explanation |
| --- | --- |
| Unit Testing | Testing one individual component of the application. |
| Integration Testing | Checking whether multiple components work together. |
| Regression Testing | Checking whether new code changes break previously working functionality. |
| Golden Output | A previously verified expected result used for comparison. |
| Mocking | Using a simulated response instead of depending on a real external service. |
| Diagnostic | A message explaining an error or unusual condition. |
| Validation | Checking whether the extracted information meets the expected requirements. |
| Test Coverage | The functionality or scenarios checked by the test suite. |

