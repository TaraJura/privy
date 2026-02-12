from __future__ import annotations

from dataclasses import dataclass

VALID_ENTITY_TYPES = {"PERSON", "COMPANY", "ADDRESS", "EMAIL", "PHONE", "DOC_ID", "NATIONAL_ID"}


@dataclass(frozen=True)
class EntitySpan:
    start: int
    end: int
    label: str
    text: str
    confidence: float = 1.0


@dataclass(frozen=True)
class SpanReplacement:
    start: int
    end: int
    replacement: str
