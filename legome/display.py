"""Optional GUI display, with a headless guard.

Separated so CLI / batch jobs can skip display without importing GUI deps
(TODO DEC-01, CONC-02, REL-06).
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

WAIT_MS = 100
WINDOW_TITLE = "LegoMe - recolored image"
# Target preview-window size. The image is scaled so that it fits inside this
# box while preserving its aspect ratio, *whether the source is smaller or
# larger* — block-pixel mosaics upscaled, oversized build plans downscaled.
TARGET_PREVIEW_W = 1400
TARGET_PREVIEW_H = 1000
# Legacy aliases kept for tests / external callers.
MAX_INITIAL_W = TARGET_PREVIEW_W
MAX_INITIAL_H = TARGET_PREVIEW_H
MIN_PREVIEW_AXIS_PX = min(TARGET_PREVIEW_W, TARGET_PREVIEW_H)


def has_display() -> bool:
    """Best-effort check for a usable display environment."""
    if os.name == "nt" or os.name == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def show_image(image, title: str = WINDOW_TITLE, wait_ms: int = WAIT_MS) -> bool:
    """Show image in a window; return True if displayed, False if skipped.

    Skips when no display is available or when OpenCV's GUI backend is missing.
    Closes on `q` keypress or window close.
    """
    if not has_display():
        log.info("no display detected, skipping image preview")
        return False
    try:
        import cv2
    except ImportError:
        log.warning("cv2 unavailable, skipping image preview")
        return False
    try:
        # WINDOW_NORMAL lets the user resize; WINDOW_KEEPRATIO preserves the
        # image's aspect ratio so it always fills the window edge-to-edge
        # without distortion. Some OpenCV GUI backends (notably the Qt build
        # used on Linux) only scale the displayed image *down* when the
        # window shrinks; they do not interpolate when the window grows past
        # the image's native size. The fix is to bake the upscale into the
        # pixel data before imshow — we render the image at the target
        # preview size up front, then cv2 only needs to downscale on user
        # resize (which it does reliably).
        cv2.namedWindow(title, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        h, w = image.shape[:2]
        scale = min(TARGET_PREVIEW_W / max(w, 1), TARGET_PREVIEW_H / max(h, 1))
        target_w = max(1, int(round(w * scale)))
        target_h = max(1, int(round(h * scale)))
        if scale > 1.0:
            # Upscale block-pixel mosaics with nearest-neighbor so adjacent
            # bricks stay sharp.
            image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        elif scale < 1.0:
            # Downscale oversized build plans with area filtering — keeps
            # the per-cell text legible at the smaller size.
            image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
        cv2.resizeWindow(title, target_w, target_h)
        cv2.imshow(title, image)
        while cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) >= 1:
            key = cv2.waitKey(wait_ms)
            if (key & 0xFF) == ord("q"):
                break
        cv2.destroyAllWindows()
        return True
    except cv2.error as exc:  # pragma: no cover - depends on GUI backend
        log.warning("GUI backend unavailable: %s", exc)
        return False
