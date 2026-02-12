from __future__ import annotations

import json
import re
import shlex
import subprocess
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .types import EntitySpan, VALID_ENTITY_TYPES

LABEL_ALIASES = {
    "PERSON": "PERSON",
    "PER": "PERSON",
    "NAME": "PERSON",
    "HUMAN": "PERSON",
    "ORG": "COMPANY",
    "ORGANIZATION": "COMPANY",
    "COMPANY": "COMPANY",
    "ADDRESS": "ADDRESS",
    "LOCATION": "ADDRESS",
    "LOC": "ADDRESS",
    "EMAIL": "EMAIL",
    "MAIL": "EMAIL",
    "PHONE": "PHONE",
    "PHONE NUMBER": "PHONE",
    "TEL": "PHONE",
    "MOBILE": "PHONE",
}

# Mapping from privy entity types to GLiNER-friendly labels.
GLINER_LABEL_MAP: dict[str, str] = {
    "PERSON": "person",
    "COMPANY": "organization",
    "ADDRESS": "location",
    "EMAIL": "email",
    "PHONE": "phone number",
}


class DetectorError(RuntimeError):
    pass


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> list[EntitySpan]:
        raise NotImplementedError


@dataclass
class CommandDetector(BaseDetector):
    command: str
    timeout_seconds: int = 30

    def detect(self, text: str) -> list[EntitySpan]:
        if not text.strip():
            return []

        args = shlex.split(self.command)
        payload = json.dumps({"text": text}, ensure_ascii=False)

        proc = subprocess.run(
            args,
            input=payload,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        if proc.returncode != 0:
            raise DetectorError(
                "Model command failed "
                f"(exit={proc.returncode}): {proc.stderr.strip() or 'no stderr'}"
            )

        try:
            model_output = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise DetectorError(
                "Model command must return JSON. "
                f"Got: {proc.stdout[:200]!r}"
            ) from exc

        entities_raw: Any
        if isinstance(model_output, dict):
            entities_raw = model_output.get("entities", [])
        elif isinstance(model_output, list):
            entities_raw = model_output
        else:
            raise DetectorError("Model output must be a JSON object or list.")

        if not isinstance(entities_raw, list):
            raise DetectorError("Model output field 'entities' must be a list.")

        entities = []
        for item in entities_raw:
            if not isinstance(item, dict):
                continue
            normalized = _normalize_entity(item, text)
            if normalized is not None:
                entities.append(normalized)

        return sorted(entities, key=lambda e: (e.start, e.end))


@dataclass
class HeuristicDetector(BaseDetector):
    # This fallback is intentionally conservative and mainly useful for bootstrapping.
    person_pattern: re.Pattern[str] = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
    company_pattern: re.Pattern[str] = re.compile(
        r"\b(?:[A-Z][\w&.-]*\s+){0,3}[A-Z][\w&.-]*\s(?:Inc|LLC|Ltd|Corporation|Corp|GmbH|s\.r\.o\.)\b"
    )
    address_pattern: re.Pattern[str] = re.compile(
        r"\b\d{1,5}\s+[A-Z][A-Za-z0-9.'-]*(?:\s+[A-Z][A-Za-z0-9.'-]*){0,5}\s(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b"
    )
    email_pattern: re.Pattern[str] = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    phone_pattern: re.Pattern[str] = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")

    def detect(self, text: str) -> list[EntitySpan]:
        entities: list[EntitySpan] = []
        entities.extend(_from_pattern(self.person_pattern, text, "PERSON", 0.65))
        entities.extend(_from_pattern(self.company_pattern, text, "COMPANY", 0.85))
        entities.extend(_from_pattern(self.address_pattern, text, "ADDRESS", 0.8))
        entities.extend(_from_pattern(self.email_pattern, text, "EMAIL", 0.95))
        entities.extend(_from_pattern(self.phone_pattern, text, "PHONE", 0.9))
        return sorted(entities, key=lambda e: (e.start, e.end))


_DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class GlinerDetector(BaseDetector):
    def __init__(
        self,
        model_name: str = "urchade/gliner_medium-v2.1",
        threshold: float = 0.5,
        models_dir: Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        try:
            from gliner import GLiNER
        except ModuleNotFoundError as exc:
            raise DetectorError(
                "Missing dependency 'gliner'. Install it with: pip install gliner"
            ) from exc

        local_dir = (models_dir or _DEFAULT_MODELS_DIR) / model_name.replace("/", "--")
        if (local_dir / "gliner_config.json").exists():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._model = GLiNER.from_pretrained(str(local_dir))
        else:
            local_dir.mkdir(parents=True, exist_ok=True)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._model = GLiNER.from_pretrained(model_name)
                self._model.save_pretrained(str(local_dir))
            typer_echo = None
            try:
                import typer
                typer_echo = typer.echo
            except ImportError:
                pass
            if typer_echo:
                typer_echo(f"Model saved to {local_dir}")

    _email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    _phone_re = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")

    def detect(self, text: str) -> list[EntitySpan]:
        if not text.strip():
            return []

        gliner_labels = list(GLINER_LABEL_MAP.values())
        raw_entities = self._model.predict_entities(text, gliner_labels, threshold=self.threshold)

        entities: list[EntitySpan] = []
        for item in raw_entities:
            label = _normalize_label(item.get("label", ""))
            if label is None:
                continue
            start = int(item["start"])
            end = int(item["end"])
            if start < 0 or end <= start or end > len(text):
                continue
            entities.append(EntitySpan(
                start=start,
                end=end,
                label=label,
                text=item.get("text", text[start:end]),
                confidence=float(item.get("score", 1.0)),
            ))

        # GLiNER is weak on structured patterns — supplement with regex for email/phone.
        entities.extend(_from_pattern(self._email_re, text, "EMAIL", 0.95))
        entities.extend(_from_pattern(self._phone_re, text, "PHONE", 0.90))

        return sorted(entities, key=lambda e: (e.start, e.end))


def available_detectors() -> list[str]:
    return ["gliner", "command", "heuristic"]


def build_detector(
    detector: str,
    model_cmd: str | None,
    gliner_model: str | None = None,
) -> BaseDetector:
    detector_name = detector.strip().lower()
    if detector_name == "heuristic":
        return HeuristicDetector()
    if detector_name == "command":
        if not model_cmd:
            raise DetectorError("--model-cmd is required when detector is 'command'.")
        return CommandDetector(command=model_cmd)
    if detector_name == "gliner":
        return GlinerDetector(model_name=gliner_model or "urchade/gliner_medium-v2.1")
    raise DetectorError(f"Unsupported detector type: {detector}")


def validate_command_detector(model_cmd: str) -> None:
    detector = CommandDetector(command=model_cmd)
    detector.detect("Jane Doe works at Acme LLC.")


def validate_gliner_detector(gliner_model: str | None = None) -> None:
    detector = GlinerDetector(model_name=gliner_model or "urchade/gliner_medium-v2.1")
    detector.detect("Jane Doe works at Acme LLC.")


def _from_pattern(pattern: re.Pattern[str], text: str, label: str, confidence: float) -> list[EntitySpan]:
    return [
        EntitySpan(
            start=match.start(),
            end=match.end(),
            label=label,
            text=match.group(0),
            confidence=confidence,
        )
        for match in pattern.finditer(text)
    ]


def _normalize_label(label: str) -> str | None:
    canonical = LABEL_ALIASES.get(label.strip().upper())
    if canonical in VALID_ENTITY_TYPES:
        return canonical
    return None


def _normalize_entity(entity: dict[str, Any], source_text: str) -> EntitySpan | None:
    try:
        start = int(entity["start"])
        end = int(entity["end"])
        label_raw = str(entity["label"])
    except (KeyError, TypeError, ValueError):
        return None

    if start < 0 or end <= start or end > len(source_text):
        return None

    label = _normalize_label(label_raw)
    if label is None:
        return None

    confidence = float(entity.get("confidence", 1.0))
    text = str(entity.get("text", source_text[start:end]))

    return EntitySpan(start=start, end=end, label=label, text=text, confidence=confidence)
