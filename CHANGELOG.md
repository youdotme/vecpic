# Changelog

All notable changes to vecpic will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — Unreleased

### Added

- Initial release.
- Convert PNG, JPEG, BMP, GIF, TIFF, WebP to SVG via vtracer.
- CLI with `vecpic -i input.png` and `python -m vecpic`.
- Python API: `vecpic.convert(...)`.
- Three presets: `bw`, `poster`, `photo`.
- EXIF orientation correction.
- Alpha channel preservation and optional `--flatten-bg`.
- `--max-size` for downscaling large images.
- CMYK / P / L / LA colour mode conversion.
- Multi-frame GIF/TIFF/WebP first-frame extraction.
- SVG structural validation.
- Safe atomic SVG output via `os.replace()`.
- PDF/EPS export via `cairosvg`, `inkscape`, or `rsvg-convert` (optional).
- Custom exception hierarchy (`VecpicError` and subclasses).
- 90+ unit, integration, and CLI tests.
