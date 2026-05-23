#!/usr/bin/env python3
"""SCAL-07: regenerate the bundled real-Lego palette files from `legome.lego_colors`.

Run manually after editing `legome/lego_colors.py`:

    python3 scripts/build_palettes.py

The two outputs are committed alongside the source-of-truth Python module:

    legome/palettes/lego_bricks.json   (canonical legome format)
    legome/palettes/lego_bricks.gpl    (GIMP cross-tool format)

The legacy `legome/palettes/lego.json` (112-color colormap LUT) is left
untouched — it is a different palette and still ships for callers that
loaded it explicitly via `--palette`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from legome.lego_colors import LEGO_COLORS  # noqa: E402  (path-tweak first)

OUT_DIR = ROOT / "legome" / "palettes"


def write_json() -> Path:
    payload = {
        "name": "lego-bricks",
        "description": (
            "Solid Lego brick colors — derived from legome.lego_colors.LEGO_COLORS. "
            "Regenerate via `python3 scripts/build_palettes.py`."
        ),
        "source": "legome.lego_colors.LEGO_COLORS",
        "colors": [list(c.rgb) for c in LEGO_COLORS],
        "metadata": [
            {
                "name": c.name,
                "aliases": list(c.aliases),
                "bricklink_id": c.bricklink_id,
            }
            for c in LEGO_COLORS
        ],
    }
    path = OUT_DIR / "lego_bricks.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def write_gpl() -> Path:
    lines = [
        "GIMP Palette",
        "Name: Lego Bricks",
        "Columns: 4",
        "# Generated from legome.lego_colors.LEGO_COLORS",
        "# Re-run scripts/build_palettes.py to update.",
        "#",
    ]
    # GIMP .gpl rows are `R G B name`. Inline comments after the name are
    # non-standard and confuse some loaders, so we keep the row pure and
    # ship the Bricklink IDs only in the JSON sidecar.
    for c in LEGO_COLORS:
        r, g, b = c.rgb
        lines.append(f"{r:3d} {g:3d} {b:3d} {c.name}")
    path = OUT_DIR / "lego_bricks.gpl"
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = write_json()
    gpl_path = write_gpl()
    print(f"wrote {json_path} ({len(LEGO_COLORS)} colors)")
    print(f"wrote {gpl_path}")


if __name__ == "__main__":
    main()
