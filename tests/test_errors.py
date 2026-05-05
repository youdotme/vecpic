"""Tests for error classes."""

from vecpic.errors import (
    ConfigError,
    ConversionFailedError,
    EmptyFileError,
    ExportBackendMissingError,
    ExportFailedError,
    FileAccessError,
    ImageTooLargeError,
    InputFileNotFoundError,
    InvalidImageError,
    OutputPermissionError,
    SvgValidationError,
    UnsupportedFormatError,
    VecpicError,
    VtracerNotInstalledError,
)


def test_all_errors_inherit_vecpic_error():
    errors = [
        ConfigError,
        FileAccessError,
        InputFileNotFoundError,
        OutputPermissionError,
        UnsupportedFormatError,
        EmptyFileError,
        InvalidImageError,
        ImageTooLargeError,
        VtracerNotInstalledError,
        ConversionFailedError,
        SvgValidationError,
        ExportBackendMissingError,
        ExportFailedError,
    ]
    for cls in errors:
        assert issubclass(cls, VecpicError), f"{cls.__name__} must be a VecpicError"


def test_error_messages():
    exc = ConfigError("test message")
    assert str(exc) == "test message"


def test_file_access_hierarchy():
    assert issubclass(InputFileNotFoundError, FileAccessError)
    assert issubclass(OutputPermissionError, FileAccessError)


def test_catch_all():
    try:
        raise ConversionFailedError("failed")
    except VecpicError as e:
        assert "failed" in str(e)
