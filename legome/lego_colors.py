"""Authoritative reference list of solid Lego brick colors with RGB values.

Each entry: (canonical name, RGB tuple, optional aliases). RGB values are
the *brick* color as published by LEGO / Bricklink, not printed-on-paper
or scan-matched values.

Sources (well-known, cross-referenced — see the README for the full list,
and TODO.md DOC-03 for tracking per-color Bricklink IDs):
- LEGO Customer Service color chart (solid colors, current catalog).
- Bricklink color guide: https://www.bricklink.com/catalogColors.asp
- Rebrickable color database: https://rebrickable.com/colors/

`closest_lego_color(rgb)` returns the closest entry by Euclidean RGB
distance; `match_palette_to_lego(colors, threshold)` flags palette entries
that lack a buildable Lego match.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

RGB = tuple[int, int, int]


class LegoColor(NamedTuple):
    name: str
    rgb: RGB
    aliases: tuple[str, ...] = ()
    bricklink_id: int | None = None  # DOC-03: Bricklink "colorID" if known.


# Subset of solid, currently-or-historically produced Lego colors. Not
# exhaustive; covers the common solid palette used for mosaic builds.
#
# `aliases` captures catalog naming differences (e.g. LEGO's internal name
# vs Bricklink's name) for the same physical brick, so the DB has one entry
# per distinct RGB and `closest_lego_color` returns an unambiguous result.
#
# `bricklink_id` (DOC-03) is the canonical Bricklink color ID — useful for
# linking out to https://www.bricklink.com/catalogItemColors.asp?ID=N when
# generating shopping lists. Only the well-known core IDs are filled in
# here; entries without a confirmed ID are left as None and tracked under
# TODO DOC-03 for verification against the live Bricklink table.
LEGO_COLORS: tuple[LegoColor, ...] = (
    LegoColor("Black", (27, 42, 52), bricklink_id=11),
    LegoColor("White", (242, 243, 242), bricklink_id=1),
    LegoColor("Bright Red", (196, 40, 28), aliases=("Red",), bricklink_id=5),
    LegoColor("Bright Blue", (13, 105, 172), aliases=("Blue",), bricklink_id=7),
    LegoColor("Bright Yellow", (245, 205, 47), aliases=("Yellow",), bricklink_id=3),
    LegoColor("Bright Green", (75, 151, 75), aliases=("Green",), bricklink_id=6),
    LegoColor("Dark Green", (40, 127, 70), bricklink_id=80),
    LegoColor("Earth Green", (39, 70, 44)),
    LegoColor("Dark Red", (123, 46, 47), bricklink_id=59),
    LegoColor("Reddish Brown", (105, 64, 39), bricklink_id=88),
    LegoColor("Medium Nougat", (175, 120, 76), bricklink_id=150),
    LegoColor("Nougat", (214, 145, 99), bricklink_id=28),
    LegoColor("Light Nougat", (245, 193, 137), bricklink_id=90),
    LegoColor("Brick Yellow", (215, 197, 153), aliases=("Tan",), bricklink_id=2),
    LegoColor("Dark Tan", (149, 138, 115), bricklink_id=69),
    LegoColor("Medium Stone Grey", (163, 162, 165), aliases=("Light Gray",), bricklink_id=9),
    LegoColor("Light Bluish Gray", (175, 181, 199), bricklink_id=86),
    LegoColor("Dark Stone Grey", (99, 95, 82), aliases=("Dark Gray",), bricklink_id=10),
    LegoColor("Dark Bluish Gray", (89, 93, 96), bricklink_id=85),
    LegoColor("Sand Blue", (116, 134, 156), bricklink_id=55),
    LegoColor("Medium Blue", (110, 153, 201), bricklink_id=42),
    LegoColor("Earth Blue", (32, 58, 86), aliases=("Dark Blue",), bricklink_id=63),
    LegoColor("Bright Light Blue", (159, 195, 233), bricklink_id=105),
    LegoColor("Light Royal Blue", (135, 192, 234), bricklink_id=87),
    LegoColor("Aqua", (179, 215, 209), bricklink_id=41),
    LegoColor("Dark Turquoise", (0, 138, 128), bricklink_id=39),
    LegoColor("Sand Green", (160, 188, 172), bricklink_id=48),
    LegoColor("Medium Lavender", (160, 110, 185), bricklink_id=157),
    LegoColor("Lavender", (205, 164, 222), bricklink_id=154),
    LegoColor("Bright Pink", (255, 158, 205), aliases=("Pink",), bricklink_id=23),
    LegoColor("Dark Pink", (200, 80, 155), bricklink_id=47),
    LegoColor("Magenta", (146, 57, 120), bricklink_id=71),
    LegoColor("Bright Purple", (164, 30, 99), aliases=("Purple",), bricklink_id=24),
    LegoColor("Dark Purple", (95, 38, 131), bricklink_id=89),
    LegoColor("Medium Orange", (255, 158, 24), bricklink_id=31),
    LegoColor("Bright Orange", (218, 133, 64), aliases=("Orange",), bricklink_id=4),
    LegoColor("Dark Orange", (168, 95, 28), bricklink_id=68),
    LegoColor("Coral", (255, 109, 119), bricklink_id=220),
    LegoColor("Salmon", (242, 112, 94), bricklink_id=25),
    LegoColor("Light Yellow", (251, 232, 144), bricklink_id=33),
    LegoColor("Bright Light Yellow", (255, 240, 130), bricklink_id=103),
    LegoColor("Bright Light Orange", (248, 187, 61), bricklink_id=110),
    LegoColor("Olive Green", (155, 154, 90), bricklink_id=155),
    LegoColor("Yellowish Green", (220, 232, 116), bricklink_id=158),
    LegoColor("Lime", (188, 233, 27), bricklink_id=34),
    LegoColor("Medium Azure", (54, 174, 191), bricklink_id=156),
    LegoColor("Dark Azure", (7, 139, 201), bricklink_id=153),
    LegoColor("Light Aqua", (173, 195, 192), bricklink_id=152),
    LegoColor("Flame Yellowish Orange", (245, 159, 39)),
)


def bricklink_url(color: LegoColor) -> str | None:
    """Return the Bricklink catalog URL for the brick swatch, if `bricklink_id` is known."""
    if color.bricklink_id is None:
        return None
    return f"https://www.bricklink.com/catalogItemInv.asp?colorID={color.bricklink_id}"


def _assert_unique_rgbs() -> None:
    seen: dict = {}
    for c in LEGO_COLORS:
        if c.rgb in seen:
            raise RuntimeError(
                f"duplicate Lego RGB {c.rgb}: '{c.name}' and '{seen[c.rgb]}' — "
                "merge one as an alias"
            )
        seen[c.rgb] = c.name


_assert_unique_rgbs()


def _euclid_sq(a: RGB, b: RGB) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def closest_lego_color(rgb: RGB) -> tuple[LegoColor, float]:
    """Return (closest_lego_color, euclidean_distance) for `rgb`."""
    best = min(LEGO_COLORS, key=lambda lc: _euclid_sq(lc.rgb, rgb))
    dist = _euclid_sq(best.rgb, rgb) ** 0.5
    return best, dist


def match_palette_to_lego(
    palette_colors: Iterable[RGB], threshold: float = 40.0
) -> list[dict]:
    """For each palette color, return its closest Lego color and a match flag.

    PERF-06: vectorized via numpy broadcasting — one O(N*M) matrix op
    instead of N Python `min` loops over M items. Caller-visible output is
    unchanged.

    Returns list of dicts: {palette_rgb, lego_name, lego_rgb, distance, match}.
    """
    import numpy as np

    pal_list = [tuple(c) for c in palette_colors]
    if not pal_list:
        return []
    pal = np.array(pal_list, dtype=np.int32)
    lego = np.array([c.rgb for c in LEGO_COLORS], dtype=np.int32)
    diff = pal[:, None, :] - lego[None, :, :]
    d2 = (diff * diff).sum(axis=2)
    best_idx = d2.argmin(axis=1)
    best_d = np.sqrt(d2[np.arange(len(pal)), best_idx]).astype(float)

    out: list[dict] = []
    for i, c in enumerate(pal_list):
        lc = LEGO_COLORS[int(best_idx[i])]
        d = float(best_d[i])
        out.append(
            {
                "palette_rgb": c,
                "lego_name": lc.name,
                "lego_rgb": lc.rgb,
                "distance": d,
                "match": d <= threshold,
            }
        )
    return out


def coverage(palette_colors: Iterable[RGB], threshold: float = 40.0) -> float:
    """Fraction of palette colors that match a real Lego brick within `threshold`."""
    rows = match_palette_to_lego(palette_colors, threshold)
    if not rows:
        return 0.0
    return sum(1 for r in rows if r["match"]) / len(rows)
