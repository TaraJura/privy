# CLAUDE.md — privy-cli

## Project Overview

**privy-cli** is a local CLI utility for reversible `.docx` anonymization using GLiNER (local zero-shot NER model). It detects sensitive entities (PERSON, COMPANY, ADDRESS, EMAIL, PHONE) in Word documents, replaces them with numbered placeholders, and stores a JSON mapping file to allow later restoration.

Key properties: fully local (no API calls), GLiNER-based NER, run-level formatting preservation, plain JSON mapping files.

## Quick Reference

```bash
# Install (editable/dev)
pip install -e ".[dev]"

# Run tests
pytest

# Anonymize (all entity types by default, GLiNER detector by default)
privy anonymize input.docx -o out/anonymized.docx

# Deanonymize
privy deanonymize out/anonymized.docx -o out/restored.docx --map out/anonymized.docx.map.json

# List detectors
privy models list

# Validate detector
privy models validate
```

## Project Structure

```
src/privy_cli/
├── __init__.py          # Package version (__version__ = "0.1.0")
├── types.py             # EntitySpan, SpanReplacement dataclasses; VALID_ENTITY_TYPES
├── cli.py               # Typer CLI app — commands: anonymize, deanonymize, models list/validate
├── detector.py          # BaseDetector (ABC), GlinerDetector (default), CommandDetector, HeuristicDetector
├── anonymizer.py        # anonymize_docx(), deanonymize_docx() — core pipeline
├── docx_engine.py       # iter_document_paragraphs(), apply_replacements_to_paragraph() — run-level ops
└── mapping_store.py     # MappingData, write_mapping(), read_mapping() — plain JSON

tests/
├── test_mapping_store.py      # Mapping roundtrip + missing file
└── test_docx_roundtrip.py     # Full anonymize→deanonymize with formatting checks

models/                        # GLiNER model cache (auto-downloaded on first run, gitignored)
examples/
└── model_adapter_example.py   # Template for external command detector adapter
```

## Architecture

```
CLI (cli.py / Typer)
  └─ anonymizer.py  ←  detector.py (Strategy pattern: GLiNER | Command | Heuristic)
       ├─ docx_engine.py   (paragraph traversal + run-level text replacement)
       ├─ mapping_store.py  (plain JSON mapping read/write)
       └─ types.py          (EntitySpan, SpanReplacement)
```

**Data flow (anonymize):** Input.docx → iterate paragraphs (body, tables, headers, footers) → detect entities via GLiNER → filter by type/confidence/overlap → generate placeholders (PERSON_001) → replace at run level → save anonymized docx + JSON mapping.

**Data flow (deanonymize):** Anonymized.docx + JSON mapping → find placeholders in text → replace with originals at run level → save restored docx.

## Code Conventions

- **Python >= 3.10** required
- `from __future__ import annotations` in every module
- Modern type hints: `str | None`, `list[EntitySpan]`, `dict[str, str]`
- Frozen dataclasses for value types (`EntitySpan`, `SpanReplacement`, `ParagraphRef`)
- Private helpers prefixed with `_` (e.g., `_normalize_label`, `_overlaps`)
- Constants as `UPPER_SNAKE_CASE` (`VALID_ENTITY_TYPES`, `GLINER_LABEL_MAP`)
- Custom exceptions inherit from `RuntimeError`: `DetectorError`, `AnonymizationError`, `MappingStoreError`
- Relative imports within the package (`from .types import EntitySpan`)

## Dependencies

- **typer** >= 0.12.3 — CLI framework
- **python-docx** >= 1.1.2 — Word document manipulation
- **gliner** >= 0.2.5 — Local zero-shot NER (GLiNER model)
- **pytest** >= 8.0.0 — testing (dev dependency)

## Build System

- **setuptools** >= 68 with `src` layout (`package-dir = {"" = "src"}`)
- Entry point: `privy = "privy_cli.cli:app"`
- pytest configured with `pythonpath = ["src"]`

## Environment Variables

- `PRIVY_MODEL_CMD` — model command for command detector
- `PRIVY_GLINER_MODEL` — GLiNER model name/path (default: `urchade/gliner_medium-v2.1`)

## GLiNER Integration

- Default detector, no flags needed
- Model auto-downloads to `models/` inside the repo on first run, loads locally after that
- Entity type mapping: PERSON→"person", COMPANY→"organization", ADDRESS→"location", EMAIL→"email", PHONE→"phone number"
- Label aliases normalize GLiNER output back to privy types (e.g., "organization"→COMPANY)

## Key Design Decisions

- **Strategy pattern** for detectors — easy to add new backends by subclassing `BaseDetector`
- **GLiNER as default** — local, zero-shot, no setup needed beyond `pip install`
- **Plain JSON mappings** — simple, readable, no encryption overhead
- **Run-level replacement** in docx_engine preserves bold/italic/color formatting
- **All entity types on by default** — PERSON, COMPANY, ADDRESS, EMAIL, PHONE
- **Deduplication** via reverse_index: same (label, original) pair → same placeholder across entire document
- **Overlap resolution** in `_select_entities`: higher confidence and longer spans win
- **Local model cache** in `models/` directory (gitignored) — no repeated downloads
