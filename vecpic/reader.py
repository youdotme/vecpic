"""Image reading and preprocessing based on Pillow."""

import logging
import os
from pathlib import Path

from PIL import Image, ImageOps

from .errors import (
    EmptyFileError,
    ImageTooLargeError,
    InputFileNotFoundError,
    InvalidImageError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP"}

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".bmp",
    ".dib",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
}

MAX_PIXELS_WARNING = 100_000_000
MAX_PIXELS_HARD_LIMIT = 300_000_000

Image.MAX_IMAGE_PIXELS = MAX_PIXELS_HARD_LIMIT


def detect_format(path: str | Path) -> str:
    """Detect the true image format from file headers using Pillow.

    Returns the Pillow format string (e.g. "PNG", "JPEG", "GIF", "TIFF", "WEBP").

    Raises:
        InputFileNotFoundError: File does not exist.
        EmptyFileError: File is empty (0 bytes).
        InvalidImageError: Pillow cannot identify the image format.
    """
    path = Path(path)

    if not path.exists():
        raise InputFileNotFoundError(f"file not found: {path}")
    if not path.is_file():
        raise InputFileNotFoundError(f"path is not a file: {path}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise EmptyFileError(f"file is empty: {path}")

    try:
        with Image.open(path) as img:
            fmt = img.format
    except Exception as exc:
        raise InvalidImageError(
            f"cannot read image, file may be corrupt or format unsupported: {path}"
        ) from exc

    if fmt is None:
        raise InvalidImageError(
            f"cannot identify image format: {path}"
        )

    return fmt


def read_image(
    path: str | Path,
    *,
    max_size: int | None = None,
    flatten_bg: str | None = None,
) -> Image.Image:
    """Open, validate, and normalize an image for conversion.

    Processing steps:
    1. Check file existence and non-empty
    2. Detect true format via Pillow file headers
    3. Validate format is supported
    4. Apply EXIF Orientation correction
    5. For multi-frame GIF/WebP/TIFF, default to first frame
    6. Convert CMYK / P / L / LA modes to RGB or RGBA
    7. Preserve alpha by default
    8. If flatten_bg is set, composite alpha onto the specified background colour
    9. If max_size is set, scale longest edge via thumbnail()
    10. Return a Pillow Image

    Raises:
        InputFileNotFoundError: File does not exist or is not a file.
        EmptyFileError: File is empty.
        InvalidImageError: Pillow cannot open or identify the image.
        UnsupportedFormatError: True format is not in SUPPORTED_FORMATS.
        ImageTooLargeError: Image exceeds the hard pixel limit.
    """
    path = Path(path)

    if not path.exists():
        raise InputFileNotFoundError(f"file not found: {path}")
    if not path.is_file():
        raise InputFileNotFoundError(f"path is not a file: {path}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise EmptyFileError(f"file is empty: {path}")

    try:
        img = Image.open(path)
    except Exception as exc:
        raise InvalidImageError(
            f"cannot open image, file may be corrupt: {path}"
        ) from exc

    fmt = img.format
    if fmt is None:
        img.close()
        raise InvalidImageError(f"cannot identify image format: {path}")

    ext = path.suffix.lower()

    if fmt not in SUPPORTED_FORMATS:
        img.close()
        raise UnsupportedFormatError(
            f"unsupported image format: {fmt}. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    if ext not in SUPPORTED_EXTENSIONS and ext:
        logger.warning(
            "unusual file extension %r but true format is %s, continuing",
            ext,
            fmt,
        )

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if fmt in ("GIF", "TIFF", "WEBP"):
        try:
            img.seek(0)
        except EOFError:
            pass
        else:
            logger.info("multi-frame image detected, using first frame")

    img = _normalize_mode(img)

    img = _convert_to_srgb(img)

    if img.mode == "RGBA":
        logger.debug("alpha channel detected, preserving alpha")
        if flatten_bg is not None:
            logger.info("compositing alpha onto background colour: %s", flatten_bg)
            img = _flatten_alpha(img, flatten_bg)

    _check_size(img, max_size)

    return img


def _normalize_mode(img: Image.Image) -> Image.Image:
    """Convert image mode to RGB or RGBA as appropriate."""
    mode = img.mode

    if mode in ("RGB", "RGBA"):
        return img

    if mode == "LA":
        logger.info("converting LA -> RGBA")
        return img.convert("RGBA")

    if mode == "L":
        logger.info("converting L -> RGB")
        return img.convert("RGB")

    if mode == "CMYK":
        logger.info("converting CMYK -> RGB")
        return img.convert("RGB")

    if mode == "P":
        if "transparency" in img.info:
            logger.info("converting P -> RGBA (transparency info present)")
            converted = img.convert("RGBA")
            img.close()
            return converted
        logger.info("converting P -> RGB")
        converted = img.convert("RGB")
        img.close()
        return converted

    try:
        logger.info("converting %s -> RGBA", mode)
        return img.convert("RGBA")
    except Exception:
        try:
            logger.info("converting %s -> RGB", mode)
            return img.convert("RGB")
        except Exception as exc:
            img.close()
            raise InvalidImageError(
                f"cannot normalize image mode {mode!r} to RGB or RGBA"
            ) from exc


def _flatten_alpha(img: Image.Image, bg_colour: str) -> Image.Image:
    """Composite RGBA image onto a solid background colour."""
    bg = Image.new("RGBA", img.size, bg_colour)
    flattened = Image.alpha_composite(bg, img)
    img.close()
    return flattened


def _convert_to_srgb(img: Image.Image) -> Image.Image:
    """Convert image to sRGB colour space if it has an embedded ICC profile.

    Without this step, images with non-sRGB profiles (Display P3, Adobe RGB)
    produce shifted colours: Pillow reads raw pixel values without applying
    the profile, but downstream consumers (SVG, web) assume sRGB.
    """
    icc = img.info.get("icc_profile")
    if not icc:
        return img

    try:
        import io as _io

        from PIL import ImageCms

        srgb = ImageCms.createProfile("sRGB")
        output_mode = img.mode if img.mode in ("RGB", "RGBA") else "RGBA"
        converted = ImageCms.profileToProfile(
            img, _io.BytesIO(icc), srgb, outputMode=output_mode
        )
        converted.info.pop("icc_profile", None)
        img.close()
        logger.info("converted ICC profile -> sRGB")
        return converted
    except Exception as exc:
        logger.debug("ICC profile conversion skipped: %s", exc)
        return img


def _check_size(img: Image.Image, max_size: int | None) -> None:
    """Check pixel dimensions and optionally scale down."""
    w, h = img.size
    pixels = w * h
    limit = MAX_PIXELS_HARD_LIMIT
    warn_limit = MAX_PIXELS_WARNING

    if pixels > limit:
        img.close()
        raise ImageTooLargeError(
            f"image too large: {w}x{h} ({pixels} px). "
            f"Hard limit is {limit} px. "
            "Use a smaller image or --max-size."
        )

    if max_size is not None:
        longest = max(w, h)
        if longest > max_size:
            logger.info("scaling image: %dx%d -> ", w, h)
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            new_w, new_h = img.size
            logger.info("%dx%d", new_w, new_h)
    else:
        longest = max(w, h)
        if longest > 10000:
            logger.warning(
                "input image is very large: %dx%d, conversion may be slow; "
                "consider using --max-size",
                w,
                h,
            )
