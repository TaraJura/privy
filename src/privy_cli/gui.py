"""pywebview GUI for privy-cli."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import threading
from pathlib import Path

import webview  # type: ignore[import-untyped]

from .anonymizer import AnonymizationError, anonymize_docx, deanonymize_docx
from .detector import BaseDetector, DetectorError, build_detector
from .gui_html import HTML
from .types import VALID_ENTITY_TYPES


class Api:
    """Exposed to JavaScript as ``window.pywebview.api.*``."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._selected_file: str | None = None
        self._detector: BaseDetector | None = None
        self._detector_lock = threading.Lock()

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    # ── File selection ──────────────────────────────────────────────────

    def open_file_dialog(self) -> dict:
        """Open native file dialog, return selected path."""
        assert self._window is not None
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            file_types=("Word Documents (*.docx)",),
        )
        if result and len(result) > 0:
            path = str(result[0])
            if not path.lower().endswith(".docx"):
                return {"error": "Please select a .docx file."}
            self._selected_file = path
            return {"path": path, "name": Path(path).name}
        return {"cancelled": True}

    def select_file_via_drop(self, file_path: str) -> dict:
        """Called when user drops a file on the drop zone."""
        if not file_path.lower().endswith(".docx"):
            return {"error": "Please drop a .docx file."}
        self._selected_file = file_path
        return {"path": file_path, "name": Path(file_path).name}

    # ── Core operations ─────────────────────────────────────────────────

    def anonymize(self) -> dict:
        """Run anonymization with default settings."""
        if not self._selected_file:
            return {"error": "No file selected."}

        input_path = Path(self._selected_file)
        if not input_path.exists():
            return {"error": f"File not found: {input_path}"}

        output_path = _unique_path(input_path.parent / f"{input_path.stem}_anonymized.docx")
        map_path = output_path.with_suffix(output_path.suffix + ".map.json")

        self._update_status("Loading AI model...")

        try:
            detector = self._get_or_build_detector()
        except DetectorError as exc:
            return {"error": f"Model error: {exc}"}

        self._update_status("Anonymizing document...")

        try:
            report = anonymize_docx(
                input_path=input_path,
                output_path=output_path,
                map_path=map_path,
                detector=detector,
                entity_types=list(VALID_ENTITY_TYPES),
                min_confidence=0.5,
            )
        except (AnonymizationError, OSError, ValueError) as exc:
            return {"error": str(exc)}

        return {
            "success": True,
            "output_path": str(output_path),
            "map_path": str(map_path),
            "report": report.to_dict(),
        }

    def deanonymize(self) -> dict:
        """Run deanonymization, auto-detecting the map file."""
        if not self._selected_file:
            return {"error": "No file selected."}

        input_path = Path(self._selected_file)
        if not input_path.exists():
            return {"error": f"File not found: {input_path}"}

        # Auto-detect map file next to the input
        map_path = input_path.with_suffix(input_path.suffix + ".map.json")
        if not map_path.exists():
            # Try to let user pick one
            assert self._window is not None
            result = self._window.create_file_dialog(
                webview.FileDialog.OPEN,
                file_types=("Mapping files (*.json)",),
            )
            if result and len(result) > 0:
                map_path = Path(str(result[0]))
            else:
                return {"error": "No mapping file found. Place the .map.json next to the input file, or select it manually."}

        output_path = _unique_path(input_path.parent / f"{input_path.stem}_restored.docx")

        self._update_status("Restoring document...")

        try:
            report = deanonymize_docx(
                input_path=input_path,
                output_path=output_path,
                map_path=map_path,
            )
        except (AnonymizationError, OSError, ValueError) as exc:
            return {"error": str(exc)}

        return {
            "success": True,
            "output_path": str(output_path),
            "report": report.to_dict(),
        }

    def reveal_in_finder(self, path: str) -> None:
        """Open the containing folder in Finder/Explorer."""
        p = Path(path)
        if not p.exists():
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
        elif platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", str(p)], check=False)

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_or_build_detector(self) -> BaseDetector:
        with self._detector_lock:
            if self._detector is None:
                self._detector = build_detector(
                    detector="gliner",
                    model_cmd=None,
                    gliner_model=None,
                )
            return self._detector

    def _update_status(self, message: str) -> None:
        if self._window:
            self._window.evaluate_js(
                f"window.__privyUpdateStatus({json.dumps(message)})"
            )


def _unique_path(path: Path) -> Path:
    """Return *path* if it doesn't exist, otherwise append ``_2``, ``_3``, etc."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 2
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def launch_gui() -> None:
    """Create and start the pywebview window."""
    api = Api()
    window = webview.create_window(
        title="privy",
        html=HTML,
        js_api=api,
        width=560,
        height=640,
        min_size=(460, 520),
        resizable=True,
        text_select=False,
        background_color="#ffffff",
    )
    api.set_window(window)
    webview.start(debug=("--debug" in sys.argv))
