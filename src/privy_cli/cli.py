from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .anonymizer import AnonymizationError, anonymize_docx, deanonymize_docx
from .detector import DetectorError, available_detectors, build_detector, validate_command_detector

app = typer.Typer(help="Local AI CLI for reversible DOCX anonymization.")
models_app = typer.Typer(help="Inspect local detector backends.")
app.add_typer(models_app, name="models")


def _resolve_map_path(map_path: Optional[Path], output_path: Path) -> Path:
    if map_path is not None:
        return map_path
    return output_path.with_suffix(output_path.suffix + ".map.enc.json")


@app.command("anonymize")
def anonymize_command(
    input_docx: Path = typer.Argument(..., exists=True, readable=True, help="Source .docx file."),
    output_docx: Path = typer.Option(..., "-o", "--output", help="Target anonymized .docx."),
    map_path: Optional[Path] = typer.Option(
        None,
        "--map",
        help="Encrypted reversible mapping path. Defaults to <output>.map.enc.json",
    ),
    map_password: str = typer.Option(
        ..., "--map-password", envvar="PRIVY_MAP_PASSWORD", hide_input=True, prompt=True,
        confirmation_prompt=True, help="Password used to encrypt mapping file."
    ),
    detector: str = typer.Option(
        "command",
        "--detector",
        help="Detector backend: command or heuristic.",
    ),
    model_cmd: Optional[str] = typer.Option(
        None,
        "--model-cmd",
        envvar="PRIVY_MODEL_CMD",
        help="Local model command returning JSON entities for a text payload.",
    ),
    entity_type: list[str] = typer.Option(
        ["PERSON", "COMPANY", "ADDRESS"],
        "--entity-type",
        "-e",
        help="Entity type to replace. Repeat option to include more.",
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
        detector_impl = build_detector(detector=detector, model_cmd=model_cmd)
        report = anonymize_docx(
            input_path=input_docx,
            output_path=output_docx,
            map_path=resolved_map_path,
            map_password=map_password,
            detector=detector_impl,
            entity_types=entity_type,
            min_confidence=min_confidence,
            report_path=report_path,
        )
    except (DetectorError, AnonymizationError, OSError, ValueError) as exc:
        typer.echo(f"Anonymization failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Anonymized document: {output_docx}")
    typer.echo(f"Encrypted mapping: {resolved_map_path}")
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
    map_path: Path = typer.Option(..., "--map", exists=True, readable=True, help="Encrypted mapping path."),
    map_password: str = typer.Option(
        ..., "--map-password", envvar="PRIVY_MAP_PASSWORD", hide_input=True, prompt=True,
        help="Password used to decrypt mapping file."
    ),
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
            map_password=map_password,
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
    detector: str = typer.Option("command", "--detector", help="Detector backend to validate."),
    model_cmd: Optional[str] = typer.Option(
        None,
        "--model-cmd",
        envvar="PRIVY_MODEL_CMD",
        help="Local model command used for --detector command.",
    ),
) -> None:
    selected = detector.strip().lower()
    if selected == "heuristic":
        typer.echo("heuristic detector is available")
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
