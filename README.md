# privy-cli

Local CLI utility for reversible `.docx` anonymization using GLiNER (zero-shot NER) + regex patterns.

## Features

- Anonymize `.docx` files while preserving run-level formatting (bold, italic, etc.).
- Hybrid detection: GLiNER model for names/companies/addresses, regex for emails/phones/IDs.
- Deanonymize from plain JSON mapping file.
- Handles text inside hyperlinks, tables, headers, and footers.
- Fully local — no external API calls.

## Install (macOS)

1. Go to [Releases](https://github.com/TaraJura/privy/releases/latest) and download **`privy-0.1.0-arm64.pkg`** (Apple Silicon).
2. Double-click the `.pkg` file and follow the installer.
3. Open **Terminal** (search "Terminal" in Spotlight) and verify it works:

```bash
privy --help
```

That's it — no Python, no pip, no setup required.

> **First run note:** The first time you anonymize a document, privy downloads the GLiNER language model (~750 MB). This is a one-time download and takes a few minutes depending on your connection.

## Quick start

**Anonymize a document:**

```bash
privy anonymize contract.docx -o anonymized.docx
```

This produces two files:
- `anonymized.docx` — your document with sensitive data replaced by placeholders like `PERSON_001`, `COMPANY_001`, etc.
- `anonymized.docx.map.json` — the mapping file needed to restore the original text.

**Restore the original:**

```bash
privy deanonymize anonymized.docx -o restored.docx --map anonymized.docx.map.json
```

## Usage

Anonymize (all entity types detected by default):

```bash
privy anonymize input.docx -o out/anonymized.docx
```

Deanonymize:

```bash
privy deanonymize out/anonymized.docx -o out/restored.docx --map out/anonymized.docx.map.json
```

List available detectors:

```bash
privy models list
```

## Entity types

All detected by default: `PERSON`, `COMPANY`, `ADDRESS`, `EMAIL`, `PHONE`, `DOC_ID`, `NATIONAL_ID`.

Narrow with `-e`:

```bash
privy anonymize input.docx -o out.docx -e PERSON -e EMAIL
```

## Dev

```bash
pip install -e ".[dev]"
pytest
```
