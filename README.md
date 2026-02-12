# privy-cli

Local CLI utility for reversible `.docx` anonymization using GLiNER (zero-shot NER) + regex patterns.

## Features

- Anonymize `.docx` files while preserving run-level formatting (bold, italic, etc.).
- Hybrid detection: GLiNER model for names/companies/addresses, regex for emails/phones/IDs.
- Deanonymize from plain JSON mapping file.
- Handles text inside hyperlinks, tables, headers, and footers.
- Fully local — no external API calls.

## Install

```bash
pip install -e .
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
