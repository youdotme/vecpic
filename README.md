# vecpic

Convert raster images (PNG, JPEG, BMP, GIF, TIFF, WebP) to SVG vector graphics using [vtracer](https://github.com/visioncortex/vtracer).

## Installation

```bash
pip install vecpic
```

For PDF/EPS export support:

```bash
pip install "vecpic[export]"
```

## Quick Start

### CLI

```bash
# Convert PNG to SVG
vecpic -i input.png

# Specify output path
vecpic -i photo.jpg -o drawing.svg

# Use a preset
vecpic -i logo.png --preset bw
```

### Python API

```python
from vecpic import convert

# Basic conversion
convert("input.png")

# With options
convert(
    "photo.jpg",
    output_path="output.svg",
    preset="photo",
    filter_speckle=8,
    max_size=2048,
)
```

## Supported Formats

| Input | Output |
|-------|--------|
| PNG, JPEG, BMP | SVG |
| GIF (first frame) | PDF (with export extras) |
| TIFF (first frame) | EPS (with export extras) |
| WebP (first frame) | |

## CLI Options

```
usage: vecpic -i INPUT [-o OUTPUT] [--format {svg,pdf,eps}]
              [--preset {bw,poster,photo}]
              [--colormode {color,bw}] [--mode {spline,polygon,pixel}]
              [--filter-speckle N] [--color-precision N]
              [--layer-difference N] [--corner-threshold N]
              [--length-threshold F] [--max-iterations N]
              [--splice-threshold N] [--path-precision N]
              [--max-size N] [--flatten-bg COLOR] [--keep-svg]
              [-v | -vv | -q]
```

### Presets

| Preset | Best for |
|--------|----------|
| `bw` | Text, signatures, line art, black-and-white icons |
| `poster` | Illustrations, flat design, poster-style images |
| `photo` | Photographs, images with complex colours |

### Key Options

| Option | Description |
|--------|-------------|
| `--max-size N` | Scale longest edge to at most N pixels |
| `--flatten-bg COLOR` | Composite transparency onto a background colour |
| `--keep-svg` | Keep intermediate SVG when exporting to PDF/EPS |
| `--mode` | Curve fitting: `spline`, `polygon`, or `pixel` |
| `--colormode` | `color` or `bw` |

## PDF/EPS Export

Export support requires one of:

1. `pip install "vecpic[export]"` (cairosvg)
2. [Inkscape](https://inkscape.org) installed and in PATH
3. [librsvg](https://wiki.gnome.org/Projects/LibRsvg) (rsvg-convert) installed and in PATH

```bash
vecpic -i input.png -o output.pdf
vecpic -i input.png --format eps
```

## Development

```bash
# Clone and install
git clone https://github.com/your/vecpic.git
cd vecpic
pip install -e ".[dev]"

# Run tests
pytest

# Run slow integration tests
pytest -m slow

# Lint
ruff check vecpic/
mypy vecpic/
```

## Requirements

- Python >= 3.10
- Pillow >= 10.0
- vtracer >= 0.6.11

## License

MIT
