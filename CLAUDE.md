# CLAUDE.md — privy-cli

## CRITICAL RULE

**After every code change, you MUST update this CLAUDE.md to reflect the current state of the project.** This includes but is not limited to: adding/removing files, changing module responsibilities, adding/removing dependencies, changing entity types, modifying CLI commands, altering architecture, or changing conventions. CLAUDE.md must always be the single source of truth for the project structure and design.

## Project Overview

**privy-cli** is a local CLI utility for reversible `.docx` anonymization using GLiNER (local zero-shot NER model) + regex patterns. It detects sensitive entities in Word documents, replaces them with numbered placeholders, and stores a JSON mapping file to allow later restoration.

Key properties: fully local (no API calls), GLiNER + regex hybrid detection, run-level formatting preservation, hyperlink-aware, plain JSON mapping files.

## Quick Reference

```bash
# Install (editable/dev)
pip install -e ".[dev]"

# Run tests
pytest

# Anonymize (all entity types detected by default)
privy anonymize input.docx -o out/anonymized.docx

# Deanonymize
privy deanonymize out/anonymized.docx -o out/restored.docx --map out/anonymized.docx.map.json

# List/validate detectors
privy models list
privy models validate
```

## Project Structure

```
src/privy_cli/
├── __init__.py          # Package version (__version__ = "0.1.0")
├── types.py             # EntitySpan, SpanReplacement dataclasses; VALID_ENTITY_TYPES
├── cli.py               # Typer CLI — commands: anonymize, deanonymize, models list/validate
├── detector.py          # BaseDetector (ABC), GlinerDetector (default), CommandDetector, HeuristicDetector
├── anonymizer.py        # anonymize_docx(), deanonymize_docx() — core pipeline
├── docx_engine.py       # Paragraph traversal (incl. hyperlinks), run-level text replacement
└── mapping_store.py     # MappingData, write_mapping(), read_mapping() — plain JSON

tests/
├── test_mapping_store.py      # Mapping roundtrip + missing file error
└── test_docx_roundtrip.py     # Full anonymize→deanonymize with formatting checks

models/                        # GLiNER model cache (auto-downloaded on first run, gitignored)
examples/
└── model_adapter_example.py   # Template for external command detector adapter (stdin/stdout JSON)
```

## Architecture

```
CLI (cli.py / Typer)
  └─ anonymizer.py  ←  detector.py (Strategy: GLiNER + regex | Command | Heuristic)
       ├─ docx_engine.py   (paragraph traversal + run-level replacement)
       ├─ mapping_store.py  (plain JSON mapping read/write)
       └─ types.py          (EntitySpan, SpanReplacement)
```

**Data flow (anonymize):** Input.docx → iterate paragraphs (body, tables, headers, footers) → extract text including hyperlink runs → detect entities → filter by type/confidence/overlap → generate placeholders (PERSON_001) → replace at run level → save anonymized docx + JSON mapping.

**Data flow (deanonymize):** Anonymized.docx + JSON mapping → find placeholders in text → replace with originals at run level → save restored docx.

## Entity Detection Strategy

The default `GlinerDetector` uses a hybrid approach:

| Entity Type | Detection Method | Why |
|-------------|-----------------|-----|
| PERSON | GLiNER model | Best at natural language names |
| COMPANY | GLiNER model | Best at organization names |
| ADDRESS | GLiNER model | Best at location/address text |
| EMAIL | Regex | Structured pattern, GLiNER unreliable |
| PHONE | Regex | Structured pattern, GLiNER misclassifies |
| DOC_ID | Regex | Alphanumeric codes (e.g. SEC-9920-X) |
| NATIONAL_ID | Regex | National ID numbers (e.g. Czech rodné číslo 880512/0012) |

GLiNER labels sent to model: `"person"`, `"organization"`, `"location"`.
GLiNER results for PHONE/EMAIL/DOC_ID/NATIONAL_ID are ignored — regex handles those.

## Code Conventions

- **Python >= 3.10** required
- `from __future__ import annotations` in every module
- Modern type hints: `str | None`, `list[EntitySpan]`, `dict[str, str]`
- Frozen dataclasses for value types (`EntitySpan`, `SpanReplacement`, `ParagraphRef`)
- Private helpers prefixed with `_` (e.g., `_normalize_label`, `_all_runs`)
- Constants as `UPPER_SNAKE_CASE` (`VALID_ENTITY_TYPES`, `GLINER_LABEL_MAP`)
- Custom exceptions inherit from `RuntimeError`: `DetectorError`, `AnonymizationError`, `MappingStoreError`
- Relative imports within the package (`from .types import SpanReplacement`)

## Dependencies

- **typer** >= 0.12.3 — CLI framework
- **python-docx** >= 1.1.2 — Word document manipulation
- **gliner** >= 0.2.5 — Local zero-shot NER model
- **pytest** >= 8.0.0 — testing (dev dependency)

## Build System

- **setuptools** >= 68 with `src` layout (`package-dir = {"" = "src"}`)
- Entry point: `privy = "privy_cli.cli:app"`
- pytest configured with `pythonpath = ["src"]`

## Environment Variables

- `PRIVY_GLINER_MODEL` — GLiNER model name/path (default: `urchade/gliner_medium-v2.1`)
- `PRIVY_MODEL_CMD` — model command for the `command` detector backend

## Key Design Decisions

- **Hybrid detection** — GLiNER for semantic entities (names, orgs, addresses), regex for structured patterns (emails, phones, IDs)
- **Hyperlink-aware** — `_all_runs()` walks paragraph XML to include text inside `<w:hyperlink>` elements
- **Plain JSON mappings** — simple, readable, no encryption
- **Run-level replacement** preserves bold/italic/color formatting
- **All 7 entity types on by default** — PERSON, COMPANY, ADDRESS, EMAIL, PHONE, DOC_ID, NATIONAL_ID
- **Deduplication** — same (label, original) pair → same placeholder across entire document
- **Overlap resolution** — higher confidence and longer spans win, processed in `_select_entities()`
- **Local model cache** in `models/` directory (gitignored) — downloads once on first run, loads locally after
- **Model stored in repo** at `models/urchade--gliner_medium-v2.1/`, not in `~/.cache/huggingface`
