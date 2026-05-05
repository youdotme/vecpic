"""SVG validation, safe final output, and PDF/EPS export."""

import logging
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .errors import (
    ExportBackendMissingError,
    ExportFailedError,
    OutputPermissionError,
    SvgValidationError,
)

logger = logging.getLogger(__name__)

GRAPHIC_TAGS = {
    "path",
    "polygon",
    "polyline",
    "rect",
    "circle",
    "ellipse",
    "line",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_svg(path: str | Path) -> None:
    """Validate that a file is well-formed SVG with at least one graphic element.

    Checks:
    1. XML is parseable.
    2. Root element local name is 'svg'.
    3. Has viewBox or width+height attributes.
    4. Contains at least one known graphic element (recursive).

    Raises:
        SvgValidationError: Any validation check fails.
    """
    path = Path(path)

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise SvgValidationError(f"SVG is not valid XML: {exc}") from exc
    except FileNotFoundError:
        raise SvgValidationError(f"SVG file does not exist: {path}")

    root = tree.getroot()
    root_name = _local_name(root.tag)
    if root_name != "svg":
        raise SvgValidationError(
            f"root element is <{root_name}>, expected <svg>"
        )

    has_viewbox = "viewBox" in root.attrib
    has_width_height = "width" in root.attrib and "height" in root.attrib
    if not has_viewbox and not has_width_height:
        raise SvgValidationError(
            "SVG missing viewBox and width/height attributes"
        )

    if not _has_graphic_element(root):
        raise SvgValidationError("SVG contains no graphic elements")


def _has_graphic_element(element: ET.Element) -> bool:
    if _local_name(element.tag) in GRAPHIC_TAGS:
        return True
    for child in element:
        if _has_graphic_element(child):
            return True
    return False


def finalize_svg(
    tmp_svg_path: str | Path,
    output_path: str | Path,
    *,
    validate: bool = True,
) -> None:
    """Safely publish a temporary SVG as the final output file.

    1. Optionally validate the temporary SVG.
    2. Create output directory if needed.
    3. Atomically replace the target file via os.replace().

    Raises:
        SvgValidationError: validate is True and SVG is invalid.
        OutputPermissionError: Cannot write to the output path.
    """
    tmp_svg_path = Path(tmp_svg_path)
    output_path = Path(output_path)

    if validate:
        validate_svg(tmp_svg_path)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_svg_path, output_path)
    except PermissionError as exc:
        raise OutputPermissionError(f"no write permission: {output_path}") from exc
    except OSError as exc:
        raise OutputPermissionError(
            f"cannot write output file {output_path}: {exc}"
        ) from exc


def export_svg(
    svg_path: str | Path,
    output_path: str | Path,
    output_format: str,
    *,
    backend: str = "auto",
) -> None:
    """Export an SVG to PDF or EPS.

    The SVG file should already be validated by the caller.

    Args:
        svg_path: Path to the validated SVG file.
        output_path: Desired output file path.
        output_format: "pdf" or "eps".
        backend: "auto", "cairosvg", "inkscape", or "rsvg".

    Raises:
        ExportBackendMissingError: No backend is available.
        ExportFailedError: The chosen backend returned an error.
    """
    svg_path = Path(svg_path)
    output_path = Path(output_path)

    if output_format not in ("pdf", "eps"):
        raise ExportFailedError(f"unsupported export format: {output_format!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if backend == "auto":
        backends = _detect_backends(output_format)
        if not backends:
            raise ExportBackendMissingError(_MISSING_BACKEND_MSG)
        backend = backends[0]

    _export_with_backend(svg_path, output_path, output_format, backend)


_MISSING_BACKEND_MSG = (
    "Cannot export PDF/EPS: no available backend.\n\n"
    "Options:\n"
    "1. pip install vecpic[export]\n"
    "2. Install Inkscape and ensure 'inkscape' is in PATH\n"
    "3. Install librsvg and ensure 'rsvg-convert' is in PATH"
)


def _detect_backends(output_format: str) -> list[str]:
    available: list[str] = []
    if shutil.which("inkscape"):
        available.append("inkscape")
    if shutil.which("rsvg-convert"):
        available.append("rsvg")
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        pass
    else:
        available.append("cairosvg")
    return available


def _export_with_backend(
    svg_path: Path,
    output_path: Path,
    output_format: str,
    backend: str,
) -> None:
    if backend == "cairosvg":
        _export_cairosvg(svg_path, output_path, output_format)
    elif backend == "inkscape":
        _export_inkscape(svg_path, output_path, output_format)
    elif backend == "rsvg":
        _export_rsvg(svg_path, output_path, output_format)
    else:
        raise ExportBackendMissingError(
            f"unknown backend: {backend!r}. "
            "Supported: auto, cairosvg, inkscape, rsvg"
        )


def _export_cairosvg(
    svg_path: Path,
    output_path: Path,
    output_format: str,
) -> None:
    try:
        import cairosvg
    except ImportError:
        raise ExportBackendMissingError(
            "cairosvg is not installed. Install it with: pip install vecpic[export]"
        )

    try:
        if output_format == "pdf":
            cairosvg.svg2pdf(url=str(svg_path), write_to=str(output_path))
        elif output_format == "eps":
            cairosvg.svg2eps(url=str(svg_path), write_to=str(output_path), output=str(output_path))
    except Exception as exc:
        raise ExportFailedError(f"cairosvg export failed: {exc}") from exc


def _export_inkscape(
    svg_path: Path,
    output_path: Path,
    output_format: str,
) -> None:
    if output_format == "pdf":
        fmt_args = ["--export-type=pdf"]
    else:
        fmt_args = ["--export-type=eps"]

    cmd = [
        "inkscape",
        str(svg_path),
        f"--export-filename={output_path}",
        *fmt_args,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise ExportBackendMissingError("inkscape not found in PATH")
    except subprocess.CalledProcessError as exc:
        raise ExportFailedError(
            f"inkscape export failed: {exc.stderr.strip()}"
        ) from exc


def _export_rsvg(
    svg_path: Path,
    output_path: Path,
    output_format: str,
) -> None:
    cmd = [
        "rsvg-convert",
        "-f",
        output_format,
        "-o",
        str(output_path),
        str(svg_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise ExportBackendMissingError("rsvg-convert not found in PATH")
    except subprocess.CalledProcessError as exc:
        raise ExportFailedError(
            f"rsvg-convert export failed: {exc.stderr.strip()}"
        ) from exc
