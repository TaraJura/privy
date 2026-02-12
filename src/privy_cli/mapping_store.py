from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MappingStoreError(RuntimeError):
    pass


@dataclass
class MappingData:
    placeholders: dict[str, dict[str, str]]
    created_at: str

    @classmethod
    def create_empty(cls) -> "MappingData":
        return cls(
            placeholders={},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "created_at": self.created_at,
            "placeholders": self.placeholders,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MappingData":
        placeholders = value.get("placeholders", {})
        if not isinstance(placeholders, dict):
            raise MappingStoreError("Invalid mapping payload: placeholders must be an object.")
        created_at = str(value.get("created_at", ""))
        return cls(placeholders=placeholders, created_at=created_at)


def write_mapping(path: Path, mapping: MappingData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def read_mapping(path: Path) -> MappingData:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MappingStoreError(f"Mapping file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MappingStoreError(f"Mapping file is not valid JSON: {path}") from exc

    return MappingData.from_dict(payload)
