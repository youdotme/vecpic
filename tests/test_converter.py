"""Tests for converter.py with mocked vtracer."""

import sys
from unittest.mock import MagicMock

import pytest

from vecpic.config import VtracerConfig
from vecpic.converter import convert_image
from vecpic.errors import ConversionFailedError, VtracerNotInstalledError


@pytest.fixture
def mock_vtracer(monkeypatch):
    mock = MagicMock()
    mock.convert_raw_image_to_svg.return_value = (
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100">\n'
        '<path d="M10 10 L90 90"/>\n'
        "</svg>\n"
    )
    monkeypatch.setitem(sys.modules, "vtracer", mock)
    return mock


def test_vtracer_not_installed(monkeypatch, rgb_image, tmp_path):
    monkeypatch.setitem(sys.modules, "vtracer", None)
    out = tmp_path / "out.svg"
    with pytest.raises(VtracerNotInstalledError):
        convert_image(rgb_image, out, VtracerConfig())


def test_convert_image_calls_vtracer(mock_vtracer, rgb_image, tmp_path):
    out = tmp_path / "out.svg"
    convert_image(rgb_image, out, VtracerConfig())
    mock_vtracer.convert_raw_image_to_svg.assert_called_once()
    assert out.exists()


def test_convert_image_writes_valid_svg(mock_vtracer, rgb_image, tmp_path):
    out = tmp_path / "out.svg"
    convert_image(rgb_image, out, VtracerConfig())
    content = out.read_text()
    assert "svg" in content
    assert "<path" in content


def test_convert_image_passes_config(mock_vtracer, rgb_image, tmp_path):
    out = tmp_path / "out.svg"
    config = VtracerConfig(
        colormode="bw",
        mode="polygon",
        filter_speckle=8,
        path_precision=5,
    )
    convert_image(rgb_image, out, config)
    args = mock_vtracer.convert_raw_image_to_svg.call_args
    assert args is not None
    assert args[0][2] == "bw"
    assert args[0][4] == "polygon"
    assert args[0][5] == 8
    assert args[0][12] == 5


def test_convert_image_wraps_vtracer_error(mock_vtracer, rgb_image, tmp_path):
    mock_vtracer.convert_raw_image_to_svg.side_effect = RuntimeError("vtracer crash")
    out = tmp_path / "out.svg"
    with pytest.raises(ConversionFailedError, match="vtracer crash"):
        convert_image(rgb_image, out, VtracerConfig())


def test_convert_image_handles_rgba(mock_vtracer, rgba_image, tmp_path):
    out = tmp_path / "out.svg"
    convert_image(rgba_image, out, VtracerConfig())
    mock_vtracer.convert_raw_image_to_svg.assert_called_once()
    assert out.exists()


def test_convert_image_presets_are_passed(mock_vtracer, rgb_image, tmp_path):
    from vecpic.config import PRESETS

    configs = [
        PRESETS["bw"],
        PRESETS["poster"],
        PRESETS["photo"],
    ]
    for config in configs:
        mock_vtracer.reset_mock()
        out = tmp_path / f"out_{config.colormode}.svg"
        convert_image(rgb_image, out, config)
        args = mock_vtracer.convert_raw_image_to_svg.call_args
        assert args is not None
        assert args[0][2] == config.colormode
