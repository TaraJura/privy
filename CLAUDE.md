# CLAUDE.md — privy-cli

## CRITICAL RULES

1. **After EVERY code change, you MUST update this CLAUDE.md to reflect the current state of the project.** This includes but is not limited to: adding/removing files, changing module responsibilities, adding/removing dependencies, changing entity types, modifying CLI commands, altering architecture, or changing conventions.
2. **When adding a new file** — add it to the Project Structure section with a one-line description.
3. **When removing a file** — remove it from the Project Structure section.
4. **When adding/removing a dependency** — update the Dependencies section.
5. **When adding/removing a CLI command** — update the Quick Reference section.
6. **When changing architecture or data flow** — update the Architecture section.
7. **CLAUDE.md is the single source of truth.** If it contradicts the code, update it. Never leave it stale.

## Project Overview

**privy-cli** is a local tool for reversible `.docx` anonymization using GLiNER (local zero-shot NER model) + regex patterns. It detects sensitive entities in Word documents, replaces them with numbered placeholders, and stores a JSON mapping file to allow later restoration. Available as both a CLI and a drag-and-drop GUI (pywebview).

Key properties: fully local (no API calls), GLiNER + regex hybrid detection, run-level formatting preservation, hyperlink-aware, plain JSON mapping files, native GUI via pywebview.

## Quick Reference

```bash
# Install (editable/dev with GUI)
pip install -e ".[gui,dev]"

# Run tests
pytest

# Launch GUI (drag-and-drop interface)
privy gui

# Anonymize (CLI — all entity types detected by default)
privy anonymize input.docx -o out/anonymized.docx

# Deanonymize (CLI)
privy deanonymize out/anonymized.docx -o out/restored.docx --map out/anonymized.docx.map.json

# List/validate detectors
privy models list
privy models validate

# Build standalone macOS .pkg (unsigned)
./scripts/build_macos.sh
```

## Project Structure

```
src/privy_cli/
├── __init__.py          # Package version (__version__ = "0.1.0")
├── __main__.py          # Entry point — launches GUI if frozen+no args, else CLI
├── types.py             # EntitySpan, SpanReplacement dataclasses; VALID_ENTITY_TYPES set
├── cli.py               # Typer CLI — no-arg launches GUI; commands: anonymize, deanonymize, gui, models list/validate
├── gui.py               # pywebview GUI — Api class (JS↔Python bridge), launch_gui()
├── gui_html.py          # Embedded HTML/CSS/JS for the GUI (single Python string constant)
├── detector.py          # BaseDetector (ABC), GlinerDetector, CommandDetector, HeuristicDetector
├── anonymizer.py        # anonymize_docx(), deanonymize_docx(), ProcessingReport, AnonymizationError
├── docx_engine.py       # ParagraphRef, iter_document_paragraphs(), paragraph_text(), apply_replacements_to_paragraph()
└── mapping_store.py     # MappingData, write_mapping(), read_mapping(), MappingStoreError

tests/
├── test_mapping_store.py      # Mapping roundtrip + missing file error
└── test_docx_roundtrip.py     # Full anonymize→deanonymize with formatting checks

models/                        # GLiNER model cache (auto-downloaded on first run, gitignored)
examples/
└── model_adapter_example.py   # Template for external command detector adapter (stdin/stdout JSON)
example_data.docx              # Sample .docx for manual testing

# Packaging & build
privy.spec                     # PyInstaller spec (CLI onedir mode, collect_all for gliner/transformers/torch)
entitlements.plist             # macOS hardened runtime entitlements for PyTorch JIT
scripts/
└── build_macos.sh             # Full macOS build pipeline (venv → pyinstaller → sign → pkg → notarize)
packaging/
├── distribution.xml           # macOS .pkg distribution definition
├── resources/welcome.html     # Installer welcome screen
└── scripts/
    ├── postinstall            # Creates /usr/local/bin/privy symlink
    └── preinstall             # Cleans previous install on upgrade
.github/workflows/
└── build-macos.yml            # CI/CD: builds arm64 .pkg on version tags, uploads to GitHub Release
```

## Architecture

```
CLI (cli.py / Typer)  ─or─  GUI (gui.py / pywebview)
  └─ anonymizer.py  ←  detector.py (Strategy: GLiNER + regex | Command | Heuristic)
       ├─ docx_engine.py   (paragraph traversal + run-level replacement)
       ├─ mapping_store.py  (plain JSON mapping read/write)
       └─ types.py          (EntitySpan, SpanReplacement)
```

**Data flow (anonymize):** Input.docx → iterate paragraphs (body, tables, headers, footers) → extract text including hyperlink runs → detect entities → filter by type/confidence/overlap → filter out legal role labels → generate placeholders (PERSON_001) → deduplicate across document → replace at run level → save anonymized docx + JSON mapping.

**Data flow (deanonymize):** Anonymized.docx + JSON mapping → find placeholders in text → replace with originals at run level → save restored docx.

**GUI flow:** pywebview window loads HTML from `gui_html.py` → JS calls `window.pywebview.api.*` methods → `Api` class in `gui.py` calls `anonymize_docx()`/`deanonymize_docx()` in worker threads → progress pushed to JS via `evaluate_js()` → results displayed in status area.

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

### Required
- **typer** >= 0.12.3 — CLI framework
- **python-docx** >= 1.1.2 — Word document manipulation
- **gliner** >= 0.2.5 — Local zero-shot NER model

### Optional extras
- **pywebview** >= 5.0 — Native GUI (`pip install -e ".[gui]"`)
- **pytest** >= 8.0.0 — Testing (`pip install -e ".[dev]"`)

## Build System

- **setuptools** >= 68 with `src` layout (`package-dir = {"" = "src"}`)
- Entry point: `privy = "privy_cli.cli:app"`
- Optional dependency groups: `[gui]` (pywebview), `[dev]` (pytest)
- pytest configured with `pythonpath = ["src"]`

## macOS Packaging & Distribution

Distributed as a standalone macOS `.pkg` installer via GitHub Releases and Homebrew cask.

```bash
# Local build (unsigned)
./scripts/build_macos.sh

# Signed + notarized build (requires Apple Developer ID)
CODESIGN_IDENTITY="Developer ID Application: ..." \
INSTALLER_IDENTITY="Developer ID Installer: ..." \
APPLE_ID="..." TEAM_ID="..." APP_SPECIFIC_PASSWORD="..." \
  ./scripts/build_macos.sh
```

**Build pipeline:** venv setup → PyInstaller (onedir, collect_all for gliner/transformers/torch) → patch python-docx template paths (mkdir docx/parts) → smoke test → sign binaries → pkgbuild/productbuild → sign .pkg → notarize → staple

**GitHub Actions:** Push a `v*` tag → builds arm64 .pkg on macos-14 → uploads to GitHub Release.

**Homebrew:** `brew tap TaraJura/privy && brew install --cask privy` (repo: TaraJura/homebrew-privy, cask file: Casks/privy.rb)

**Install location:** `/usr/local/lib/privy/` with symlink at `/usr/local/bin/privy`

**Model cache (frozen app):** `~/Library/Application Support/privy-cli/models/` (detected via `sys.frozen`)

**Known PyInstaller issues:**
- `gliner` is lazily imported (try/except) — must use `collect_all()` not just `hiddenimports`
- `torch` internal imports reference `torch.distributed`, `torch.testing`, `unittest` — do NOT exclude these
- `python-docx` parts/*.py reference `../templates/*.xml` via `__file__` — must create empty `docx/parts/` dir post-build

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
- **Legal role label filtering** — all-caps party descriptors (e.g. "THE CONSULTANT") excluded via `_LEGAL_ROLE_WORDS` set in `anonymizer.py`
- **Overlap resolution** — higher confidence and longer spans win, processed in `_select_entities()`
- **Local model cache** in `models/` directory (gitignored) — downloads once on first run
- **Frozen app model path** — `_get_default_models_dir()` in `detector.py` uses `~/Library/Application Support/privy-cli/models/` when `sys.frozen` is set
- **macOS packaging** — PyInstaller onedir + `.pkg` installer, signed/notarized for Gatekeeper
- **GUI via pywebview** — native WebKit on macOS, Edge/WebView2 on Windows; HTML/CSS/JS embedded as Python string; drag-and-drop file input; auto-named outputs (`input_anonymized.docx`); map file auto-detection for deanonymize
- **GUI detector caching** — `GlinerDetector` built once and reused across operations (thread-safe via `_detector_lock`)
