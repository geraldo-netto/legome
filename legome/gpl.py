"""SCAL-06: GIMP `.gpl` palette loader.

`.gpl` is the de-facto cross-tool plain-text palette format (GIMP, Krita,
Inkscape, Aseprite). Layout:

    GIMP Palette
    Name: My Palette
    Columns: 4
    #
    27  42  52 Black
    242 243 242 White
    ...

Each color row is `R\\sG\\sB\\sname` with arbitrary whitespace. `Name:`,
`Columns:`, and `#`-prefixed lines are metadata / comments.

The loader returns a `legome.palette.Palette` so the rest of the pipeline
treats `.gpl` exactly like a JSON palette.
"""

from __future__ import annotations

from pathlib import Path

from .palette import Palette


def _parse_color_row(p: Path, raw: str, line: str) -> tuple[tuple[int, int, int], str]:
    """Parse one `R G B [name]` data row from a `.gpl` file."""
    parts = line.split(None, 3)
    if len(parts) < 3:
        raise ValueError(
            f"{p}: malformed color row (need at least 3 channels): {raw!r}"
        )
    try:
        r, g, b = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError as exc:
        raise ValueError(f"{p}: non-integer channel in row {raw!r}") from exc
    for ch in (r, g, b):
        if not 0 <= ch <= 255:
            raise ValueError(
                f"{p}: channel out of range in row {raw!r}; must be 0..255"
            )
    color_name = parts[3].strip() if len(parts) >= 4 else ""
    return (r, g, b), color_name


def _parse_palette_entries(
    p: Path, body_lines: list[str]
) -> tuple[str, list[tuple[int, int, int]], list[str]]:
    name = p.stem
    colors: list[tuple[int, int, int]] = []
    color_names: list[str] = []
    for raw in body_lines:
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("name:"):
            extracted = line.split(":", 1)[1].strip()
            if extracted:
                name = extracted
            continue
        if lower.startswith("columns:"):
            continue
        rgb, cname = _parse_color_row(p, raw, line)
        colors.append(rgb)
        color_names.append(cname)
    return name, colors, color_names


def load_gpl(path: str | Path) -> Palette:
    """Load a GIMP `.gpl` palette into a `Palette`."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"palette file not found: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "GIMP Palette":
        raise ValueError(
            f"{p}: not a GIMP palette (first line must be 'GIMP Palette')"
        )

    name, colors, color_names = _parse_palette_entries(p, lines[1:])

    if not colors:
        raise ValueError(f"{p}: no color rows found")

    description = (
        f"Loaded from GIMP palette `{p.name}`. "
        f"Named entries: {', '.join(n for n in color_names if n)}"
        if any(color_names)
        else f"Loaded from GIMP palette `{p.name}`."
    )
    return Palette(
        name=name,
        colors=tuple(colors),
        description=description,
        source=str(p),
    )
