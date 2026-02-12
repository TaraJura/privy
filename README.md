# privy-cli

Local CLI utility for reversible `.docx` anonymization and deanonymization using local model inference.

## Features

- Anonymize `.docx` files while preserving run-level formatting.
- Deanonymize from encrypted mapping file.
- Local model integration through a command adapter (JSON in/out).
- No external API calls required.

## Install

```bash
pip install -e .
```

## CLI usage

Anonymize using local model command:

```bash
privy anonymize input.docx \
  --output anonymized.docx \
  --map anonymized.map.enc.json \
  --detector command \
  --model-cmd "python /absolute/path/to/your_model_adapter.py" \
  --entity-type PERSON --entity-type COMPANY --entity-type ADDRESS
```

Deanonymize:

```bash
privy deanonymize anonymized.docx \
  --output restored.docx \
  --map anonymized.map.enc.json
```

Validate model command:

```bash
privy models validate --detector command --model-cmd "python /absolute/path/to/your_model_adapter.py"
```

## Local model adapter contract

`privy-cli` calls your model command with JSON input via `stdin`:

```json
{"text":"Jane Doe works at Acme LLC on 123 Main Street."}
```

Your command must return JSON via `stdout`:

```json
{
  "entities": [
    {"start": 0, "end": 8, "label": "PERSON", "confidence": 0.99},
    {"start": 18, "end": 26, "label": "COMPANY", "confidence": 0.96},
    {"start": 30, "end": 45, "label": "ADDRESS", "confidence": 0.94}
  ]
}
```

Supported labels: `PERSON`, `COMPANY`, `ADDRESS`, `EMAIL`, `PHONE`.
Aliases like `PER`, `ORG`, `LOC` are normalized.

## Security notes

- The deanonymization mapping is encrypted using PBKDF2 + Fernet.
- Keep the mapping file and password secure; both are required for restoration.

## Dev

```bash
pytest
```
# privy
