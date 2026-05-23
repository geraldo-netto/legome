"""Tests for legome.resize (SCAL-04)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from legome.resize import PAPER_SIZES, parse_resize_arg, resize_image


@pytest.mark.parametrize("size_str,expected", [
    ("100x200", (100, 200)),
    ("1x1", (1, 1)),
    ("320X240", (320, 240)),
    (" 64x64 ", (64, 64)),
])
def test_parse_resize_arg_wxh(size_str, expected):
    assert parse_resize_arg(size_str) == expected


@pytest.mark.parametrize("preset", list(PAPER_SIZES))
def test_parse_resize_arg_presets(preset):
    assert parse_resize_arg(preset) == PAPER_SIZES[preset]
    assert parse_resize_arg(preset.upper()) == PAPER_SIZES[preset]


@pytest.mark.parametrize("bad", ["", "abc", "100", "x100", "10x", "0x10", "10x-5"])
def test_parse_resize_arg_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_resize_arg(bad)


def test_resize_image_changes_dimensions():
    img = np.full((100, 50, 3), 64, dtype=np.uint8)
    out = resize_image(img, (200, 100))  # (w, h)
    assert out.shape == (100, 200, 3)
    assert out.dtype == np.uint8


def test_resize_image_inter_area_downscale_is_average():
    """INTER_AREA on a constant image must preserve the constant value."""
    img = np.full((128, 128, 3), 100, dtype=np.uint8)
    out = resize_image(img, (32, 32))
    assert out.shape == (32, 32, 3)
    assert (out == 100).all()


def test_resize_image_rejects_zero_dims():
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        resize_image(img, (0, 4))


def test_cli_resize_wxh(tmp_path):
    from legome.cli import main

    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    cv2.imwrite(str(src), np.full((64, 64, 3), 100, dtype=np.uint8))
    rc = main([str(src), str(dst), "--resize", "16x16", "--no-display"])
    assert rc == 0
    out = cv2.imread(str(dst))
    assert out.shape == (16, 16, 3)


def test_cli_resize_preset(tmp_path):
    from legome.cli import main

    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    cv2.imwrite(str(src), np.full((200, 200, 3), 50, dtype=np.uint8))
    rc = main([str(src), str(dst), "--resize", "a4", "--no-display"])
    assert rc == 0
    out = cv2.imread(str(dst))
    # PAPER_SIZES["a4"] == (32, 48)  -> width 32, height 48
    assert out.shape == (48, 32, 3)


def test_cli_resize_rejects_garbage(tmp_path):
    from legome.cli import main

    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 50, dtype=np.uint8))
    rc = main([str(src), str(tmp_path / "out.png"), "--resize", "not-a-size", "--no-display"])
    assert rc == 2
