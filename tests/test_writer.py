"""Tests for writer.py."""

import os

import pytest

from vecpic.errors import OutputPermissionError, SvgValidationError
from vecpic.writer import finalize_svg, validate_svg


class TestValidateSvg:
    def test_valid_svg(self, valid_svg):
        validate_svg(valid_svg)

    def test_valid_svg_no_namespace(self, valid_svg_no_namespace):
        validate_svg(valid_svg_no_namespace)

    def test_valid_svg_nested_graphics(self, valid_svg_nested):
        validate_svg(valid_svg_nested)

    def test_invalid_non_xml(self, invalid_svg_non_xml):
        with pytest.raises(SvgValidationError):
            validate_svg(invalid_svg_non_xml)

    def test_invalid_no_graphics(self, invalid_svg_no_graphics):
        with pytest.raises(SvgValidationError, match="no graphic"):
            validate_svg(invalid_svg_no_graphics)

    def test_invalid_missing_dimensions(self, invalid_svg_missing_dimensions):
        with pytest.raises(SvgValidationError, match="viewBox"):
            validate_svg(invalid_svg_missing_dimensions)

    def test_invalid_wrong_root(self, invalid_svg_wrong_root):
        with pytest.raises(SvgValidationError, match="root"):
            validate_svg(invalid_svg_wrong_root)

    def test_nonexistent_file(self):
        with pytest.raises(SvgValidationError):
            validate_svg("/nonexistent/file.svg")


class TestFinalizeSvg:
    def test_finalize_moves_file(self, valid_svg, tmp_path):
        dest = tmp_path / "dest.svg"
        finalize_svg(valid_svg, dest)
        assert dest.exists()
        assert not os.path.exists(valid_svg)

    def test_finalize_with_validation(self, valid_svg, tmp_path):
        dest = tmp_path / "dest.svg"
        finalize_svg(valid_svg, dest, validate=True)
        assert dest.exists()

    def test_finalize_without_validation(self, valid_svg, tmp_path):
        dest = tmp_path / "dest.svg"
        finalize_svg(valid_svg, dest, validate=False)
        assert dest.exists()

    def test_finalize_invalid_svg_no_validate(self, invalid_svg_non_xml, tmp_path):
        dest = tmp_path / "dest.svg"
        finalize_svg(invalid_svg_non_xml, dest, validate=False)
        assert dest.exists()

    def test_finalize_invalid_svg_with_validate_raises(self, invalid_svg_non_xml, tmp_path):
        dest = tmp_path / "dest.svg"
        with pytest.raises(SvgValidationError):
            finalize_svg(invalid_svg_non_xml, dest, validate=True)

    def test_finalize_overwrites_existing(self, valid_svg, tmp_path):
        dest = tmp_path / "dest.svg"
        dest.write_text("old content")
        finalize_svg(valid_svg, dest, validate=False)
        assert dest.read_text() != "old content"

    def test_finalize_creates_parent_dir(self, valid_svg, tmp_path):
        dest = tmp_path / "subdir" / "dest.svg"
        finalize_svg(valid_svg, dest, validate=False)
        assert dest.exists()
