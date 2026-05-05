"""Core conversion logic that calls vtracer to generate intermediate SVG."""

import io
import logging
from pathlib import Path

from PIL import Image

from .config import VtracerConfig
from .errors import ConversionFailedError, VtracerNotInstalledError

logger = logging.getLogger(__name__)


def convert_image(
    image: Image.Image,
    output_path: str | Path,
    config: VtracerConfig,
) -> None:
    """Convert a Pillow Image to an intermediate SVG file using vtracer.

    Encodes the preprocessed image as PNG bytes and calls vtracer's
    raw-image API, which returns an SVG string. This ensures all Pillow
    preprocessing (EXIF, colour space, alpha, scaling) takes effect.

    The SVG is written to *output_path*.

    Raises:
        VtracerNotInstalledError: vtracer cannot be imported.
        ConversionFailedError: vtracer conversion raised an error.
    """
    try:
        import vtracer  # noqa: F811
    except ImportError as exc:
        raise VtracerNotInstalledError(
            "vtracer is not installed. Install it with: pip install vtracer"
        ) from exc

    output_path = Path(output_path)
    config_dict = config.to_dict()

    params = {
        "colormode": config_dict["colormode"],
        "hierarchical": config_dict["hierarchical"],
        "mode": config_dict["mode"],
        "filter_speckle": config_dict["filter_speckle"],
        "color_precision": config_dict["color_precision"],
        "layer_difference": config_dict["layer_difference"],
        "corner_threshold": config_dict["corner_threshold"],
        "length_threshold": config_dict["length_threshold"],
        "max_iterations": config_dict["max_iterations"],
        "splice_threshold": config_dict["splice_threshold"],
        "path_precision": config_dict["path_precision"],
    }

    logger.debug("vtracer config: %s", params)

    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except Exception as exc:
        raise ConversionFailedError(
            f"failed to encode image for vtracer: {exc}"
        ) from exc

    try:
        svg_string = vtracer.convert_raw_image_to_svg(
            png_bytes,
            "png",
            params["colormode"],
            params["hierarchical"],
            params["mode"],
            params["filter_speckle"],
            params["color_precision"],
            params["layer_difference"],
            params["corner_threshold"],
            params["length_threshold"],
            params["max_iterations"],
            params["splice_threshold"],
            params["path_precision"],
        )
    except Exception as exc:
        raise ConversionFailedError(
            f"vtracer conversion failed: {exc}"
        ) from exc

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(svg_string, encoding="utf-8")
    except OSError as exc:
        raise ConversionFailedError(
            f"failed to write SVG to {output_path}: {exc}"
        ) from exc
