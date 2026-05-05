"""Command-line interface for vecpic."""

import argparse
import logging
import sys

from .config import PRESETS, QUALITY_LEVELS
from .errors import VecpicError
from .pipeline import SUPPORTED_OUTPUT_FORMATS, convert

logger = logging.getLogger("vecpic")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from .gui import main as gui_main

        gui_main()
        return

    if args.input is None:
        parser.error("the following arguments are required: -i/--input (or use --gui)")

    _configure_logging(args)

    try:
        output = convert(
            input_path=args.input,
            output_path=args.output,
            preset=args.preset,
            quality=args.quality,
            output_format=args.format,
            export_backend=args.export_backend,
            max_size=args.max_size,
            flatten_bg=args.flatten_bg,
            keep_svg=args.keep_svg,
            colormode=args.colormode,
            hierarchical=args.hierarchical,
            mode=args.mode,
            filter_speckle=args.filter_speckle,
            color_precision=args.color_precision,
            layer_difference=args.layer_difference,
            corner_threshold=args.corner_threshold,
            length_threshold=args.length_threshold,
            max_iterations=args.max_iterations,
            splice_threshold=args.splice_threshold,
            path_precision=args.path_precision,
        )
        logger.info("conversion successful: %s -> %s", args.input, output)
    except VecpicError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.error("interrupted by user")
        sys.exit(130)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vecpic",
        description="Convert raster images to SVG vector graphics using vtracer.",
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        default=False,
        help="launch the graphical user interface",
    )
    parser.add_argument(
        "-i", "--input",
        default=None,
        help="path to input raster image (required for CLI mode)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="output file path (default: input_name.svg)",
    )
    parser.add_argument(
        "--format",
        dest="format",
        default=None,
        choices=sorted(SUPPORTED_OUTPUT_FORMATS),
        help="output format (svg, pdf, eps). Inferred from --output extension if omitted.",
    )
    parser.add_argument(
        "--export-backend",
        default="auto",
        choices=["auto", "cairosvg", "inkscape", "rsvg"],
        help="backend for PDF/EPS export (default: auto)",
    )
    parser.add_argument(
        "--preset",
        default=None,
        choices=sorted(PRESETS),
        help="use a preset configuration (bw, poster, photo)",
    )
    parser.add_argument(
        "--quality",
        default=None,
        choices=sorted(QUALITY_LEVELS),
        help="quality level (low, medium, high, extreme)",
    )
    parser.add_argument(
        "--colormode",
        default=None,
        choices=["color", "bw"],
        help="colormode: color or bw (default: color)",
    )
    parser.add_argument(
        "--hierarchical",
        default=None,
        choices=["stacked", "cutout"],
        help="hierarchical clustering: stacked or cutout (default: stacked)",
    )
    parser.add_argument(
        "--mode",
        default=None,
        choices=["spline", "polygon", "pixel"],
        help="curve fitting mode (default: spline)",
    )
    parser.add_argument(
        "--filter-speckle",
        type=int,
        default=None,
        help="discard patches smaller than N px (default: 4)",
    )
    parser.add_argument(
        "--color-precision",
        type=int,
        default=None,
        help="significant bits per RGB channel (default: 6)",
    )
    parser.add_argument(
        "--layer-difference",
        type=int,
        default=None,
        help="colour difference between gradient layers (default: 16)",
    )
    parser.add_argument(
        "--corner-threshold",
        type=int,
        default=None,
        help="minimum angle (degrees) to be considered a corner (default: 60)",
    )
    parser.add_argument(
        "--length-threshold",
        type=float,
        default=None,
        help="iterate subdivide until segments shorter than this (default: 4.0)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="maximum number of iterations (default: 10)",
    )
    parser.add_argument(
        "--splice-threshold",
        type=int,
        default=None,
        help="minimum angle to splice a spline (default: 45)",
    )
    parser.add_argument(
        "--path-precision",
        type=int,
        default=None,
        help="decimal places in path strings (default: 3)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=None,
        help="scale longest edge to at most N pixels",
    )
    parser.add_argument(
        "--flatten-bg",
        default=None,
        help="composite alpha onto this background colour (e.g. '#ffffff' or 'white')",
    )
    parser.add_argument(
        "--keep-svg",
        action="store_true",
        default=False,
        help="keep intermediate SVG when exporting to PDF/EPS",
    )
    parser.add_argument(
        "-v",
        action="store_const",
        dest="verbosity",
        const="INFO",
        default="WARNING",
        help="verbose output (INFO)",
    )
    parser.add_argument(
        "-vv",
        action="store_const",
        dest="verbosity",
        const="DEBUG",
        help="very verbose output (DEBUG)",
    )
    parser.add_argument(
        "-q",
        action="store_const",
        dest="verbosity",
        const="ERROR",
        help="quiet, only errors",
    )

    return parser


def _configure_logging(args: argparse.Namespace) -> None:
    level = getattr(logging, args.verbosity, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
