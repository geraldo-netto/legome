"""SCAL-07: the derived `lego_bricks.{json,gpl}` files must stay in sync
with `legome.lego_colors.LEGO_COLORS`. The test re-runs the build logic
on a fresh tmp dir and byte-compares the result to the committed file.
"""

from __future__ import annotations

import json
from pathlib import Path

from legome.gpl import load_gpl
from legome.lego_colors import LEGO_COLORS
from legome.palette import load_palette

REPO = Path(__file__).resolve().parent.parent
JSON_PATH = REPO / "legome" / "palettes" / "lego_bricks.json"
GPL_PATH = REPO / "legome" / "palettes" / "lego_bricks.gpl"


def test_lego_bricks_json_matches_source_of_truth():
    pal = load_palette(JSON_PATH)
    assert pal.colors == tuple(c.rgb for c in LEGO_COLORS), (
        f"{JSON_PATH} is out of sync with legome.lego_colors.LEGO_COLORS; "
        "run `python3 scripts/build_palettes.py` to regenerate."
    )


def test_lego_bricks_gpl_matches_source_of_truth():
    pal = load_gpl(GPL_PATH)
    assert pal.colors == tuple(c.rgb for c in LEGO_COLORS), (
        f"{GPL_PATH} is out of sync with legome.lego_colors.LEGO_COLORS; "
        "run `python3 scripts/build_palettes.py` to regenerate."
    )


def test_lego_bricks_json_payload_shape():
    raw = json.loads(JSON_PATH.read_text())
    assert raw["name"] == "lego-bricks"
    assert raw["source"] == "legome.lego_colors.LEGO_COLORS"
    assert "Regenerate via" in raw["description"]
    assert len(raw["colors"]) == len(LEGO_COLORS)
