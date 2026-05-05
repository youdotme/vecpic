"""Configuration dataclass and presets for vtracer parameters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .errors import ConfigError

_NON_NEGATIVE_INT_FIELDS = (
    "filter_speckle",
    "color_precision",
    "layer_difference",
    "corner_threshold",
    "max_iterations",
    "splice_threshold",
    "path_precision",
)


@dataclass(frozen=True)
class VtracerConfig:
    colormode: str = "color"
    hierarchical: str = "stacked"
    mode: str = "spline"

    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16

    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 3

    def __post_init__(self) -> None:
        if self.colormode not in {"color", "bw"}:
            raise ConfigError(f"illegal colormode: {self.colormode!r}")

        if self.hierarchical not in {"stacked", "cutout"}:
            raise ConfigError(f"illegal hierarchical: {self.hierarchical!r}")

        if self.mode not in {"spline", "polygon", "pixel"}:
            raise ConfigError(f"illegal mode: {self.mode!r}")

        for name in _NON_NEGATIVE_INT_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, int):
                raise ConfigError(f"{name} must be an integer")
            if value < 0:
                raise ConfigError(f"{name} must be >= 0")

        if self.length_threshold < 0:
            raise ConfigError("length_threshold must be >= 0")

    def merged(self, **overrides: object) -> "VtracerConfig":
        valid_keys = set(self.__dataclass_fields__)
        unknown = set(overrides) - valid_keys
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ConfigError(f"unknown config keys: {names}")

        values = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **values)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PRESETS: dict[str, VtracerConfig] = {
    "bw": VtracerConfig(
        colormode="bw",
        mode="polygon",
        hierarchical="cutout",
    ),
    "poster": VtracerConfig(
        colormode="color",
        mode="polygon",
    ),
    "photo": VtracerConfig(
        colormode="color",
        mode="spline",
    ),
}


QUALITY_LEVELS: dict[str, dict[str, object]] = {
    "low": {
        "max_size": 1024,
        "filter_speckle": 8,
        "color_precision": 6,
        "layer_difference": 12,
        "corner_threshold": 45,
        "length_threshold": 4.0,
        "max_iterations": 8,
        "splice_threshold": 40,
        "path_precision": 3,
    },
    "medium": {
        "max_size": 2048,
        "filter_speckle": 3,
        "color_precision": 7,
        "layer_difference": 7,
        "corner_threshold": 20,
        "length_threshold": 3.5,
        "max_iterations": 13,
        "splice_threshold": 22,
        "path_precision": 4,
    },
    "high": {
        "max_size": 3072,
        "filter_speckle": 1,
        "color_precision": 8,
        "layer_difference": 4,
        "corner_threshold": 10,
        "length_threshold": 3.5,
        "max_iterations": 17,
        "splice_threshold": 14,
        "path_precision": 5,
    },
    "extreme": {
        "max_size": 4096,
        "filter_speckle": 0,
        "color_precision": 8,
        "layer_difference": 3,
        "corner_threshold": 6,
        "length_threshold": 3.5,
        "max_iterations": 22,
        "splice_threshold": 10,
        "path_precision": 6,
    },
}

DEFAULT_QUALITY = "low"
