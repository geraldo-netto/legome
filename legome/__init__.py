"""Legome package — apply a Lego color palette to images.

Public API:
    load_palette(path) -> Palette
    apply_palette(image, palette) -> ndarray
"""

from .palette import Palette, load_palette
from .processor import apply_palette, build_lut

__version__ = "0.2.0"
__all__ = ["Palette", "load_palette", "apply_palette", "build_lut", "__version__"]
