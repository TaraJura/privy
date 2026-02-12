# CLAUDE.md — privy-cli

## Project Overview

**privy-cli** is a local CLI utility for reversible `.docx` anonymization using local AI model inference. It detects sensitive entities (PERSON, COMPANY, ADDRESS, EMAIL, PHONE) in Word documents, replaces them with numbered placeholders, and stores an encrypted mapping file to allow later restoration.

Key properties: no external API calls, run-level formatting preservation, PBKDF2+Fernet encrypted mappings.

## Quick Reference

```bash
# Install (editable/dev)
pip install -e ".[dev]"

# Run tests
pytest

# CLI entry point
privy anonymize input.docx -o out.docx --map out.map.enc.json --detector heuristic -e PERSON -e COMPANY
privy deanonymize out.docx -o restored.docx --map out.map.enc.json
privy models list
privy models validate --detector command --model-cmd "python adapter.py"
```

## Project Structure

```
src/privy_cli/
├── __init__.py          # Package version (__version__ = "0.1.0")
├── types.py             # EntitySpan, SpanReplacement dataclasses; VALID_ENTITY_TYPES
├── cli.py               # Typer CLI app — commands: anonymize, deanonymize, models list/validate
├── detector.py          # BaseDetector (ABC), CommandDetector (subprocess JSON), HeuristicDetector (regex)
├── anonymizer.py        # anonymize_docx(), deanonymize_docx() — core pipeline
├── docx_engine.py       # iter_document_paragraphs(), apply_replacements_to_paragraph() — run-level ops
└── mapping_store.py     # MappingData, write/read_encrypted_mapping — PBKDF2+Fernet encryption

tests/
├── test_mapping_store.py      # Encryption roundtrip + wrong password
└── test_docx_roundtrip.py     # Full anonymize→deanonymize with formatting checks

examples/
└── model_adapter_example.py   # Template for external model adapter (stdin JSON → stdout JSON)
```

## Architecture

```
CLI (cli.py / Typer)
  └─ anonymizer.py  ←  detector.py (Strategy pattern: Command | Heuristic)
       ├─ docx_engine.py   (paragraph traversal + run-level text replacement)
       ├─ mapping_store.py  (encrypted mapping read/write)
       └─ types.py          (EntitySpan, SpanReplacement)
```

**Data flow (anonymize):** Input.docx → iterate paragraphs (body, tables, headers, footers) → detect entities → filter by type/confidence/overlap → generate placeholders (PERSON_001) → replace at run level → save anonymized docx + encrypted mapping.

**Data flow (deanonymize):** Anonymized.docx + encrypted mapping → decrypt → find placeholders in text → replace with originals at run level → save restored docx.

## Code Conventions

- **Python ≥ 3.10** required
- `from __future__ import annotations` in every module
- Modern type hints: `str | None`, `list[EntitySpan]`, `dict[str, str]`
- Frozen dataclasses for value types (`EntitySpan`, `SpanReplacement`, `ParagraphRef`)
- Private helpers prefixed with `_` (e.g., `_normalize_label`, `_overlaps`)
- Constants as `UPPER_SNAKE_CASE` (`VALID_ENTITY_TYPES`, `PBKDF2_ITERATIONS`)
- Custom exceptions inherit from `RuntimeError`: `DetectorError`, `AnonymizationError`, `MappingStoreError`
- Relative imports within the package (`from .types import EntitySpan`)
- No linter/formatter explicitly configured (no ruff/black/flake8 config present)

## Dependencies

- **typer** ≥ 0.12.3 — CLI framework
- **python-docx** ≥ 1.1.2 — Word document manipulation
- **cryptography** ≥ 43.0.0 — PBKDF2 key derivation + Fernet encryption
- **pytest** ≥ 8.0.0 — testing (dev dependency)

## Build System

- **setuptools** ≥ 68 with `src` layout (`package-dir = {"" = "src"}`)
- Entry point: `privy = "privy_cli.cli:app"`
- pytest configured with `pythonpath = ["src"]`

## Environment Variables

- `PRIVY_MAP_PASSWORD` — mapping encryption password (alternative to `--map-password` prompt)
- `PRIVY_MODEL_CMD` — model command (alternative to `--model-cmd` flag)

## Model Adapter Protocol

External model commands receive JSON on stdin and must return JSON on stdout:

**Input:** `{"text": "Jane Doe works at Acme LLC."}`
**Output:** `{"entities": [{"start": 0, "end": 8, "label": "PERSON", "confidence": 0.99}, ...]}`

Supported labels: PERSON, COMPANY, ADDRESS, EMAIL, PHONE. Aliases normalized: PER→PERSON, ORG→COMPANY, LOC→ADDRESS, TEL→PHONE, etc.

## Key Design Decisions

- **Strategy pattern** for detectors — easy to add new backends by subclassing `BaseDetector`
- **Run-level replacement** in docx_engine preserves bold/italic/color formatting
- **Deduplication** via reverse_index: same (label, original) pair → same placeholder across entire document
- **Overlap resolution** in `_select_entities`: higher confidence and longer spans win
- **Longest-match-first** during deanonymization to prevent partial placeholder matches
- **390,000 PBKDF2 iterations** with random 16-byte salt per mapping file
