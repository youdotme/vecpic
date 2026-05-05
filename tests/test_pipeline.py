"""Tests for pipeline.py."""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vecpic.config import PRESETS
from vecpic.errors import ConfigError, VecpicError
from vecpic.pipeline import SUPPORTED_OUTPUT_FORMATS, convert

_VALID_SVG = (
    '<?xml version="1.0"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'viewBox="0 0 100 100">\n'
    '<path d="M10 10 L90 90"/>\n'
    "</svg>\n"
)


def _mock_convert_image(image, output_path, config):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(_VALID_SVG)


@pytest.fixture(autouse=True)
def _mock_modules(monkeypatch):
    mock_conv = MagicMock(side_effect=_mock_convert_image)
    monkeypatch.setattr("vecpic.pipeline.convert_image", mock_conv)

    mock_export = MagicMock()
    monkeypatch.setattr("vecpic.pipeline.export_svg", mock_export)


class TestPipelineSvg:
    def test_default_output_path(self, temp_png, _mock_modules):
        result = convert(temp_png)
        assert result.endswith(".svg")

    def test_explicit_output_path(self, temp_png, tmp_path, _mock_modules):
        out = tmp_path / "out.svg"
        result = convert(temp_png, output_path=out)
        assert str(out) == result

    def test_nonexistent_input(self):
        with pytest.raises(VecpicError, match="input file not found"):
            convert("/nonexistent.png")

    def test_output_format_inference(self, temp_png, tmp_path, _mock_modules):
        out = tmp_path / "out.pdf"
        result = convert(temp_png, output_path=out)
        assert result.endswith(".pdf")

    def test_format_conflict_raises(self, temp_png, tmp_path):
        out = tmp_path / "out.svg"
        with pytest.raises(ConfigError, match="conflict"):
            convert(temp_png, output_path=out, output_format="pdf")

    def test_unknown_extension_raises(self, temp_png, tmp_path):
        out = tmp_path / "out.xyz"
        with pytest.raises(ConfigError, match="unknown output file extension"):
            convert(temp_png, output_path=out)

    def test_invalid_format_raises(self, temp_png):
        with pytest.raises(ConfigError, match="unsupported output format"):
            convert(temp_png, output_format="invalid")

    def test_preset_invalid_raises(self, temp_png):
        with pytest.raises(ConfigError, match="unknown preset"):
            convert(temp_png, preset="invalid")


class TestPipelineParameters:
    def test_explicit_params_override_preset(self, temp_png, monkeypatch):
        mock_conv = MagicMock(side_effect=_mock_convert_image)
        monkeypatch.setattr("vecpic.pipeline.convert_image", mock_conv)

        convert(temp_png, preset="bw", filter_speckle=8)

        mock_conv.assert_called_once()
        config = mock_conv.call_args[0][2]
        assert config.filter_speckle == 8

    def test_all_vtracer_params(self, temp_png, monkeypatch):
        mock_conv = MagicMock(side_effect=_mock_convert_image)
        monkeypatch.setattr("vecpic.pipeline.convert_image", mock_conv)

        convert(
            temp_png,
            colormode="bw",
            hierarchical="cutout",
            mode="polygon",
            filter_speckle=2,
            color_precision=8,
            layer_difference=32,
            corner_threshold=30,
            length_threshold=6.0,
            max_iterations=5,
            splice_threshold=20,
            path_precision=4,
        )
        mock_conv.assert_called_once()
        config = mock_conv.call_args[0][2]
        assert config.colormode == "bw"
        assert config.hierarchical == "cutout"
        assert config.mode == "polygon"
        assert config.filter_speckle == 2
        assert config.color_precision == 8
        assert config.layer_difference == 32
        assert config.corner_threshold == 30
        assert config.length_threshold == 6.0
        assert config.max_iterations == 5
        assert config.splice_threshold == 20
        assert config.path_precision == 4

    def test_max_size_passed_to_reader(self, temp_png, monkeypatch):
        mock_reader = MagicMock()
        mock_reader.return_value = MagicMock()
        mock_reader.return_value.mode = "RGB"
        monkeypatch.setattr("vecpic.pipeline.read_image", mock_reader)

        convert(temp_png, max_size=500)
        mock_reader.assert_called_once()
        kwargs = mock_reader.call_args[1]
        assert kwargs["max_size"] == 500

    def test_flatten_bg_passed_to_reader(self, temp_png, monkeypatch):
        mock_reader = MagicMock()
        mock_reader.return_value = MagicMock()
        mock_reader.return_value.mode = "RGB"
        monkeypatch.setattr("vecpic.pipeline.read_image", mock_reader)

        convert(temp_png, flatten_bg="#ffffff")
        mock_reader.assert_called_once()
        kwargs = mock_reader.call_args[1]
        assert kwargs["flatten_bg"] == "#ffffff"
