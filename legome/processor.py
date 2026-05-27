"""Image processing — quantize an image to a palette of colors.

Each output pixel is the palette color with the smallest Euclidean distance
to the input pixel in RGB space. This preserves hue (a red pixel stays red,
a blue pixel stays blue) and constrains output to colors that exist as real
Lego bricks — both required for accurate mosaic reproduction.

Pure functions, no I/O. Lazy numpy/cv2 imports so the package is importable
in environments without those deps (TODO DEC-02).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .palette import LUT_SIZE, Palette

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

DEFAULT_CHUNK_PIXELS = 65536


def build_lut(palette: Palette) -> np.ndarray:
    """Build a (256,1,3) uint8 BGR LUT from a palette.

    Kept for users who want a classic OpenCV `cv2.LUT` / `applyColorMap`
    workflow with the bundled palette. `apply_palette` no longer uses it.
    """
    import numpy as np

    arr = np.array(palette.lut, dtype=np.uint8)
    if arr.shape != (LUT_SIZE, 3):
        raise ValueError(f"LUT shape mismatch: {arr.shape}")
    bgr = arr[:, ::-1]
    return bgr.reshape(LUT_SIZE, 1, 3)


def palette_bgr_unique(palette: Palette) -> np.ndarray:
    """Return (M,3) int32 array of unique palette colors in BGR order."""
    import numpy as np

    rgb = np.array(palette.colors, dtype=np.int32)
    bgr = rgb[:, ::-1]
    unique: np.ndarray = np.unique(bgr, axis=0)
    return unique


def _quantize_chunk(pixels_bgr_i32: np.ndarray, palette_bgr_i32: np.ndarray) -> np.ndarray:
    """For each pixel, return the palette color minimizing squared distance."""
    diff = pixels_bgr_i32[:, None, :] - palette_bgr_i32[None, :, :]
    d2 = (diff * diff).sum(axis=2)
    idx = d2.argmin(axis=1)
    nearest: np.ndarray = palette_bgr_i32[idx]
    return nearest


LUT3D_BREAKEVEN_PIXELS = 2_000_000
"""Switch-over point above which the precomputed 3D LUT is faster than chunked
broadcasting. Tuned empirically against the bundled Lego palette: at 1024x1024
broadcast wins (~5 s vs ~8 s); at 2048x2048 the LUT wins (~8 s vs ~18 s). See
benchmarks/RESULTS.md."""


def _build_3d_lut(palette_bgr: np.ndarray) -> np.ndarray:
    """Build a 256^3 BGR -> nearest-palette-color LUT (uint8, shape 256^3,3).

    Uses scipy.spatial.KDTree when available; falls back to chunked numpy
    broadcasting otherwise. Build cost: one-time ~0.5-2 s; lookup is then
    O(1) per pixel.
    """
    import numpy as np

    # Build a (256^3, 3) grid of all possible BGR values.
    grid = np.indices((256, 256, 256), dtype=np.int32).reshape(3, -1).T
    try:
        from scipy.spatial import KDTree

        _, idx = KDTree(palette_bgr).query(grid, k=1)
    except ImportError:  # pragma: no cover - scipy is a required dep, but keep a fallback
        idx = np.empty(grid.shape[0], dtype=np.int64)
        step = 65536
        for i in range(0, grid.shape[0], step):
            chunk = grid[i : i + step]
            d2 = ((chunk[:, None, :] - palette_bgr[None, :, :]) ** 2).sum(axis=2)
            idx[i : i + step] = d2.argmin(axis=1)
    lut: np.ndarray = palette_bgr[idx].astype(np.uint8)
    return lut


def apply_palette(
    image: np.ndarray,
    palette: Palette,
    chunk_pixels: int = DEFAULT_CHUNK_PIXELS,
    method: str = "auto",
) -> np.ndarray:
    """Quantize a BGR uint8 image to the nearest palette color per pixel.

    `method`:
      * `"auto"` (default) — pick the fastest implementation given the image
        size. For images above `LUT3D_BREAKEVEN_PIXELS` (1 MP), build a 256^3
        BGR -> palette LUT once and look up each pixel; for smaller images,
        use the chunked broadcast quantizer. Output is identical to within
        ties in the nearest-neighbor search.
      * `"broadcast"` — always use chunked numpy broadcasting (current path).
      * `"lut3d"` — always build the 256^3 LUT, even for small images.
    """
    import numpy as np

    if not isinstance(image, np.ndarray):
        raise TypeError(f"image must be numpy.ndarray, got {type(image).__name__}")
    if image.dtype != np.uint8:
        raise ValueError(f"image dtype must be uint8, got {image.dtype}")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"image must be HxWx3, got shape {image.shape}")
    if chunk_pixels < 1:
        raise ValueError(f"chunk_pixels must be >= 1, got {chunk_pixels}")
    if method not in {"auto", "broadcast", "lut3d"}:
        raise ValueError(f"method must be one of auto/broadcast/lut3d, got {method!r}")

    pal_bgr = palette_bgr_unique(palette)
    flat = image.reshape(-1, 3)
    n_pixels = flat.shape[0]

    use_lut = method == "lut3d" or (method == "auto" and n_pixels >= LUT3D_BREAKEVEN_PIXELS)
    if use_lut:
        lut = _build_3d_lut(pal_bgr)  # (16_777_216, 3) uint8
        # index by packed BGR -> single int per pixel
        idx = (
            (flat[:, 0].astype(np.uint32) << 16)
            | (flat[:, 1].astype(np.uint32) << 8)
            | flat[:, 2].astype(np.uint32)
        )
        result: np.ndarray = lut[idx].reshape(image.shape)
        return result

    out = np.empty_like(flat)
    for i in range(0, n_pixels, chunk_pixels):
        chunk = flat[i : i + chunk_pixels].astype(np.int32)
        out[i : i + chunk_pixels] = _quantize_chunk(chunk, pal_bgr).astype(np.uint8)
    return out.reshape(image.shape)


def output_pixels_in_palette(image: np.ndarray, palette: Palette) -> bool:
    """Return True iff every pixel in `image` (BGR uint8) is a palette color.

    PERF-05: vectorized via uint32 packing + `np.isin`. The cost is now
    O(N + M) numpy ops instead of an O(N) Python set comprehension that
    materializes one tuple per pixel.
    """
    import numpy as np

    flat = image.reshape(-1, 3).astype(np.uint32)
    packed = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
    pal_arr = np.array(
        [(b, g, r) for r, g, b in palette.colors], dtype=np.uint32
    )
    pal_packed = (pal_arr[:, 0] << 16) | (pal_arr[:, 1] << 8) | pal_arr[:, 2]
    return bool(np.isin(packed, pal_packed).all())
