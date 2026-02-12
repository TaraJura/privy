from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .anonymizer import AnonymizationError, anonymize_docx, deanonymize_docx
from .detector import DetectorError, available_detectors, build_detector, validate_command_detector, validate_gliner_detector

app = typer.Typer(help="Local AI CLI for reversible DOCX anonymization.")
models_app = typer.Typer(help="Inspect local detector backends.")
app.add_typer(models_app, name="models")


def _resolve_map_path(map_path: Optional[Path], output_path: Path) -> Path:
    if map_path is not None:
        return map_path
    return output_path.with_suffix(output_path.suffix + ".map.json")


@app.command("anonymize")
def anonymize_command(
    input_docx: Path = typer.Argument(..., exists=True, readable=True, help="Source .docx file."),
    output_docx: Path = typer.Option(..., "-o", "--output", help="Target anonymized .docx."),
    map_path: Optional[Path] = typer.Option(
        None,
        "--map",
        help="Mapping file path. Defaults to <output>.map.json",
    ),
    detector: str = typer.Option(
        "gliner",
        "--detector",
        help="Detector backend: gliner, command, or heuristic.",
    ),
    model_cmd: Optional[str] = typer.Option(
        None,
        "--model-cmd",
        envvar="PRIVY_MODEL_CMD",
        help="Local model command returning JSON entities for a text payload.",
    ),
    gliner_model: Optional[str] = typer.Option(
        None,
        "--gliner-model",
        envvar="PRIVY_GLINER_MODEL",
        help="GLiNER model name or path. Defaults to urchade/gliner_medium-v2.1.",
    ),
    entity_type: list[str] = typer.Option(
        ["PERSON", "COMPANY", "ADDRESS", "EMAIL", "PHONE", "DOC_ID", "NATIONAL_ID"],
        "--entity-type",
        "-e",
        help="Entity types to replace. Defaults to all. Repeat option to narrow.",
    ),
    min_confidence: float = typer.Option(0.5, "--min-confidence", min=0.0, max=1.0),
    report_path: Optional[Path] = typer.Option(None, "--report", help="Optional JSON processing report."),
) -> None:
    if input_docx.suffix.lower() != ".docx":
        typer.echo("Only .docx input is currently supported.", err=True)
        raise typer.Exit(1)

    if output_docx.suffix.lower() != ".docx":
        typer.echo("Output path must use .docx extension.", err=True)
        raise typer.Exit(1)

    resolved_map_path = _resolve_map_path(map_path, output_docx)

    try:
        detector_impl = build_detector(detector=detector, model_cmd=model_cmd, gliner_model=gliner_model)
        report = anonymize_docx(
            input_path=input_docx,
            output_path=output_docx,
            map_path=resolved_map_path,
            detector=detector_impl,
            entity_types=entity_type,
            min_confidence=min_confidence,
            report_path=report_path,
        )
    except (DetectorError, AnonymizationError, OSError, ValueError) as exc:
        typer.echo(f"Anonymization failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Anonymized document: {output_docx}")
    typer.echo(f"Mapping: {resolved_map_path}")
    typer.echo(
        "Summary: "
        f"paragraphs={report.paragraphs_scanned}, "
        f"entities={report.entities_detected}, "
        f"run_changes={report.replacements_applied}"
    )


@app.command("deanonymize")
def deanonymize_command(
    input_docx: Path = typer.Argument(..., exists=True, readable=True, help="Anonymized .docx file."),
    output_docx: Path = typer.Option(..., "-o", "--output", help="Target restored .docx file."),
    map_path: Path = typer.Option(..., "--map", exists=True, readable=True, help="Mapping file path."),
    report_path: Optional[Path] = typer.Option(None, "--report", help="Optional JSON processing report."),
) -> None:
    if input_docx.suffix.lower() != ".docx":
        typer.echo("Only .docx input is currently supported.", err=True)
        raise typer.Exit(1)

    if output_docx.suffix.lower() != ".docx":
        typer.echo("Output path must use .docx extension.", err=True)
        raise typer.Exit(1)

    try:
        report = deanonymize_docx(
            input_path=input_docx,
            output_path=output_docx,
            map_path=map_path,
            report_path=report_path,
        )
    except (AnonymizationError, OSError, ValueError) as exc:
        typer.echo(f"Deanonymization failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Restored document: {output_docx}")
    typer.echo(
        "Summary: "
        f"paragraphs={report.paragraphs_scanned}, "
        f"placeholders={report.entities_detected}, "
        f"run_changes={report.replacements_applied}"
    )


@models_app.command("list")
def list_models() -> None:
    for name in available_detectors():
        typer.echo(name)


@models_app.command("validate")
def validate_models(
    detector: str = typer.Option("gliner", "--detector", help="Detector backend to validate."),
    model_cmd: Optional[str] = typer.Option(
        None,
        "--model-cmd",
        envvar="PRIVY_MODEL_CMD",
        help="Local model command used for --detector command.",
    ),
    gliner_model: Optional[str] = typer.Option(
        None,
        "--gliner-model",
        envvar="PRIVY_GLINER_MODEL",
        help="GLiNER model name or path.",
    ),
) -> None:
    selected = detector.strip().lower()
    if selected == "heuristic":
        typer.echo("heuristic detector is available")
        return

    if selected == "gliner":
        try:
            validate_gliner_detector(gliner_model)
        except DetectorError as exc:
            typer.echo(f"gliner detector validation failed: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo("gliner detector is available")
        return

    if selected == "command":
        if not model_cmd:
            typer.echo("--model-cmd (or PRIVY_MODEL_CMD) is required for command detector.", err=True)
            raise typer.Exit(1)
        try:
            validate_command_detector(model_cmd)
        except DetectorError as exc:
            typer.echo(f"command detector validation failed: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo("command detector is available")
        return

    typer.echo(f"Unsupported detector: {detector}", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
