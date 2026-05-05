"""Custom exceptions for vecpic."""


class VecpicError(Exception):
    """Base class for all vecpic exceptions."""


class ConfigError(VecpicError):
    """Configuration error (unknown parameter, illegal value, unknown preset)."""


class FileAccessError(VecpicError):
    """Base class for file access errors."""


class InputFileNotFoundError(FileAccessError):
    """Input file does not exist."""


class OutputPermissionError(FileAccessError):
    """Output path has no write permission."""


class UnsupportedFormatError(VecpicError):
    """Unsupported input format."""


class EmptyFileError(VecpicError):
    """Input file is empty (0 bytes)."""


class InvalidImageError(VecpicError):
    """Image is corrupt, undecodable, or unrecognized by Pillow."""


class ImageTooLargeError(VecpicError):
    """Image exceeds the maximum pixel limit."""


class VtracerNotInstalledError(VecpicError):
    """vtracer is not installed or cannot be imported."""


class ConversionFailedError(VecpicError):
    """vtracer conversion failed."""


class SvgValidationError(VecpicError):
    """Generated SVG failed structural validation."""


class ExportBackendMissingError(VecpicError):
    """No PDF/EPS export backend is available."""


class ExportFailedError(VecpicError):
    """PDF/EPS export failed."""
