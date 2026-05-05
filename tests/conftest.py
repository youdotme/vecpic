"""Shared pytest fixtures."""

import pytest
from PIL import Image


@pytest.fixture
def rgb_image():
    """A small solid RGB image."""
    return Image.new("RGB", (100, 100), (128, 64, 200))


@pytest.fixture
def rgba_image():
    """A small RGBA image with transparency."""
    return Image.new("RGBA", (100, 100), (255, 0, 0, 128))


@pytest.fixture
def cmyk_image():
    """A small CMYK image."""
    rgb = Image.new("RGB", (100, 100), (10, 200, 50))
    return rgb.convert("CMYK")


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory that persists for the test."""
    return tmp_path


@pytest.fixture
def temp_png(tmp_path):
    """Create a temporary PNG file and return its path."""
    path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), (100, 200, 50))
    img.save(path)
    return str(path)


@pytest.fixture
def temp_transparent_png(tmp_path):
    """Create a temporary transparent PNG file."""
    path = tmp_path / "transparent.png"
    img = Image.new("RGBA", (100, 100), (100, 200, 50, 128))
    img.save(path)
    return str(path)


@pytest.fixture
def temp_jpeg(tmp_path):
    """Create a temporary JPEG file."""
    path = tmp_path / "test.jpg"
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    img.save(path, format="JPEG")
    return str(path)


@pytest.fixture
def temp_gif(tmp_path):
    """Create a temporary multi-frame GIF file."""
    path = tmp_path / "test.gif"
    img1 = Image.new("RGB", (100, 100), (255, 0, 0))
    img2 = Image.new("RGB", (100, 100), (0, 255, 0))
    img1.save(path, save_all=True, append_images=[img2], duration=100, loop=0)
    return str(path)


@pytest.fixture
def temp_empty_file(tmp_path):
    """Create an empty file."""
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    return str(path)


@pytest.fixture
def valid_svg(tmp_path):
    """Create a valid SVG file."""
    path = tmp_path / "valid.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100" width="100" height="100">\n'
        '<path d="M10 10 L90 90"/>\n'
        "</svg>\n"
    )
    return str(path)


@pytest.fixture
def valid_svg_no_namespace(tmp_path):
    """Create a valid SVG without namespace."""
    path = tmp_path / "valid_no_ns.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg viewBox="0 0 100 100" width="100" height="100">\n'
        '<path d="M10 10 L90 90"/>\n'
        "</svg>\n"
    )
    return str(path)


@pytest.fixture
def valid_svg_nested(tmp_path):
    """Create a valid SVG with nested graphic element."""
    path = tmp_path / "valid_nested.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100">\n'
        "<g><g><path d=\"M10 10 L90 90\"/></g></g>\n"
        "</svg>\n"
    )
    return str(path)


@pytest.fixture
def invalid_svg_non_xml(tmp_path):
    """Create a file that is not valid XML."""
    path = tmp_path / "invalid_xml.svg"
    path.write_text("this is not xml <<<<")
    return str(path)


@pytest.fixture
def invalid_svg_no_graphics(tmp_path):
    """Create an SVG with no graphic elements."""
    path = tmp_path / "no_graphics.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100">\n'
        "<desc>Just a description</desc>\n"
        "</svg>\n"
    )
    return str(path)


@pytest.fixture
def invalid_svg_missing_dimensions(tmp_path):
    """Create an SVG with no viewBox or width/height."""
    path = tmp_path / "no_dims.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg">\n'
        '<path d="M10 10 L90 90"/>\n'
        "</svg>\n"
    )
    return str(path)


@pytest.fixture
def invalid_svg_wrong_root(tmp_path):
    """Create a file that is XML but not SVG."""
    path = tmp_path / "wrong_root.svg"
    path.write_text(
        '<?xml version="1.0"?>\n'
        "<html><body>not svg</body></html>\n"
    )
    return str(path)
