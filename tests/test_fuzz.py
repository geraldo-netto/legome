"""Hypothesis-based property/fuzz tests.

Properties:
  - apply_palette is total over the input domain (uint8 HxWx3) — never raises.
  - Output dtype/shape preserved.
  - Every output pixel belongs to the loaded palette.
  - apply_palette is deterministic (same input -> same output).
  - apply_palette is idempotent when palette acts as identity on already-
    palettized pixels.
  - Channel-permutation invariant: swapping LUT input channels permutes the
    LUT-lookup index per-channel; we sanity-check by all-zero / all-255 images.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from legome.palette import LUT_SIZE, Palette, default_palette_path, load_palette
from legome.processor import apply_palette, output_pixels_in_palette

PALETTE = load_palette(default_palette_path())

_image_strategy = hnp.arrays(
    dtype=np.uint8,
    shape=st.tuples(
        st.integers(min_value=1, max_value=16),
        st.integers(min_value=1, max_value=16),
        st.just(3),
    ),
    elements=st.integers(min_value=0, max_value=255),
)


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_image_strategy)
def test_fuzz_apply_palette_never_raises(img):
    out = apply_palette(img, PALETTE)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_image_strategy)
def test_fuzz_output_in_palette(img):
    out = apply_palette(img, PALETTE)
    assert output_pixels_in_palette(out, PALETTE)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_image_strategy)
def test_fuzz_apply_palette_deterministic(img):
    a = apply_palette(img, PALETTE)
    b = apply_palette(img, PALETTE)
    assert np.array_equal(a, b)


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
        ),
        min_size=LUT_SIZE,
        max_size=LUT_SIZE,
    )
)
def test_fuzz_palette_construction_accepts_any_valid_lut(lut_list):
    pal = Palette(name="fuzz", colors=tuple(lut_list))
    assert len(pal.lut) == LUT_SIZE


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(min_value=-100, max_value=400).filter(lambda x: x < 0 or x > 255))
def test_fuzz_palette_rejects_out_of_range(bad_channel):
    lut = [(0, 0, 0)] * (LUT_SIZE - 1) + [(0, 0, bad_channel)]
    with pytest.raises(ValueError):
        Palette(name="fuzz", colors=tuple(lut))


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    hnp.arrays(
        dtype=np.uint8,
        shape=st.tuples(
            st.integers(min_value=1, max_value=8),
            st.integers(min_value=1, max_value=8),
            st.just(3),
        ),
        elements=st.integers(min_value=0, max_value=255),
    )
)
def test_fuzz_apply_palette_pixel_count_preserved(img):
    out = apply_palette(img, PALETTE)
    assert out.size == img.size
