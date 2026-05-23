"""SCAL-04: resize input images before quantization.

Two input forms:
  * Explicit "WxH" — e.g. `--resize 320x320`.
  * Named preset — e.g. `--resize a4` for a brick-grid size that matches A4
    paper at a typical 1x1-stud-per-cell density.

Preset sizes are stud counts. Common mosaic baseplates / framed prints:
  * `48x48`  — a single 48x48 baseplate (set 11010).
  * `a4`     — 32x48 studs (portrait), matches an A4 framed print roughly.
  * `a3`     — 48x64 studs.
  * `a2`     — 64x96 studs.
  * `a1`     — 96x128 studs.
  * `mosaic` — 128x128 studs (large hobbyist mosaic).

`resize_image` uses OpenCV's INTER_AREA interpolation which is the canonical
choice for downscaling photographic content (preserves luminance, avoids
aliasing).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

PAPER_SIZES: dict[str, tuple[int, int]] = {
    "48x48": (48, 48),
    "a4": (32, 48),
    "a3": (48, 64),
    "a2": (64, 96),
    "a1": (96, 128),
    "mosaic": (128, 128),
}

_WXH_RE = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*$")


def parse_resize_arg(arg: str) -> tuple[int, int]:
    """Parse a `--resize` argument into a `(width, height)` pair.

    Accepts:
      * `"WxH"` literal (case-insensitive separator).
      * A preset name from `PAPER_SIZES`.

    Raises `ValueError` on unrecognised input.
    """
    key = arg.strip().lower()
    if key in PAPER_SIZES:
        return PAPER_SIZES[key]
    m = _WXH_RE.match(arg)
    if not m:
        raise ValueError(
            f"--resize argument {arg!r} must be 'WxH' (e.g. 320x320) or "
            f"one of {sorted(PAPER_SIZES)}"
        )
    w, h = int(m.group(1)), int(m.group(2))
    if w < 1 or h < 1:
        raise ValueError(f"--resize dimensions must be >= 1, got {w}x{h}")
    return (w, h)


def resize_image(image: np.ndarray, target: tuple[int, int]) -> np.ndarray:
    """Resize `image` (HxWx3 uint8) to `(width, height)` using INTER_AREA."""
    import cv2

    width, height = target
    if width < 1 or height < 1:
        raise ValueError(f"resize target must be positive, got {target}")
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
