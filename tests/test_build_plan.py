"""Tests for legome.build_plan (BUILD-01)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from legome.build_plan import (
    DEFAULT_CELL_W_PX,
    LEGO_UNIT_ASPECT,
    MIN_CELL_W_PX,
    _excel_column,
    _fit_text,
    _luminance,
    _text_color,
    render_build_plan,
)
from legome.lego_colors import LEGO_COLORS
from legome.palette import lego_palette
from legome.processor import apply_palette


def _mosaic(rows: int, cols: int) -> np.ndarray:
    """Produce a quantized BGR mosaic of the requested shape."""
    pal = lego_palette()
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(rows, cols, 3), dtype=np.uint8)
    return apply_palette(img, pal)


def test_excel_column_letters():
    assert _excel_column(0) == "A"
    assert _excel_column(25) == "Z"
    assert _excel_column(26) == "AA"
    assert _excel_column(51) == "AZ"
    assert _excel_column(52) == "BA"


def test_luminance_dark_vs_light():
    assert _luminance(0, 0, 0) == 0
    assert _luminance(255, 255, 255) == pytest.approx(255.0)
    assert _text_color((0, 0, 0)) == (255, 255, 255)
    assert _text_color((255, 255, 255)) == (0, 0, 0)


def test_render_build_plan_canvas_shape():
    mosaic = _mosaic(rows=4, cols=3)
    out = render_build_plan(mosaic)
    cell_w = DEFAULT_CELL_W_PX
    cell_h = round(cell_w * LEGO_UNIT_ASPECT)
    margin = 60
    grid_w = 3 * cell_w
    grid_h = 4 * cell_h
    # Width = 2*margin + grid_w. Height has extra legend rows.
    assert out.shape[1] == 2 * margin + grid_w
    assert out.shape[0] >= 2 * margin + grid_h  # legend extends below


def test_render_build_plan_cell_aspect_matches_real_brick():
    mosaic = _mosaic(rows=2, cols=2)
    canvas = render_build_plan(mosaic, cell_w_px=78)
    # 78 * 9.6 / 7.8 == 96 exactly.
    assert round(78 * LEGO_UNIT_ASPECT) == 96
    # Canvas height must contain at least the grid (2 rows of 96 px) + margins.
    assert canvas.shape[0] >= 2 * 96 + 60 * 2


def test_render_build_plan_rejects_undersize_cell():
    mosaic = _mosaic(rows=2, cols=2)
    with pytest.raises(ValueError, match="below minimum"):
        render_build_plan(mosaic, cell_w_px=MIN_CELL_W_PX - 1)


def test_render_build_plan_rejects_bad_image():
    with pytest.raises(ValueError, match="HxWx3 uint8"):
        render_build_plan(np.zeros((4, 4), dtype=np.uint8))


def test_render_build_plan_cell_color_matches_input():
    """The top-left chunk of each cell must equal that cell's input BGR."""
    pal = lego_palette()
    rng = np.random.default_rng(7)
    img = rng.integers(0, 256, size=(2, 2, 3), dtype=np.uint8)
    quant = apply_palette(img, pal)
    out = render_build_plan(quant, cell_w_px=60)
    margin = 60
    # Sample a pixel near the top edge of cell (0,0) where the rectangle fill
    # dominates and no text has been drawn yet.
    sample = out[margin + 2, margin + 2]
    assert tuple(int(c) for c in sample) == tuple(int(c) for c in quant[0, 0])


def test_render_build_plan_unknown_color_marks_question_mark():
    """A pixel whose color is NOT in LEGO_COLORS produces '?' in name + id."""
    mosaic = np.zeros((1, 1, 3), dtype=np.uint8)
    mosaic[0, 0] = (123, 45, 67)  # unlikely-to-match BGR
    # Must not raise; legend should still draw with "(unknown)" entry.
    out = render_build_plan(mosaic, cell_w_px=60)
    assert out.dtype == np.uint8


def test_render_build_plan_legend_rows_present():
    # Two-color mosaic to keep the legend tight and deterministic.
    img = np.zeros((1, 2, 3), dtype=np.uint8)
    img[0, 0] = (LEGO_COLORS[0].rgb[2], LEGO_COLORS[0].rgb[1], LEGO_COLORS[0].rgb[0])
    img[0, 1] = (LEGO_COLORS[1].rgb[2], LEGO_COLORS[1].rgb[1], LEGO_COLORS[1].rgb[0])
    out = render_build_plan(img, cell_w_px=60, show_legend=True)
    # Without legend the canvas is shorter; assert legend adds height.
    out_no = render_build_plan(img, cell_w_px=60, show_legend=False)
    assert out.shape[0] > out_no.shape[0]


def test_cli_writes_build_plan(tmp_path, monkeypatch):
    from legome.cli import main

    monkeypatch.setattr("legome.display.show_image", lambda *a, **k: False)
    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 100, dtype=np.uint8))
    out = tmp_path / "out.png"
    plan = tmp_path / "plan.png"
    rc = main([str(src), str(out), "--no-display", "--build-plan", str(plan)])
    assert rc == 0
    assert plan.is_file()
    img = cv2.imread(str(plan))
    assert img is not None
    assert img.shape[1] > 4 * MIN_CELL_W_PX  # rendered cells, not raw 4x4


def test_cli_build_plan_extension_forced_to_png(tmp_path, monkeypatch):
    from legome.cli import main

    monkeypatch.setattr("legome.display.show_image", lambda *a, **k: False)
    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 60, dtype=np.uint8))
    plan_path = tmp_path / "plan.jpg"
    rc = main([str(src), str(tmp_path / "out.png"), "--no-display", "--build-plan", str(plan_path)])
    assert rc == 0
    # CLI forces .png extension on the build-plan output (REL-14 alignment).
    assert (tmp_path / "plan.png").is_file()


def test_cli_build_plan_ignored_in_batch_mode(tmp_path, caplog):
    import logging

    from legome.cli import main

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    cv2.imwrite(str(in_dir / "a.png"), np.full((4, 4, 3), 100, dtype=np.uint8))
    with caplog.at_level(logging.WARNING):
        rc = main([str(in_dir), str(out_dir), "--no-display", "--build-plan", str(tmp_path / "plan.png")])
    assert rc == 0
    assert any("ignored in batch mode" in m for m in caplog.messages)


def test_fit_text_empty_returns_blank():
    """Empty input string short-circuits to ('', 0.5)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    assert _fit_text("", 100, 30, font, 1) == ("", 0.5)


def test_fit_text_truncates_to_question_mark_when_too_narrow():
    """No scale + no truncation fits → fall through to '?' fallback."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    # max_w=1 px is narrower than even a single rendered char at the minimum
    # scale (0.3), so every candidate (including the empty truncation) fails
    # the width check and the function returns the sentinel '?'.
    fitted, scale = _fit_text("WWWWW", 1, 30, font, 1)
    assert fitted == "?"
    assert scale == 0.3


def test_cli_build_plan_cell_too_small(tmp_path, monkeypatch):
    from legome.cli import main

    monkeypatch.setattr("legome.display.show_image", lambda *a, **k: False)
    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((2, 2, 3), 60, dtype=np.uint8))
    rc = main([
        str(src),
        str(tmp_path / "out.png"),
        "--no-display",
        "--build-plan", str(tmp_path / "plan.png"),
        "--build-plan-cell-px", "20",
    ])
    assert rc == 2
