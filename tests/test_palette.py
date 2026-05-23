"""Unit tests for legome.palette."""

import json

import pytest

from legome.palette import LUT_SIZE, Palette, default_palette_path, load_palette


def _valid_lut():
    return [[i, i, i] for i in range(LUT_SIZE)]


def test_default_palette_loads():
    pal = load_palette(default_palette_path())
    assert pal.name == "lego"
    assert len(pal.colors) == 112
    assert all(len(c) == 3 for c in pal.colors)


def test_palette_unique_colors_default():
    pal = load_palette(default_palette_path())
    unique = pal.unique_colors()
    assert 1 < len(unique) <= LUT_SIZE
    assert (0, 0, 0) in unique
    assert (255, 255, 255) in unique


def test_palette_rejects_empty_colors():
    with pytest.raises(ValueError, match="at least one color"):
        Palette(name="bad", colors=tuple())


def test_palette_accepts_short_color_list():
    """REL-05/LEGO-05: palettes are no longer fixed at 256 entries."""
    pal = Palette(name="tiny", colors=tuple([(1, 2, 3), (255, 0, 0)]))
    assert len(pal.colors) == 2


def test_palette_rejects_non_rgb_entry():
    bad = [(0, 0, 0), (1, 2)]  # type: ignore[list-item]
    with pytest.raises(ValueError, match="RGB triple"):
        Palette(name="bad", colors=tuple(bad))


def test_load_palette_short_entry_reports_index(tmp_path):
    lut = [[0, 0, 0]] * (LUT_SIZE - 1) + [[1, 2]]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"name": "t", "lut": lut}))
    with pytest.raises(ValueError, match=r"entry 255"):
        load_palette(p)


def test_palette_rejects_out_of_range_channel():
    bad = [(0, 0, 0), (0, 0, 300)]
    with pytest.raises(ValueError, match="channel out of range"):
        Palette(name="bad", colors=tuple(bad))


def test_load_palette_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_palette(tmp_path / "nope.json")


def test_load_palette_root_not_object(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError, match="root must be object"):
        load_palette(p)


def test_load_palette_missing_name(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"lut": _valid_lut()}))
    with pytest.raises(ValueError, match="missing 'name'"):
        load_palette(p)


def test_load_palette_missing_colors_and_lut(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"name": "x"}))
    with pytest.raises(ValueError, match="missing 'colors' or 'lut'"):
        load_palette(p)


def test_load_palette_accepts_colors_key(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"name": "t", "colors": [[1, 2, 3], [4, 5, 6]]}))
    pal = load_palette(p)
    assert pal.colors == ((1, 2, 3), (4, 5, 6))


def test_lego_palette_factory():
    """The default `lego_palette()` returns a Palette built from LEGO_COLORS."""
    from legome.lego_colors import LEGO_COLORS
    from legome.palette import lego_palette

    pal = lego_palette()
    assert pal.name == "lego-bricks"
    assert len(pal.colors) == len(LEGO_COLORS)
    assert len(pal.unique_colors()) == len(LEGO_COLORS)


def test_palette_lut_property_requires_256():
    pal = Palette(name="tiny", colors=tuple([(0, 0, 0), (1, 1, 1)]))
    with pytest.raises(ValueError, match="requires exactly 256"):
        _ = pal.lut


def test_default_palette_uses_colors_schema():
    """FMT-03: bundled palette is compact (`colors` list, not 256-LUT)."""
    import json

    from legome.palette import default_palette_path

    raw = json.loads(default_palette_path().read_text())
    assert "colors" in raw
    assert "lut" not in raw
    assert len(raw["colors"]) == 112


def test_default_palette_compact_matches_legacy_lut(tmp_path):
    """FMT-03 parity: compact `colors` form yields identical quantizer output
    to the legacy 256-entry `lut` form for the same image."""
    import json

    import numpy as np

    from legome.palette import default_palette_path
    from legome.processor import apply_palette

    raw = json.loads(default_palette_path().read_text())
    colors = raw["colors"]
    # Rebuild a 256-entry LUT by repeating each unique color round-robin.
    lut = [colors[i % len(colors)] for i in range(256)]
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"name": "legacy", "lut": lut}))

    pal_new = load_palette(default_palette_path())
    pal_legacy = load_palette(legacy)
    rng = np.random.default_rng(2026)
    img = rng.integers(0, 256, size=(12, 12, 3), dtype=np.uint8)
    assert np.array_equal(apply_palette(img, pal_new), apply_palette(img, pal_legacy)), (
        "compact `colors` and legacy `lut` palettes must produce identical "
        "quantizer output when they expose the same color set"
    )


def test_load_palette_coerces_int(tmp_path):
    lut = [[float(i), float(i), float(i)] for i in range(LUT_SIZE)]
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"name": "t", "lut": lut, "description": "d", "source": "s"}))
    pal = load_palette(p)
    assert pal.name == "t"
    assert pal.description == "d"
    assert pal.source == "s"
    assert all(isinstance(ch, int) for c in pal.lut for ch in c)


def test_default_palette_path_exists():
    assert default_palette_path().is_file()
