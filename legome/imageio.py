"""Image-format detection and extension reconciliation.

REL-13: trust file content, not filename. If a `.png`-named file is actually
a JPEG, log a warning and keep going — the underlying OpenCV decoder works
from content, so this is purely a diagnostic.

REL-14: PNG is the canonical output format for quantized mosaics (lossless).
If the user picks an unsupported extension, fall back to PNG with a warning.
If the user picks JPEG, warn that the encoder will shift palette colors.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("legome.imageio")

SUPPORTED_OUTPUT_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
)
LOSSY_OUTPUT_EXTENSIONS = frozenset({".jpg", ".jpeg"})

_EXT_TO_FORMAT = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".webp": "webp",
    ".gif": "gif",
}


def detect_format(path: Path) -> str | None:
    """Return the image format ("jpeg"/"png"/...) from the file's magic bytes.

    Returns None if the format is unknown / file is empty.
    """
    try:
        with path.open("rb") as fh:
            head = fh.read(16)
    except OSError:
        return None
    if len(head) >= 8 and head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(head) >= 3 and head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(head) >= 2 and head[:2] == b"BM":
        return "bmp"
    if len(head) >= 4 and head[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if len(head) >= 6 and head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def reconcile_input_extension(path: Path) -> str | None:
    """Compare the file extension to the magic-byte format and log on mismatch.

    Returns the detected format string (or None if unknown). The caller can
    still try to decode; this is diagnostic only because OpenCV's `imread`
    auto-detects from content.
    """
    actual = detect_format(path)
    ext = path.suffix.lower()
    expected = _EXT_TO_FORMAT.get(ext)
    if actual is None:
        log.warning(
            "input %s: could not identify image format from magic bytes",
            path,
        )
        return None
    if expected is None:
        log.warning(
            "input %s has %s content but extension '%s' is not a known image "
            "extension — trusting content",
            path,
            actual,
            ext,
        )
    elif expected != actual:
        log.warning(
            "input %s has %s content but extension '%s' would suggest %s — "
            "trusting content (extension is wrong)",
            path,
            actual,
            ext,
            expected,
        )
    return actual


def reconcile_output_extension(path: Path) -> Path:
    """Return a (possibly rewritten) output path with a safe extension.

    - Unsupported extension → switched to `.png` (lossless) with a warning.
    - Lossy extension (.jpg/.jpeg) → kept but warned about palette drift.
    """
    ext = path.suffix.lower()
    if ext not in SUPPORTED_OUTPUT_EXTENSIONS:
        new = path.with_suffix(".png")
        log.warning(
            "output extension '%s' is not supported; writing PNG to %s instead",
            ext or "(none)",
            new,
        )
        return new
    if ext in LOSSY_OUTPUT_EXTENSIONS:
        log.warning(
            "output %s uses lossy JPEG encoding — quantized palette colors "
            "may shift on round-trip; prefer .png for mosaic builds",
            path,
        )
    return path
