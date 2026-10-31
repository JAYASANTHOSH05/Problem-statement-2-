# CRediT Contributor Role Normalization

Python 3.11+ batch tool for extracting manuscript contributor statements and normalizing them to the NISO CRediT taxonomy. It is verified with Python 3.13.3 on Windows.

## Setup

On Windows PowerShell, open the project folder, create a virtual environment with the installed Python 3.13 launcher, and activate it:

```powershell
Set-Location 'C:\Users\jayas\OneDrive\Desktop\Tnq tech'
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow it for the current terminal only, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install the test and mutation-test dependencies:

```powershell
python -m pip install -r requirements.txt
```

Runtime code uses the standard library. The tool fetches the official NISO taxonomy from [CRediT role descriptors](https://credit.niso.org/contributor-roles-defined/) when it runs, so network access is required.

Place the manuscript input files in the `manuscripts` directory inside the project folder. The supplied batch is `merged_01.docx` through `merged_20.docx`; `merged_12.docx` is intentionally invalid and is reported without stopping the batch.

## Run

```powershell
python main.py manuscripts --output-dir results
```

The input directory may contain `.docx` or `.DOCX` files. Each file is processed independently; invalid DOCX files are diagnosed without stopping the remaining batch.

Exit codes:

- `0`: taxonomy retrieval succeeded and reports were written.
- `2`: taxonomy retrieval failed; reports were written, but normalized role output is unavailable.

## Outputs

- `output.csv`: `file,author,credit_role`. An author-associated contribution that cannot be mapped confidently is written as `INVALID`.
- `test_report.csv`: processing status, validation status, and complete taxonomy/document diagnostics.

Missing contribution sections, roster mismatches, and unmapped phrasing do not stop processing; they appear in `test_report.csv` as validation issues.

## Test

```powershell
python -m pytest -v
```

The suite includes a deterministic golden-output regression fixture for all valid supplied manuscripts. Mutation testing is configured in `pyproject.toml`, but mutmut requires WSL on Windows.

## Test Documentation

See [Test Suite Documentation](TEST_SUITE_DOCUMENTATION.md) for the complete explanation of all nine test files, their scenarios, and interview explanations.
