"""BUILD-01: render a printable build plan for a quantized mosaic.

Each pixel of the quantized image is rendered as a real-Lego-aspect-ratio
cell with three lines of text inside:

  Line 1   color name (if the pixel maps to a known LegoColor; truncated
           with `...` if it overflows the cell)
  Line 2   Bricklink ID (or `?` when the entry has no known ID)
  Line 3   grid coordinate (Excel-style column letter + row number,
           e.g. `B3`)

A bottom legend lists every brick color used, its Bricklink ID, count,
and a swatch — that doubles as the SCAL-05 brick-count / shopping list.

Cell geometry follows real Lego brick dimensions per
https://upload.wikimedia.org/wikipedia/commons/1/1a/Lego_dimensions.svg:
brick depth 7.8 mm, brick height 9.6 mm. Cells are therefore taller than
wide by `LEGO_UNIT_ASPECT = 9.6 / 7.8 ≈ 1.231`. The minimum cell width
is 48 px (legibility floor); the default is 78 px because it yields an
exact 96-px cell height at the brick aspect ratio.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from .lego_colors import LEGO_COLORS, LegoColor

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

log = logging.getLogger("legome.build_plan")

LEGO_UNIT_W_MM = 7.8
LEGO_UNIT_H_MM = 9.6
LEGO_UNIT_ASPECT = LEGO_UNIT_H_MM / LEGO_UNIT_W_MM  # ~1.2308

MIN_CELL_W_PX = 48
# Default cell width picks 100 so four text lines (coord, RGB, name, ID) each
# get ~30 px of vertical space at the real-brick aspect ratio (cell height
# 100 * 9.6/7.8 = ~123 px). 78 stayed legible for three lines but became
# cramped after RGB was added as a fourth line.
DEFAULT_CELL_W_PX = 100

GRID_LINE_COLOR_BGR = (40, 40, 40)
MARGIN_BG_BGR = (245, 245, 245)
MARGIN_FG_BGR = (20, 20, 20)
LEGEND_BG_BGR = (255, 255, 255)


def _excel_column(idx: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA', ..."""
    s = ""
    n = idx
    while True:
        s = chr(ord("A") + n % 26) + s
        n = n // 26 - 1
        if n < 0:
            return s


def _luminance(b: int, g: int, r: int) -> float:
    return 0.114 * b + 0.587 * g + 0.299 * r


def _text_color(bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    return (0, 0, 0) if _luminance(*bgr) >= 128 else (255, 255, 255)


def _fit_text(text: str, max_w: int, max_h: int, font, thickness: int) -> tuple[str, float]:
    """Pick the largest font scale (and possibly truncate text) so it fits."""
    import cv2

    if not text:
        return "", 0.5
    for scale in (0.7, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3):
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        if tw <= max_w and th <= max_h:
            return text, scale
    # Couldn't fit at any scale — truncate with ellipsis at minimum scale.
    scale = 0.3
    truncated = text
    while truncated:
        candidate = truncated + ".."
        (tw, _), _ = cv2.getTextSize(candidate, font, scale, thickness)
        if tw <= max_w:
            return candidate, scale
        truncated = truncated[:-1]
    return "?", scale


def _build_color_lookup() -> dict[tuple[int, int, int], LegoColor]:
    """Map BGR -> LegoColor for fast per-cell ID lookup."""
    return {(c.rgb[2], c.rgb[1], c.rgb[0]): c for c in LEGO_COLORS}


def _draw_cell(
    canvas, top_left, cell_w, cell_h, bgr, color: LegoColor | None, coord: str
) -> None:
    """Draw a single brick cell with 4 stacked text rows.

    Line order from the TOP of the cell:
      1. coordinate     (e.g. "A1")    — where the brick goes
      2. RGB triple     (e.g. "27,42,52") — visual confirmation of the color
      3. color name     (e.g. "Black")   — what to ask for
      4. Bricklink ID   (e.g. "11")      — what to type into Bricklink

    The order is intentional: coord at the top mirrors how a build plan
    is normally read (location -> color identity). Per user request.
    """
    import cv2

    x0, y0 = top_left
    x1, y1 = x0 + cell_w, y0 + cell_h
    cv2.rectangle(canvas, (x0, y0), (x1, y1), tuple(int(c) for c in bgr), thickness=-1)
    cv2.rectangle(canvas, (x0, y0), (x1, y1), GRID_LINE_COLOR_BGR, thickness=1)

    fg = _text_color((int(bgr[0]), int(bgr[1]), int(bgr[2])))
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1

    n_lines = 4
    line_h = cell_h // n_lines
    pad = 2
    text_max_w = cell_w - 2 * pad
    text_max_h = line_h - 2 * pad

    name = color.name if color is not None else "?"
    bid = str(color.bricklink_id) if (color is not None and color.bricklink_id is not None) else "?"
    # `bgr` is BGR; humans read RGB, so flip for the label.
    rgb_label = f"{int(bgr[2])},{int(bgr[1])},{int(bgr[0])}"

    lines = (coord, rgb_label, name, bid)
    for line_idx, text in enumerate(lines):
        fitted, scale = _fit_text(text, text_max_w, text_max_h, font, thickness)
        (tw, th), _baseline = cv2.getTextSize(fitted, font, scale, thickness)
        cx = x0 + (cell_w - tw) // 2
        cy = y0 + line_h * line_idx + (line_h + th) // 2
        cv2.putText(canvas, fitted, (cx, cy), font, scale, fg, thickness, cv2.LINE_AA)


def _draw_axes(canvas, grid_origin, cols, rows, cell_w, cell_h, margin) -> None:
    import cv2

    font = cv2.FONT_HERSHEY_SIMPLEX
    gx0, gy0 = grid_origin

    # Column letters along the top.
    for col in range(cols):
        label = _excel_column(col)
        (tw, th), _ = cv2.getTextSize(label, font, 0.5, 1)
        cx = gx0 + col * cell_w + (cell_w - tw) // 2
        cy = gy0 - max(8, (margin - th) // 2)
        cv2.putText(canvas, label, (cx, cy), font, 0.5, MARGIN_FG_BGR, 1, cv2.LINE_AA)

    # Row numbers along the left side.
    for row in range(rows):
        label = str(row + 1)
        (tw, th), _ = cv2.getTextSize(label, font, 0.5, 1)
        cx = gx0 - max(8, tw + 4)
        cy = gy0 + row * cell_h + (cell_h + th) // 2
        cv2.putText(canvas, label, (cx, cy), font, 0.5, MARGIN_FG_BGR, 1, cv2.LINE_AA)


def _draw_legend(canvas, origin, width, counts, color_for) -> int:
    """Render the brick-count legend and return its pixel height."""
    import cv2

    x0, y0 = origin
    font = cv2.FONT_HERSHEY_SIMPLEX
    row_h = 24
    swatch_w = 28
    pad = 10
    header = "brick    id   count  color name"
    cv2.putText(canvas, header, (x0 + pad, y0 + row_h - 4), font, 0.5, MARGIN_FG_BGR, 1, cv2.LINE_AA)
    cv2.line(canvas, (x0, y0 + row_h), (x0 + width, y0 + row_h), MARGIN_FG_BGR, 1)

    y = y0 + row_h
    sorted_items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for bgr, count in sorted_items:
        color = color_for.get(bgr)
        name = color.name if color is not None else "(unknown)"
        bid = str(color.bricklink_id) if (color is not None and color.bricklink_id is not None) else "?"
        cv2.rectangle(
            canvas, (x0 + pad, y + 4), (x0 + pad + swatch_w, y + row_h - 4),
            tuple(int(c) for c in bgr), thickness=-1,
        )
        cv2.rectangle(
            canvas, (x0 + pad, y + 4), (x0 + pad + swatch_w, y + row_h - 4),
            GRID_LINE_COLOR_BGR, 1,
        )
        text = f"     {bid:>4}   {count:>5}  {name}"
        cv2.putText(canvas, text, (x0 + pad + swatch_w + 6, y + row_h - 6), font, 0.5, MARGIN_FG_BGR, 1, cv2.LINE_AA)
        y += row_h

    return int(y - y0)


def render_build_plan(
    quantized_bgr: np.ndarray,
    *,
    cell_w_px: int = DEFAULT_CELL_W_PX,
    margin: int = 60,
    show_legend: bool = True,
) -> np.ndarray:
    """Return an annotated PNG-ready build plan for a quantized mosaic.

    Each input pixel becomes one brick cell at real Lego aspect ratio
    (`cell_w_px` wide, `round(cell_w_px * 9.6 / 7.8)` tall). The cell shows
    the color name, Bricklink ID, and Excel-style grid coordinate.

    Args:
        quantized_bgr: HxWx3 uint8 BGR mosaic — typically the output of
            `legome.processor.apply_palette`.
        cell_w_px: cell width in pixels. Minimum 48 (legibility floor).
        margin: margin in pixels around the grid; holds the row/column
            axis labels.
        show_legend: include the brick-count legend below the grid.
    """
    import cv2
    import numpy as np

    if quantized_bgr.dtype != np.uint8 or quantized_bgr.ndim != 3 or quantized_bgr.shape[2] != 3:
        raise ValueError("quantized_bgr must be HxWx3 uint8")
    if cell_w_px < MIN_CELL_W_PX:
        raise ValueError(
            f"cell_w_px {cell_w_px} below minimum {MIN_CELL_W_PX} (legibility floor)"
        )

    rows, cols, _ = quantized_bgr.shape
    cell_h_px = round(cell_w_px * LEGO_UNIT_ASPECT)
    grid_w = cols * cell_w_px
    grid_h = rows * cell_h_px
    color_for = _build_color_lookup()
    # PERF-08: O(N+M) numpy unique replaces O(N) Python tuple-keyed Counter.
    flat = quantized_bgr.reshape(-1, 3)
    uniq, uniq_counts = np.unique(flat, axis=0, return_counts=True)
    counts: Counter[tuple[int, int, int]] = Counter(
        {(int(b), int(g), int(r)): int(c) for (b, g, r), c in zip(uniq, uniq_counts, strict=True)}
    )

    legend_rows = (len(counts) + 1) if show_legend else 0
    legend_h = legend_rows * 24 + (20 if show_legend else 0)

    canvas_w = margin * 2 + grid_w
    canvas_h = margin * 2 + grid_h + legend_h
    canvas = np.full((canvas_h, canvas_w, 3), MARGIN_BG_BGR, dtype=np.uint8)

    grid_origin = (margin, margin)
    for row in range(rows):
        for col in range(cols):
            px = quantized_bgr[row, col]
            bgr: tuple[int, int, int] = (int(px[0]), int(px[1]), int(px[2]))
            color = color_for.get(bgr)
            coord = f"{_excel_column(col)}{row + 1}"
            top_left = (grid_origin[0] + col * cell_w_px, grid_origin[1] + row * cell_h_px)
            _draw_cell(canvas, top_left, cell_w_px, cell_h_px, bgr, color, coord)

    _draw_axes(canvas, grid_origin, cols, rows, cell_w_px, cell_h_px, margin)

    if show_legend:
        legend_origin = (margin, grid_origin[1] + grid_h + 20)
        cv2.rectangle(
            canvas,
            (legend_origin[0], legend_origin[1]),
            (legend_origin[0] + grid_w, legend_origin[1] + legend_rows * 24),
            LEGEND_BG_BGR, thickness=-1,
        )
        _draw_legend(canvas, legend_origin, grid_w, counts, color_for)

    log.info("build plan: %dx%d cells, %dx%d px canvas, %d distinct bricks",
             cols, rows, canvas_w, canvas_h, len(counts))
    return canvas
