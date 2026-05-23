"""Tests for the Lego color reference DB and palette validator."""

from legome.lego_colors import (
    LEGO_COLORS,
    closest_lego_color,
    coverage,
    match_palette_to_lego,
)
from legome.palette import default_palette_path, load_palette


def test_lego_color_db_non_empty():
    assert len(LEGO_COLORS) >= 30
    for c in LEGO_COLORS:
        assert all(0 <= ch <= 255 for ch in c.rgb)
        assert c.name


def test_lego_color_db_has_unique_rgbs():
    """REL-10: no two entries may share an RGB; duplicates collapse into aliases."""
    rgbs = [c.rgb for c in LEGO_COLORS]
    assert len(rgbs) == len(set(rgbs)), "duplicate RGB in LEGO_COLORS"


def test_lego_color_aliases_preserved():
    """Aliases keep the alternate catalog names for the same physical brick."""
    by_name = {c.name: c for c in LEGO_COLORS}
    assert "Tan" in by_name["Brick Yellow"].aliases
    assert "Dark Blue" in by_name["Earth Blue"].aliases


def test_lego_color_bricklink_ids_known_subset():
    """DOC-03: well-known core colors have a Bricklink ID filled in."""
    from legome.lego_colors import bricklink_url

    by_name = {c.name: c for c in LEGO_COLORS}
    assert by_name["Black"].bricklink_id == 11
    assert by_name["White"].bricklink_id == 1
    assert by_name["Bright Red"].bricklink_id == 5
    assert by_name["Bright Blue"].bricklink_id == 7
    assert by_name["Bright Yellow"].bricklink_id == 3
    assert by_name["Bright Green"].bricklink_id == 6
    # Some niche entries are intentionally left None until verified.
    assert by_name["Earth Green"].bricklink_id is None
    # URL helper round-trip.
    url = bricklink_url(by_name["Black"])
    assert url is not None and "colorID=11" in url
    assert bricklink_url(by_name["Earth Green"]) is None


def test_lego_color_bricklink_ids_are_unique():
    """Each filled Bricklink ID maps to a single LegoColor row."""
    ids = [c.bricklink_id for c in LEGO_COLORS if c.bricklink_id is not None]
    assert len(ids) == len(set(ids)), "duplicate bricklink_id"


def test_closest_lego_color_exact_match():
    target = LEGO_COLORS[0]
    found, dist = closest_lego_color(target.rgb)
    assert found.name == target.name
    assert dist == 0.0


def test_closest_lego_color_near_white():
    found, dist = closest_lego_color((250, 250, 250))
    assert found.name == "White"
    assert dist < 15


def test_match_palette_to_lego_threshold():
    rows = match_palette_to_lego([(27, 42, 52), (1, 2, 3)], threshold=10.0)
    assert rows[0]["match"] is True  # exact Black match
    assert rows[1]["match"] is False  # near (0,0,0) but closest Lego is Black @ ~55


def test_coverage_default_palette():
    pal = load_palette(default_palette_path())
    # At least 50% of the palette colors should match real Lego bricks within
    # a generous threshold. The bundled LUT was hand-tuned for Lego mosaic use.
    cov = coverage(pal.unique_colors(), threshold=40.0)
    assert cov >= 0.5, f"only {cov:.2%} of palette matches real Lego colors"


def test_coverage_empty_input():
    assert coverage([]) == 0.0


def test_match_palette_to_lego_returns_expected_fields():
    rows = match_palette_to_lego([(27, 42, 52)])
    r = rows[0]
    assert set(r.keys()) == {"palette_rgb", "lego_name", "lego_rgb", "distance", "match"}
    assert r["palette_rgb"] == (27, 42, 52)
    assert r["lego_name"] == "Black"
