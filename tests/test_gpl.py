"""Tests for the GIMP .gpl palette loader (SCAL-06)."""

from __future__ import annotations

import pytest

from legome.gpl import load_gpl

GPL_BASIC = """GIMP Palette
Name: Mini Lego
Columns: 4
#
 27  42  52 Black
242 243 242 White
196  40  28 Bright Red
"""


def test_load_gpl_basic(tmp_path):
    p = tmp_path / "mini.gpl"
    p.write_text(GPL_BASIC)
    pal = load_gpl(p)
    assert pal.name == "Mini Lego"
    assert pal.colors == ((27, 42, 52), (242, 243, 242), (196, 40, 28))
    assert "Black" in pal.description
    assert pal.source.endswith("mini.gpl")


def test_load_gpl_unnamed_uses_filename_stem(tmp_path):
    p = tmp_path / "test.gpl"
    p.write_text("GIMP Palette\n0 0 0 Black\n255 255 255 White\n")
    pal = load_gpl(p)
    assert pal.name == "test"


def test_load_gpl_missing_header(tmp_path):
    p = tmp_path / "bad.gpl"
    p.write_text("# not a GIMP palette\n0 0 0 Black\n")
    with pytest.raises(ValueError, match="not a GIMP palette"):
        load_gpl(p)


def test_load_gpl_empty_file(tmp_path):
    p = tmp_path / "empty.gpl"
    p.write_text("")
    with pytest.raises(ValueError, match="not a GIMP palette"):
        load_gpl(p)


def test_load_gpl_no_colors(tmp_path):
    p = tmp_path / "no-colors.gpl"
    p.write_text("GIMP Palette\nName: empty\n#\n")
    with pytest.raises(ValueError, match="no color rows found"):
        load_gpl(p)


def test_load_gpl_short_row(tmp_path):
    p = tmp_path / "short.gpl"
    p.write_text("GIMP Palette\n0 0\n")
    with pytest.raises(ValueError, match="malformed color row"):
        load_gpl(p)


def test_load_gpl_non_integer_channel(tmp_path):
    p = tmp_path / "bad.gpl"
    p.write_text("GIMP Palette\nfoo bar baz Black\n")
    with pytest.raises(ValueError, match="non-integer channel"):
        load_gpl(p)


def test_load_gpl_out_of_range(tmp_path):
    p = tmp_path / "bad.gpl"
    p.write_text("GIMP Palette\n300 0 0 OutOfRange\n")
    with pytest.raises(ValueError, match="out of range"):
        load_gpl(p)


def test_load_gpl_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_gpl(tmp_path / "nope.gpl")


def test_cli_loads_gpl_via_palette_flag(tmp_path):
    """The CLI should route .gpl files to the GIMP loader automatically."""
    import cv2
    import numpy as np

    from legome.cli import main

    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 60, dtype=np.uint8))

    pal_file = tmp_path / "tiny.gpl"
    pal_file.write_text(GPL_BASIC)
    dst = tmp_path / "out.png"

    rc = main([str(src), str(dst), "--palette", str(pal_file), "--no-display"])
    assert rc == 0
    out = cv2.imread(str(dst))
    assert out is not None
    seen = {tuple(int(c) for c in px) for px in out.reshape(-1, 3)}
    # Output BGR; palette colors stored RGB.
    expected_bgr = {(b, g, r) for r, g, b in [(27, 42, 52), (242, 243, 242), (196, 40, 28)]}
    assert seen.issubset(expected_bgr)
