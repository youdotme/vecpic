"""Tests for reader.py."""

import pytest
from PIL import Image

from vecpic.errors import (
    EmptyFileError,
    ImageTooLargeError,
    InputFileNotFoundError,
    InvalidImageError,
    UnsupportedFormatError,
)
from vecpic.reader import (
    MAX_PIXELS_HARD_LIMIT,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_FORMATS,
    detect_format,
    read_image,
)


class TestDetectFormat:
    def test_png(self, temp_png):
        assert detect_format(temp_png) == "PNG"

    def test_jpeg(self, temp_jpeg):
        assert detect_format(temp_jpeg) == "JPEG"

    def test_nonexistent_file(self):
        with pytest.raises(InputFileNotFoundError):
            detect_format("/nonexistent/file.png")

    def test_empty_file(self, temp_empty_file):
        with pytest.raises(EmptyFileError):
            detect_format(temp_empty_file)

    def test_corrupt_file(self, tmp_path):
        path = tmp_path / "corrupt.png"
        path.write_bytes(b"not an image")
        with pytest.raises(InvalidImageError):
            detect_format(path)

    def test_gif(self, temp_gif):
        assert detect_format(temp_gif) == "GIF"


class TestReadImage:
    def test_read_rgb(self, temp_png):
        img = read_image(temp_png)
        assert img.mode == "RGB"
        img.close()

    def test_read_rgba(self, temp_transparent_png):
        img = read_image(temp_transparent_png)
        assert img.mode == "RGBA"
        img.close()

    def test_unsupported_format(self, tmp_path):
        path = tmp_path / "test.tga"
        img = Image.new("RGB", (10, 10))
        img.save(path, format="TGA")
        with pytest.raises(UnsupportedFormatError):
            read_image(path)

    def test_flatten_bg(self, temp_transparent_png):
        img = read_image(temp_transparent_png, flatten_bg="#ffffff")
        assert img.mode == "RGBA"
        pixels = img.getpixel((0, 0))
        assert pixels[3] == 255
        img.close()

    def test_max_size_scale(self, temp_png):
        img = read_image(temp_png, max_size=50)
        w, h = img.size
        assert max(w, h) <= 50
        img.close()

    def test_max_size_no_scale(self, temp_png):
        img = read_image(temp_png, max_size=500)
        assert img.size == (100, 100)
        img.close()

    def test_cmyk_conversion(self, cmyk_image, tmp_path):
        path = tmp_path / "cmyk.jpg"
        cmyk_image.save(path, format="JPEG")
        img = read_image(path)
        assert img.mode == "RGB"
        img.close()

    def test_nonexistent(self):
        with pytest.raises(InputFileNotFoundError):
            read_image("/nonexistent.png")

    def test_not_a_file(self, tmp_path):
        with pytest.raises(InputFileNotFoundError):
            read_image(str(tmp_path))

    def test_empty(self, temp_empty_file):
        with pytest.raises(EmptyFileError):
            read_image(temp_empty_file)

    def test_unsupported_extension_warning(self, tmp_path, caplog):
        path = tmp_path / "test.xyz"
        Image.new("RGB", (10, 10), (100, 100, 100)).save(path, format="PNG")
        import logging

        caplog.set_level(logging.WARNING)
        img = read_image(path)
        img.close()
        assert any("unusual file extension" in r.message.lower() for r in caplog.records)

    def test_multi_frame_gif(self, temp_gif):
        img = read_image(temp_gif)
        assert img.size == (100, 100)
        img.close()

    def test_huge_image_warning(self, tmp_path, caplog):
        large = Image.new("RGB", (12000, 100), (0, 0, 0))
        path = tmp_path / "large.png"
        large.save(path)
        import logging

        caplog.set_level(logging.WARNING)
        img = read_image(path)
        img.close()
        assert any("very large" in r.message.lower() for r in caplog.records)


class TestReadImageModeConversion:
    def test_l_mode(self, tmp_path):
        path = tmp_path / "l.png"
        Image.new("L", (10, 10), 128).save(path)
        img = read_image(path)
        assert img.mode == "RGB"
        img.close()

    def test_la_mode(self, tmp_path):
        path = tmp_path / "la.png"
        Image.new("LA", (10, 10), (128, 200)).save(path)
        img = read_image(path)
        assert img.mode == "RGBA"
        img.close()

    def test_p_mode_rgba(self, tmp_path):
        path = tmp_path / "p_transparent.png"
        img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
        converted = img.convert("P")
        converted.save(path, format="PNG")
        result = read_image(path)
        result.close()

    def test_p_mode_rgb(self, tmp_path):
        path = tmp_path / "p_rgb.png"
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        converted = img.convert("P")
        converted.info.pop("transparency", None)
        converted.save(path, format="PNG")
        result = read_image(path)
        result.close()


class TestIccProfile:
    def test_no_profile_passes_through(self, temp_png):
        img = read_image(temp_png)
        assert img.mode == "RGB"
        img.close()

    def test_icc_profile_converted(self, temp_png, monkeypatch):
        mock_called = []

        class FakeProfile:
            pass

        def fake_profile_to_profile(img, input_profile, output_profile, outputMode):
            mock_called.append(True)
            result = img.copy()
            result.info = dict(img.info)
            return result

        def fake_create_profile(name):
            return FakeProfile()

        monkeypatch.setattr("PIL.ImageCms.profileToProfile", fake_profile_to_profile)
        monkeypatch.setattr("PIL.ImageCms.createProfile", fake_create_profile)

        from PIL import Image
        img = Image.open(temp_png)
        img.info["icc_profile"] = b"fake_icc_data"
        path = temp_png + "_icc.png"
        img.save(path)

        result = read_image(path)
        assert "icc_profile" not in result.info
        assert len(mock_called) == 1
        result.close()
