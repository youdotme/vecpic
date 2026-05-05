"""CLI integration tests."""

import shutil
import subprocess
import sys

import pytest


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "vecpic", *args],
        capture_output=True,
        text=True,
    )


def test_help():
    result = _run_cli("-h")
    assert result.returncode == 0
    assert "usage" in result.stdout


def test_no_input():
    result = _run_cli()
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "required" in result.stdout.lower()


def test_gui_flag_imports_cleanly():
    """--gui should import without crashing when tkinter is available."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        pytest.skip("tkinter not available")

    from vecpic.gui import main as _  # noqa: F401


def test_missing_input_file():
    result = _run_cli("-i", "/nonexistent.png")
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_convert_png_to_svg(temp_png):
    out = temp_png.replace(".png", ".svg")
    result = _run_cli("-i", temp_png, "-o", out, "-v")
    assert result.returncode == 0
    assert "conversion successful" in result.stderr.lower()


def test_convert_png_to_svg_default_output(temp_png):
    result = _run_cli("-i", temp_png, "-v")
    assert result.returncode == 0


def test_unsupported_format(tmp_path):
    path = tmp_path / "test.tga"
    from PIL import Image

    Image.new("RGB", (10, 10)).save(path, format="TGA")
    result = _run_cli("-i", str(path))
    assert result.returncode == 1
    assert "unsupported" in result.stderr.lower()


def test_format_conflict(temp_png, tmp_path):
    out = tmp_path / "out.svg"
    result = _run_cli("-i", temp_png, "-o", str(out), "--format", "pdf")
    assert result.returncode == 1
    assert "conflict" in result.stderr.lower()


def test_preset(temp_png):
    result = _run_cli("-i", temp_png, "--preset", "bw", "-v")
    assert result.returncode == 0


def test_verbosity_quiet(temp_png):
    result = _run_cli("-i", temp_png, "-q")
    assert result.returncode == 0
    assert result.stderr == ""


def test_flatten_bg(temp_transparent_png):
    out = temp_transparent_png.replace(".png", ".svg")
    result = _run_cli("-i", temp_transparent_png, "-o", out, "--flatten-bg", "white", "-v")
    assert result.returncode == 0


def test_max_size(temp_png):
    result = _run_cli("-i", temp_png, "--max-size", "50", "-v")
    assert result.returncode == 0


def test_invalid_preset(temp_png):
    result = _run_cli("-i", temp_png, "--preset", "invalid")
    assert result.returncode != 0


def test_invalid_filter_speckle(temp_png):
    result = _run_cli("-i", temp_png, "--filter-speckle", "-1")
    assert result.returncode != 0


def test_keep_svg_flag(temp_png, tmp_path):
    import shutil
    has_backend = (
        shutil.which("inkscape") or shutil.which("rsvg-convert")
    )
    if not has_backend:
        try:
            import cairosvg  # noqa: F401
        except ImportError:
            pytest.skip("no PDF export backend available")

    pdf_out = tmp_path / "out.pdf"
    result = _run_cli(
        "-i", temp_png, "-o", str(pdf_out), "--keep-svg", "-v"
    )
    assert result.returncode == 0
    svg_out = tmp_path / "out.svg"
    assert svg_out.exists()
