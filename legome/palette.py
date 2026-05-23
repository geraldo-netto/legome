"""Palette loading and representation.

A palette is an ordered collection of RGB colors used by the nearest-neighbor
quantizer in `legome.processor`. Palette files are JSON; two layouts are
accepted:

  {"name": str, "colors": [[r,g,b], ...]}              # arbitrary length
  {"name": str, "lut": [[r,g,b], ... x256]}            # legacy 256-entry LUT

Either form is loaded into a `Palette` whose `.colors` is the canonical
representation. The legacy 256-entry form is retained so an existing JSON
file (e.g. a colormap generated for cv2.applyColorMap) can be re-used as a
quantization palette without conversion.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

RGB = tuple[int, int, int]
LUT_SIZE = 256


@dataclass(frozen=True)
class Palette:
    name: str
    colors: tuple[RGB, ...]
    description: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        if not self.colors:
            raise ValueError(f"palette '{self.name}' must contain at least one color")
        for i, c in enumerate(self.colors):
            if len(c) != 3:
                raise ValueError(
                    f"palette '{self.name}' entry {i} must be an RGB triple, "
                    f"got {len(c)}-tuple: {c}"
                )
            for ch in c:
                if not isinstance(ch, int) or not (0 <= ch <= 255):
                    raise ValueError(
                        f"palette '{self.name}' entry {i} channel out of range: {c}"
                    )

    def unique_colors(self) -> list[RGB]:
        seen = set()
        out: list[RGB] = []
        for c in self.colors:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    @property
    def lut(self) -> tuple[RGB, ...]:
        """Legacy alias for `.colors` (only valid for 256-entry palettes)."""
        if len(self.colors) != LUT_SIZE:
            raise ValueError(
                f"palette '{self.name}' has {len(self.colors)} colors, "
                f"`.lut` requires exactly {LUT_SIZE}"
            )
        return self.colors


def _coerce_colors(raw: Iterable[Sequence[int]]) -> tuple[RGB, ...]:
    out: list[RGB] = []
    for i, entry in enumerate(raw):
        if len(entry) != 3:
            raise ValueError(
                f"palette entry {i} must be an RGB triple, "
                f"got {len(entry)}-tuple: {tuple(entry)}"
            )
        r, g, b = entry
        out.append((int(r), int(g), int(b)))
    return tuple(out)


_coerce_lut = _coerce_colors  # backward-compat alias for any external users.


def load_palette(path: str | Path) -> Palette:
    """Load palette from JSON file (either `colors` or legacy `lut` layout)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"palette file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"palette JSON root must be object: {p}")
    if "name" not in data:
        raise ValueError(f"palette JSON missing 'name': {p}")
    if "colors" in data:
        colors = _coerce_colors(data["colors"])
    elif "lut" in data:
        colors = _coerce_colors(data["lut"])
    else:
        raise ValueError(f"palette JSON missing 'colors' or 'lut': {p}")
    return Palette(
        name=str(data["name"]),
        colors=colors,
        description=str(data.get("description", "")),
        source=str(data.get("source", "")),
    )


def default_palette_path() -> Path:
    """Return path to the bundled `legome/palettes/lego.json`.

    Bundled inside the package so an installed wheel can still locate it.
    """
    return Path(__file__).resolve().parent / "palettes" / "lego.json"


def lego_palette() -> Palette:
    """Build a Palette from the bundled `lego_colors.LEGO_COLORS` DB.

    This is the default palette used by the CLI: every output pixel is
    guaranteed to map to a real Lego brick color.
    """
    from .lego_colors import LEGO_COLORS

    return Palette(
        name="lego-bricks",
        colors=tuple(c.rgb for c in LEGO_COLORS),
        description="Solid Lego brick colors (Bricklink/Rebrickable canonical).",
        source="legome.lego_colors.LEGO_COLORS",
    )
