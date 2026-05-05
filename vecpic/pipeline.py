"""End-to-end conversion pipeline orchestration."""

import logging
import tempfile
from pathlib import Path

from .config import DEFAULT_QUALITY, PRESETS, QUALITY_LEVELS, VtracerConfig, ConfigError
from .converter import convert_image
from .errors import VecpicError
from .reader import read_image
from .writer import export_svg, finalize_svg, validate_svg

logger = logging.getLogger(__name__)

SUPPORTED_OUTPUT_FORMATS = {"svg", "pdf", "eps"}

_OUTPUT_EXT_TO_FORMAT = {
    ".svg": "svg",
    ".pdf": "pdf",
    ".eps": "eps",
}


def convert(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preset: str | None = None,
    quality: str | None = None,
    output_format: str | None = None,
    export_backend: str = "auto",
    max_size: int | None = None,
    flatten_bg: str | None = None,
    keep_svg: bool = False,
    colormode: str | None = None,
    hierarchical: str | None = None,
    mode: str | None = None,
    filter_speckle: int | None = None,
    color_precision: int | None = None,
    layer_difference: int | None = None,
    corner_threshold: int | None = None,
    length_threshold: float | None = None,
    max_iterations: int | None = None,
    splice_threshold: int | None = None,
    path_precision: int | None = None,
) -> str:
    """Convert a raster image to SVG/PDF/EPS vector graphics.

    Args:
        input_path: Path to the input raster image.
        output_path: Desired output path. If None, defaults to input_name.<fmt>.
        preset: One of "bw", "poster", "photo".
        quality: Quality level: "low", "medium", "high", or "extreme".
        output_format: "svg", "pdf", or "eps". Inferred from output_path suffix if omitted.
        export_backend: Backend for PDF/EPS export: "auto", "cairosvg", "inkscape", "rsvg".
        max_size: Scale longest edge to at most this many pixels.
        flatten_bg: Composite alpha channel onto this background colour.
        keep_svg: Keep intermediate SVG when exporting to PDF/EPS.
        colormode, hierarchical, mode, filter_speckle, color_precision,
        layer_difference, corner_threshold, length_threshold, max_iterations,
        splice_threshold, path_precision: vtracer configuration parameters.

    Returns:
        The path to the output file.

    Raises:
        VecpicError: Any error during the conversion pipeline.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise VecpicError(f"input file not found: {input_path}")
    if not input_path.is_file():
        raise VecpicError(f"input path is not a file: {input_path}")

    final_path, fmt = _resolve_output_path_and_format(input_path, output_path, output_format)

    quality_overrides: dict[str, object] = {}
    if quality is not None:
        if quality not in QUALITY_LEVELS:
            raise ConfigError(
                f"unknown quality: {quality!r}. "
                f"Supported: {', '.join(sorted(QUALITY_LEVELS))}"
            )
        quality_overrides = dict(QUALITY_LEVELS[quality])

    quality_max_size = quality_overrides.pop("max_size", None)
    if max_size is None:
        max_size = quality_max_size  # type: ignore[assignment]

    image = read_image(
        input_path,
        max_size=max_size,
        flatten_bg=flatten_bg,
    )

    config = _build_config(
        preset=preset,
        quality_overrides=quality_overrides,
        colormode=colormode,
        hierarchical=hierarchical,
        mode=mode,
        filter_speckle=filter_speckle,
        color_precision=color_precision,
        layer_difference=layer_difference,
        corner_threshold=corner_threshold,
        length_threshold=length_threshold,
        max_iterations=max_iterations,
        splice_threshold=splice_threshold,
        path_precision=path_precision,
    )

    output_dir = final_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=output_dir) as tmpdir:
        tmp_svg = Path(tmpdir) / "intermediate.svg"
        convert_image(image, tmp_svg, config)
        image.close()

        validate_svg(tmp_svg)

        if fmt == "svg":
            finalize_svg(tmp_svg, final_path, validate=False)
        else:
            export_svg(
                tmp_svg,
                final_path,
                fmt,
                backend=export_backend,
            )
            if keep_svg:
                svg_out = final_path.with_suffix(".svg")
                finalize_svg(tmp_svg, svg_out, validate=False)

    return str(final_path)


def _resolve_output_path_and_format(
    input_path: Path,
    output_path: Path | str | None,
    output_format: str | None,
) -> tuple[Path, str]:
    if output_path is not None:
        output_path = Path(output_path)
    user_ext: str | None = None
    if output_path is not None:
        user_ext = output_path.suffix.lower()

    fmt = _resolve_format(user_ext, output_format)

    if output_path is None:
        final = input_path.with_suffix(f".{fmt}")
    else:
        final = output_path

    return Path(final), fmt


def _resolve_format(user_ext: str | None, output_format: str | None) -> str:
    ext_fmt = _OUTPUT_EXT_TO_FORMAT.get(user_ext or "")

    if output_format is not None:
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ConfigError(
                f"unsupported output format: {output_format!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_OUTPUT_FORMATS))}"
            )
        if ext_fmt is not None and ext_fmt != output_format:
            raise ConfigError(
                f"output format {output_format!r} conflicts with "
                f"file extension {user_ext!r}"
            )
        return output_format

    if ext_fmt is not None:
        return ext_fmt

    if user_ext:
        raise ConfigError(
            f"unknown output file extension: {user_ext!r}. "
            f"Supported: {', '.join(sorted(_OUTPUT_EXT_TO_FORMAT))}"
        )

    return "svg"


_PRESET_PARAM_LIST = (
    "colormode",
    "hierarchical",
    "mode",
    "filter_speckle",
    "color_precision",
    "layer_difference",
    "corner_threshold",
    "length_threshold",
    "max_iterations",
    "splice_threshold",
    "path_precision",
)


def _build_config(
    preset: str | None = None,
    quality_overrides: dict[str, object] | None = None,
    **overrides: object,
) -> VtracerConfig:
    if preset is not None:
        if preset not in PRESETS:
            raise ConfigError(
                f"unknown preset: {preset!r}. "
                f"Supported: {', '.join(sorted(PRESETS))}"
            )
        config = PRESETS[preset]
    else:
        config = VtracerConfig()

    if quality_overrides:
        config = config.merged(**quality_overrides)

    return config.merged(**overrides)
