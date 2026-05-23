"""Unit tests for legome.processor."""

import numpy as np
import pytest

from legome.palette import LUT_SIZE, Palette, default_palette_path, load_palette
from legome.processor import apply_palette, build_lut, output_pixels_in_palette


def _gradient_palette():
    return Palette(name="grad", colors=tuple((i, i, i) for i in range(LUT_SIZE)))


def test_build_lut_shape_and_dtype():
    pal = _gradient_palette()
    lut = build_lut(pal)
    assert lut.shape == (LUT_SIZE, 1, 3)
    assert lut.dtype == np.uint8


def test_build_lut_swaps_rgb_to_bgr():
    # Palette stores RGB; build_lut must emit BGR for cv2.LUT.
    lut_data = [(10, 20, 30)] * LUT_SIZE
    pal = Palette(name="t", colors=tuple(lut_data))
    lut = build_lut(pal)
    # entry 0 should be (B, G, R) = (30, 20, 10)
    assert tuple(lut[0, 0]) == (30, 20, 10)


def test_apply_palette_identity_gradient():
    pal = _gradient_palette()
    img = np.full((4, 4, 3), 100, dtype=np.uint8)
    out = apply_palette(img, pal)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    # gradient palette is gray (i,i,i), so BGR(100,100,100) maps to (100,100,100)
    assert np.all(out == 100)


def test_apply_palette_real_lego_palette():
    pal = load_palette(default_palette_path())
    rng = np.random.default_rng(42)
    img = rng.integers(0, 256, size=(16, 16, 3), dtype=np.uint8)
    out = apply_palette(img, pal)
    assert output_pixels_in_palette(out, pal)


def test_apply_palette_rejects_non_ndarray():
    with pytest.raises(TypeError):
        apply_palette([[1, 2, 3]], _gradient_palette())


def test_apply_palette_rejects_wrong_dtype():
    img = np.zeros((2, 2, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="dtype"):
        apply_palette(img, _gradient_palette())


def test_apply_palette_rejects_wrong_shape():
    img = np.zeros((2, 2), dtype=np.uint8)
    with pytest.raises(ValueError, match="HxWx3"):
        apply_palette(img, _gradient_palette())


def test_apply_palette_rejects_wrong_channel_count():
    img = np.zeros((2, 2, 4), dtype=np.uint8)
    with pytest.raises(ValueError, match="HxWx3"):
        apply_palette(img, _gradient_palette())


def test_output_pixels_in_palette_negative():
    pal = _gradient_palette()
    img = np.full((2, 2, 3), 0, dtype=np.uint8)
    img[0, 0] = (1, 2, 3)  # not in gradient gray palette
    assert not output_pixels_in_palette(img, pal)


def test_output_pixels_in_palette_positive():
    pal = _gradient_palette()
    img = np.full((2, 2, 3), 100, dtype=np.uint8)  # (100,100,100) is in gradient
    assert output_pixels_in_palette(img, pal)


def test_apply_palette_rejects_bad_chunk_size():
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="chunk_pixels"):
        apply_palette(img, _gradient_palette(), chunk_pixels=0)


def test_apply_palette_small_chunk_matches_large_chunk():
    pal = _gradient_palette()
    rng = np.random.default_rng(7)
    img = rng.integers(0, 256, size=(8, 8, 3), dtype=np.uint8)
    big = apply_palette(img, pal, chunk_pixels=10_000)
    small = apply_palette(img, pal, chunk_pixels=3)
    assert np.array_equal(big, small)


@pytest.mark.slow
def test_apply_palette_method_choices_match():
    """PERF-04: broadcast and lut3d must produce identical output.

    Marked `slow` because the lut3d path materializes a 256^3 BGR LUT,
    which takes a few seconds to build under scipy.cKDTree. Run with
    `pytest -m slow` to include it.
    """
    from legome.palette import lego_palette

    pal = lego_palette()
    rng = np.random.default_rng(42)
    img = rng.integers(0, 256, size=(48, 48, 3), dtype=np.uint8)
    broadcast = apply_palette(img, pal, method="broadcast")
    lut3d = apply_palette(img, pal, method="lut3d")
    assert np.array_equal(broadcast, lut3d), (
        "broadcast and lut3d quantizers diverged — palette membership differs"
    )


def test_apply_palette_rejects_invalid_method():
    pal = _gradient_palette()
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="method must be"):
        apply_palette(img, pal, method="kdtree-yolo")
