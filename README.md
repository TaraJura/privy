# privy

Local tool for reversible `.docx` anonymization. Drag and drop a Word document, get an anonymized copy with a mapping file to restore the original.

## Features

- Drag-and-drop GUI — no terminal needed.
- Hybrid AI detection: GLiNER model for names/companies/addresses, regex for emails/phones/IDs.
- Preserves formatting (bold, italic, colors) during anonymization.
- Handles text inside hyperlinks, tables, headers, and footers.
- Reversible — restore the original from the mapping file.
- Fully local — no data leaves your machine.

## Install

```bash
brew tap TaraJura/privy
brew install --cask privy
```

## Use

Launch the app:

```bash
privy
```

This opens the GUI. Drag a `.docx` file onto the window and click **Anonymize**.

The first run downloads the AI model (~750 MB). This is a one-time download.

### Output

Anonymizing `contract.docx` produces:
- `contract_anonymized.docx` — sensitive data replaced with placeholders (`PERSON_001`, `COMPANY_001`, etc.)
- `contract_anonymized.docx.map.json` — mapping file to restore the original

To restore, drag the anonymized file back and click **Deanonymize** (the mapping file is detected automatically).

## CLI

All features are also available from the command line:

```bash
# Anonymize
privy anonymize contract.docx -o anonymized.docx

# Restore
privy deanonymize anonymized.docx -o restored.docx --map anonymized.docx.map.json

# Narrow to specific entity types
privy anonymize contract.docx -o out.docx -e PERSON -e EMAIL
```

Entity types detected: `PERSON`, `COMPANY`, `ADDRESS`, `EMAIL`, `PHONE`, `DOC_ID`, `NATIONAL_ID`.

## Dev

```bash
pip install -e ".[gui,dev]"
pytest
privy gui
```
