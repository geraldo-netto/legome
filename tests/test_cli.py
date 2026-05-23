"""Unit tests for legome.cli."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from legome import cli


def _write_image(path: Path) -> None:
    """Write a small lossless PNG fixture image.

    QA-03: use PNG so cv2.imread round-trips return identical pixels and
    tests do not become flaky across OpenCV / libjpeg version changes.
    """
    img = np.full((8, 8, 3), 128, dtype=np.uint8)
    if path.suffix.lower() not in {".png", ".bmp", ".tif", ".tiff"}:
        path = path.with_suffix(".png")
    cv2.imwrite(str(path), img)


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "legome" in out


def test_help_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_main_happy_path(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    monkeypatch.setattr("legome.display.show_image", lambda *a, **k: False)
    rc = cli.main([str(src), str(dst), "--no-display"])
    assert rc == 0
    assert dst.is_file()
    out = cv2.imread(str(dst))
    assert out is not None
    assert out.shape == (8, 8, 3)


def test_main_input_not_found(tmp_path):
    rc = cli.main([str(tmp_path / "missing.png"), str(tmp_path / "out.png"), "--no-display"])
    assert rc == 2


def test_main_output_dir_missing(tmp_path):
    src = tmp_path / "in.png"
    _write_image(src)
    rc = cli.main([str(src), str(tmp_path / "no_such_dir" / "out.png"), "--no-display"])
    assert rc == 2


def test_main_output_is_directory(tmp_path):
    src = tmp_path / "in.png"
    _write_image(src)
    rc = cli.main([str(src), str(tmp_path), "--no-display"])
    assert rc == 2


def test_main_palette_load_failure(tmp_path):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    bad_pal = tmp_path / "bad.json"
    bad_pal.write_text("[]")
    rc = cli.main([str(src), str(dst), "--palette", str(bad_pal), "--no-display"])
    assert rc == 2


def test_main_decode_failure(tmp_path):
    bad = tmp_path / "in.png"
    bad.write_text("not actually an image")
    rc = cli.main([str(bad), str(tmp_path / "out.png"), "--no-display"])
    assert rc == 2


def test_main_imread_returns_none(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    monkeypatch.setattr(cv2, "imread", lambda *a, **k: None)
    rc = cli.main([str(src), str(dst), "--no-display"])
    assert rc == 2


def test_main_imwrite_failure(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    monkeypatch.setattr(cv2, "imwrite", lambda *a, **k: False)
    rc = cli.main([str(src), str(dst), "--no-display"])
    assert rc == 4


def test_main_cv2_missing(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)

    real_import = __import__

    def fake_import(name, *a, **k):
        if name == "cv2" and sys._getframe(1).f_globals.get("__name__") == "legome.cli":
            raise ImportError("forced")
        return real_import(name, *a, **k)

    # Simpler: patch cli's cv2 import via blocking sys.modules.
    monkeypatch.setitem(sys.modules, "cv2", None)
    rc = cli.main([str(src), str(dst), "--no-display"])
    # cv2 still installed at module-level for other tests; the cli imports lazily,
    # so blocking via sys.modules=None triggers ImportError.
    assert rc == 3
    # restore
    monkeypatch.undo()


def test_main_verbose_flag(tmp_path):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    rc = cli.main([str(src), str(dst), "--no-display", "-v"])
    assert rc == 0


def test_main_display_path(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)
    called = {"n": 0}

    def fake_show(img, **kw):
        called["n"] += 1
        return True

    monkeypatch.setattr("legome.display.show_image", fake_show)
    rc = cli.main([str(src), str(dst)])
    assert rc == 0
    assert called["n"] == 1


def test_main_output_unwritable(tmp_path, monkeypatch):
    src = tmp_path / "in.png"
    _write_image(src)
    monkeypatch.setattr(cli.os, "access", lambda *a, **k: False)
    rc = cli.main([str(src), str(tmp_path / "out.png"), "--no-display"])
    assert rc == 2


def test_main_no_arguments_prints_help(capsys):
    """LEGO-05: bare `legome` (or `legome` with no positional args) prints help and exits 0."""
    rc = cli.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "input" in out
    assert "output" in out
    assert "--palette" in out
    assert "--no-display" in out


def test_main_default_palette_is_lego_only(tmp_path, monkeypatch):
    """When --palette is omitted, output uses only real Lego brick colors."""
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_image(src)  # writes any 3-channel image; format doesn't matter here
    monkeypatch.setattr("legome.display.show_image", lambda *a, **k: False)
    rc = cli.main([str(src), str(dst), "--no-display"])
    assert rc == 0
    out = cv2.imread(str(dst))
    assert out is not None
    # Every pixel in the output should be a real Lego brick color.
    from legome.lego_colors import LEGO_COLORS

    lego_bgr = {(c.rgb[2], c.rgb[1], c.rgb[0]) for c in LEGO_COLORS}
    seen = {tuple(int(c) for c in px) for px in out.reshape(-1, 3)}
    assert seen.issubset(lego_bgr), "output contains non-Lego colors"
