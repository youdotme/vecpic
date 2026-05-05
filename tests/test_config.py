"""Tests for VtracerConfig."""

import pytest

from vecpic.config import PRESETS, QUALITY_LEVELS, VtracerConfig
from vecpic.errors import ConfigError


def test_default_config():
    config = VtracerConfig()
    assert config.colormode == "color"
    assert config.hierarchical == "stacked"
    assert config.mode == "spline"
    assert config.filter_speckle == 4
    assert config.color_precision == 6
    assert config.layer_difference == 16
    assert config.corner_threshold == 60
    assert config.length_threshold == 4.0
    assert config.max_iterations == 10
    assert config.splice_threshold == 45
    assert config.path_precision == 3


def test_invalid_colormode():
    with pytest.raises(ConfigError, match="colormode"):
        VtracerConfig(colormode="invalid")


def test_invalid_hierarchical():
    with pytest.raises(ConfigError, match="hierarchical"):
        VtracerConfig(hierarchical="invalid")


def test_invalid_mode():
    with pytest.raises(ConfigError, match="mode"):
        VtracerConfig(mode="invalid")


def test_negative_filter_speckle():
    with pytest.raises(ConfigError, match="filter_speckle"):
        VtracerConfig(filter_speckle=-1)


def test_negative_color_precision():
    with pytest.raises(ConfigError, match="color_precision"):
        VtracerConfig(color_precision=-1)


def test_negative_length_threshold():
    with pytest.raises(ConfigError, match="length_threshold"):
        VtracerConfig(length_threshold=-1.0)


def test_custom_config():
    config = VtracerConfig(
        colormode="bw",
        mode="polygon",
        filter_speckle=0,
    )
    assert config.colormode == "bw"
    assert config.mode == "polygon"
    assert config.filter_speckle == 0


def test_merged_override():
    base = VtracerConfig()
    merged = base.merged(filter_speckle=2)
    assert merged.filter_speckle == 2
    assert merged.colormode == "color"


def test_merged_none_is_ignored():
    base = VtracerConfig()
    merged = base.merged(filter_speckle=None, colormode=None)
    assert merged.filter_speckle == 4
    assert merged.colormode == "color"


def test_merged_unknown_key():
    base = VtracerConfig()
    with pytest.raises(ConfigError, match="unknown config key"):
        base.merged(unknown_key=123)


def test_to_dict():
    config = VtracerConfig()
    d = config.to_dict()
    assert isinstance(d, dict)
    assert d["colormode"] == "color"
    assert d["filter_speckle"] == 4


def test_preset_bw():
    config = PRESETS["bw"]
    assert config.colormode == "bw"
    assert config.mode == "polygon"
    assert config.hierarchical == "cutout"


def test_preset_poster():
    config = PRESETS["poster"]
    assert config.colormode == "color"
    assert config.mode == "polygon"


def test_preset_photo():
    config = PRESETS["photo"]
    assert config.colormode == "color"
    assert config.mode == "spline"


def test_frozen_config():
    config = VtracerConfig()
    with pytest.raises(Exception):
        config.filter_speckle = 10  # type: ignore[misc]


class TestQualityLevels:
    def _vtracer_fields(self, q: dict) -> dict:
        return {k: v for k, v in q.items() if k != "max_size"}

    def test_quality_low(self):
        q = QUALITY_LEVELS["low"]
        assert q["max_size"] == 1024
        assert q["corner_threshold"] == 45
        assert q["splice_threshold"] == 40
        assert q["path_precision"] == 3
        assert q["max_iterations"] == 8

    def test_quality_medium(self):
        q = QUALITY_LEVELS["medium"]
        assert q["max_size"] == 2048
        assert q["corner_threshold"] == 20
        assert q["splice_threshold"] == 22
        assert q["path_precision"] == 4
        assert q["max_iterations"] == 13

    def test_quality_high(self):
        q = QUALITY_LEVELS["high"]
        assert q["max_size"] == 3072
        assert q["corner_threshold"] == 10
        assert q["splice_threshold"] == 14
        assert q["path_precision"] == 5
        assert q["max_iterations"] == 17

    def test_quality_extreme(self):
        q = QUALITY_LEVELS["extreme"]
        assert q["max_size"] == 4096
        assert q["corner_threshold"] == 6
        assert q["splice_threshold"] == 10
        assert q["path_precision"] == 6
        assert q["max_iterations"] == 22

    def test_quality_extreme_not_absurd(self):
        q = QUALITY_LEVELS["extreme"]
        assert q["path_precision"] <= 6
        assert q["max_iterations"] <= 22
        assert q["splice_threshold"] >= 8

    def test_quality_applied_to_config(self):
        base = VtracerConfig(corner_threshold=99, splice_threshold=99)
        merged = base.merged(**self._vtracer_fields(QUALITY_LEVELS["medium"]))
        assert merged.corner_threshold == 20
        assert merged.splice_threshold == 22
        assert merged.path_precision == 4

    def test_quality_override_by_explicit(self):
        base = VtracerConfig()
        merged = (
            base.merged(**self._vtracer_fields(QUALITY_LEVELS["medium"]))
            .merged(corner_threshold=99)
        )
        assert merged.corner_threshold == 99
        assert merged.path_precision == 4

    def test_quality_unknown_key_raises(self):
        base = VtracerConfig()
        with pytest.raises(ConfigError, match="unknown config key"):
            base.merged(**{"not_a_key": 1})


def test_no_text_preset():
    assert "text" not in PRESETS


def test_presets_count():
    assert len(PRESETS) == 3
