"""Integration test: run the full pipeline on example/input.jpg.

Validates that:
  1. The CLI processes the bundled example image end-to-end.
  2. Every pixel in the output belongs to the loaded palette.
  3. A reasonable fraction of palette colors map to real Lego bricks.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from legome.cli import main as cli_main
from legome.lego_colors import coverage
from legome.palette import default_palette_path, load_palette
from legome.processor import apply_palette, output_pixels_in_palette

REPO = Path(__file__).resolve().parent.parent
EXAMPLE_INPUT = REPO / "example" / "input.jpg"


def _example_image():
    if not EXAMPLE_INPUT.is_file():
        pytest.skip(f"example image missing: {EXAMPLE_INPUT}")
    img = cv2.imread(str(EXAMPLE_INPUT))
    if img is None:
        pytest.skip(f"could not decode example image: {EXAMPLE_INPUT}")
    return img


def test_example_image_runs_through_processor():
    img = _example_image()
    pal = load_palette(default_palette_path())
    out = apply_palette(img, pal)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_example_output_only_palette_colors():
    img = _example_image()
    pal = load_palette(default_palette_path())
    out = apply_palette(img, pal)
    assert output_pixels_in_palette(out, pal), "output contains pixels outside the declared palette"


def test_example_palette_buildable_in_lego():
    pal = load_palette(default_palette_path())
    cov = coverage(pal.unique_colors(), threshold=40.0)
    assert cov >= 0.5, (
        f"only {cov:.2%} of the bundled palette matches real Lego bricks — "
        "users would not be able to source most pieces"
    )


def test_cli_end_to_end_on_example(tmp_path):
    out = tmp_path / "out.jpg"
    rc = cli_main([str(EXAMPLE_INPUT), str(out), "--no-display"])
    assert rc == 0
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    pal = load_palette(default_palette_path())
    # JPEG is lossy; verify on the in-memory recolored buffer instead by
    # reprocessing the input and ensuring at least the in-memory result obeys.
    src = cv2.imread(str(EXAMPLE_INPUT))
    recolored = apply_palette(src, pal)
    assert output_pixels_in_palette(recolored, pal)


def test_apply_palette_preserves_hue_on_example():
    """Color information must survive quantization.

    A grayscale-colormap approach would collapse a red pixel and a blue pixel
    with the same luminance to the same brick. We assert that an image with
    distinct color regions keeps distinct output colors after quantization.
    """
    pal = load_palette(default_palette_path())
    swatch = np.zeros((4, 4, 3), dtype=np.uint8)
    swatch[..., :] = (0, 0, 200)  # pure red (BGR)
    out_red = apply_palette(swatch, pal)
    swatch[..., :] = (200, 0, 0)  # pure blue (BGR)
    out_blue = apply_palette(swatch, pal)
    assert not np.array_equal(out_red, out_blue), (
        "quantizer collapsed red and blue to the same palette color"
    )


def test_apply_palette_matches_naive_nearest_reference():
    """Verify the vectorized quantizer matches a naive nearest-neighbor loop."""
    pal = load_palette(default_palette_path())
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(6, 6, 3), dtype=np.uint8)
    out = apply_palette(img, pal)

    pal_bgr = np.array([(b, g, r) for r, g, b in pal.unique_colors()], dtype=np.int32)
    expected = np.empty_like(img)
    for y in range(img.shape[0]):
        for x in range(img.shape[1]):
            px = img[y, x].astype(np.int32)
            d2 = ((pal_bgr - px) ** 2).sum(axis=1)
            expected[y, x] = pal_bgr[d2.argmin()].astype(np.uint8)
    assert np.array_equal(out, expected)
