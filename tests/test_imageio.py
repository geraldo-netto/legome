"""Unit tests for `legome.imageio`."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from legome import imageio


def _write_magic(path: Path, magic: bytes) -> None:
    path.write_bytes(magic + b"\x00" * 64)


def test_detect_format_png(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"\x89PNG\r\n\x1a\n")
    assert imageio.detect_format(p) == "png"


def test_detect_format_jpeg(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"\xff\xd8\xff\xe0")
    assert imageio.detect_format(p) == "jpeg"


def test_detect_format_bmp(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"BMxx")
    assert imageio.detect_format(p) == "bmp"


def test_detect_format_tiff_le(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"II*\x00")
    assert imageio.detect_format(p) == "tiff"


def test_detect_format_tiff_be(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"MM\x00*")
    assert imageio.detect_format(p) == "tiff"


def test_detect_format_webp(tmp_path):
    p = tmp_path / "a"
    p.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16)
    assert imageio.detect_format(p) == "webp"


def test_detect_format_gif(tmp_path):
    p = tmp_path / "a"
    _write_magic(p, b"GIF89a")
    assert imageio.detect_format(p) == "gif"


def test_detect_format_unknown(tmp_path):
    p = tmp_path / "a"
    p.write_bytes(b"not an image")
    assert imageio.detect_format(p) is None


def test_detect_format_missing_file(tmp_path):
    p = tmp_path / "nope"
    assert imageio.detect_format(p) is None


def test_reconcile_input_extension_match(tmp_path, caplog):
    p = tmp_path / "a.png"
    _write_magic(p, b"\x89PNG\r\n\x1a\n")
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_input_extension(p) == "png"
    assert not caplog.messages, "no warning expected on extension match"


def test_reconcile_input_extension_mismatch_logs(tmp_path, caplog):
    """REL-13: content disagrees with extension — warn and trust content."""
    p = tmp_path / "a.png"
    _write_magic(p, b"\xff\xd8\xff\xe0")  # JPEG bytes
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_input_extension(p) == "jpeg"
    assert any("trusting content" in m for m in caplog.messages)


def test_reconcile_input_extension_unknown_ext_logs(tmp_path, caplog):
    p = tmp_path / "a.xyz"
    _write_magic(p, b"\x89PNG\r\n\x1a\n")
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_input_extension(p) == "png"
    assert any("not a known image extension" in m for m in caplog.messages)


def test_reconcile_input_extension_unknown_content_logs(tmp_path, caplog):
    p = tmp_path / "a.png"
    p.write_bytes(b"garbage")
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_input_extension(p) is None
    assert any("could not identify" in m for m in caplog.messages)


def test_reconcile_output_extension_png_no_warning(tmp_path, caplog):
    p = tmp_path / "out.png"
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_output_extension(p) == p
    assert not caplog.messages


def test_reconcile_output_extension_jpg_warns_lossy(tmp_path, caplog):
    p = tmp_path / "out.jpg"
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        assert imageio.reconcile_output_extension(p) == p
    assert any("lossy JPEG" in m for m in caplog.messages)


def test_reconcile_output_extension_unsupported_falls_back_to_png(tmp_path, caplog):
    """REL-14: unsupported extension is rewritten to .png with a warning."""
    p = tmp_path / "out.xyz"
    with caplog.at_level(logging.WARNING, logger="legome.imageio"):
        new = imageio.reconcile_output_extension(p)
    assert new.suffix == ".png"
    assert any("not supported" in m for m in caplog.messages)


def test_cli_falls_back_to_png_on_unsupported_extension(tmp_path, caplog):
    """End-to-end: CLI rewrites foo.xyz output to foo.png and writes it."""
    from legome.cli import main

    src = tmp_path / "in.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 100, dtype=np.uint8))
    dst_bad = tmp_path / "out.xyz"
    with caplog.at_level(logging.WARNING):
        rc = main([str(src), str(dst_bad), "--no-display"])
    assert rc == 0
    assert (tmp_path / "out.png").is_file()
    assert any("PNG" in m for m in caplog.messages)
