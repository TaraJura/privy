#!/usr/bin/env python3
"""Minimal local adapter example for privy-cli.

Replace `detect_entities` with your real local model call.
"""

from __future__ import annotations

import json
import re
import sys


def detect_entities(text: str) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []

    # Demo-only patterns
    for match in re.finditer(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", text):
        entities.append(
            {
                "start": match.start(),
                "end": match.end(),
                "label": "PERSON",
                "confidence": 0.7,
            }
        )

    for match in re.finditer(r"\b(?:[A-Z][\w&.-]*\s+){0,3}[A-Z][\w&.-]*\s(?:Inc|LLC|Ltd|Corp)\b", text):
        entities.append(
            {
                "start": match.start(),
                "end": match.end(),
                "label": "COMPANY",
                "confidence": 0.8,
            }
        )

    for match in re.finditer(r"\b\d{1,5}\s+[A-Z][A-Za-z0-9.'-]*(?:\s+[A-Z][A-Za-z0-9.'-]*){0,5}\s(?:Street|St|Road|Rd|Avenue|Ave)\b", text):
        entities.append(
            {
                "start": match.start(),
                "end": match.end(),
                "label": "ADDRESS",
                "confidence": 0.8,
            }
        )

    return entities


def main() -> int:
    payload = json.load(sys.stdin)
    text = payload.get("text", "")
    out = {"entities": detect_entities(text)}
    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
