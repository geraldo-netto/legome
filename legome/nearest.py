"""ARCH-02: one nearest-neighbor RGB core, shared by every caller.

Before this module the squared-Euclidean argmin was implemented three
times independently (the quantizer, `closest_lego_color`, and
`match_palette_to_lego`). They now all route through here so the distance
math lives in exactly one place.

Lazy numpy import so importing the package stays dependency-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np


def _squared_dist_matrix(points, refs) -> np.ndarray:
    """(N,K) x (M,K) -> (N,M) int32 matrix of squared Euclidean distances.

    int32 is safe: max per-channel diff is 255, so a 3-channel sum tops out
    at 3 * 255^2 = 195075, well within int32.
    """
    import numpy as np

    pts = np.asarray(points, dtype=np.int32)
    ref = np.asarray(refs, dtype=np.int32)
    diff = pts[:, None, :] - ref[None, :, :]
    d2: np.ndarray = (diff * diff).sum(axis=2)
    return d2


def nearest_indices(points, refs) -> np.ndarray:
    """Return the argmin ref index for each point. No sqrt (hot path)."""
    idx: np.ndarray = _squared_dist_matrix(points, refs).argmin(axis=1)
    return idx


def nearest(points, refs) -> tuple[np.ndarray, np.ndarray]:
    """Return (idx, distance) — argmin ref index plus the Euclidean distance."""
    import numpy as np

    d2 = _squared_dist_matrix(points, refs)
    idx = d2.argmin(axis=1)
    dist = np.sqrt(d2[np.arange(d2.shape[0]), idx].astype(np.float64))
    return idx, dist
