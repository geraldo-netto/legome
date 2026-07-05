"""Tests for legome.batch (SCAL-01 + CONC-01)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from legome.batch import (
    BatchResult,
    BatchTask,
    _init_worker,
    _process_one,
    discover_inputs,
    run_batch,
)
from legome.palette import lego_palette


def _write_png(path: Path, value: int = 100) -> None:
    cv2.imwrite(str(path), np.full((8, 8, 3), value, dtype=np.uint8))


def test_discover_inputs_filters_by_extension(tmp_path):
    _write_png(tmp_path / "a.png")
    _write_png(tmp_path / "b.png")
    (tmp_path / "c.txt").write_text("nope")
    (tmp_path / "subdir").mkdir()
    found = discover_inputs(tmp_path)
    assert [p.name for p in found] == ["a.png", "b.png"]


def test_process_one_writes_png(tmp_path):
    _init_worker(lego_palette())
    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    _write_png(src)
    res = _process_one(BatchTask(src=src, dst=dst, resize=None))
    assert res.status == "ok"
    assert dst.is_file()


def test_process_one_decode_failure(tmp_path):
    _init_worker(lego_palette())
    src = tmp_path / "in.png"
    src.write_text("not an image")
    dst = tmp_path / "out.png"
    res = _process_one(BatchTask(src=src, dst=dst, resize=None))
    assert res.status == "decode_failed"


def test_process_one_requires_init_worker(tmp_path):
    """SEC-02: _process_one must refuse to run if no palette was installed."""
    import legome.batch as batch_mod

    src = tmp_path / "in.png"
    _write_png(src)
    saved = batch_mod._WORKER_PALETTE
    batch_mod._WORKER_PALETTE = None
    try:
        with pytest.raises(RuntimeError, match="_init_worker"):
            _process_one(BatchTask(src=src, dst=tmp_path / "out.png", resize=None))
    finally:
        batch_mod._WORKER_PALETTE = saved


def test_process_one_write_failure(tmp_path, monkeypatch):
    """write_failed branch — cv2.imwrite returns False."""
    _init_worker(lego_palette())
    src = tmp_path / "in.png"
    _write_png(src)
    monkeypatch.setattr("cv2.imwrite", lambda _path, _img: False)
    res = _process_one(BatchTask(src=src, dst=tmp_path / "out.png", resize=None))
    assert res.status == "write_failed"


def test_process_one_unexpected_error_is_isolated(tmp_path, monkeypatch):
    """REL-16: an unexpected raise becomes an 'error' result, not a batch abort."""
    import legome.processor as processor_mod

    _init_worker(lego_palette())
    src = tmp_path / "in.png"
    _write_png(src)

    def _boom(_image, _palette):
        raise MemoryError("simulated OOM")

    monkeypatch.setattr(processor_mod, "apply_palette", _boom)
    res = _process_one(BatchTask(src=src, dst=tmp_path / "out.png", resize=None))
    assert res.status == "error"
    assert "MemoryError" in res.message


def test_run_batch_isolates_one_bad_file(tmp_path, monkeypatch):
    """REL-16: one failing image does not lose the results of the good ones."""
    import legome.processor as processor_mod

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    _write_png(in_dir / "good.png", value=10)
    _write_png(in_dir / "bad.png", value=20)

    real = processor_mod.apply_palette

    def _selective(image, palette):
        if int(image[0, 0, 0]) == 20:
            raise ValueError("bad image")
        return real(image, palette)

    monkeypatch.setattr(processor_mod, "apply_palette", _selective)
    results = run_batch(in_dir, out_dir, lego_palette(), jobs=1)
    by_name = {r.src.name: r.status for r in results}
    assert by_name == {"good.png": "ok", "bad.png": "error"}


def test_run_batch_sequential(tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    for name in ("a.png", "b.png", "c.png"):
        _write_png(in_dir / name)
    pal = lego_palette()
    results = run_batch(in_dir, out_dir, pal, jobs=1)
    assert {r.src.name for r in results} == {"a.png", "b.png", "c.png"}
    assert all(r.status == "ok" for r in results)
    assert {p.name for p in out_dir.iterdir()} == {"a.png", "b.png", "c.png"}


def test_run_batch_parallel(tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    for i in range(4):
        _write_png(in_dir / f"img{i}.png", value=10 * i + 1)
    pal = lego_palette()
    results = run_batch(in_dir, out_dir, pal, jobs=2)
    assert len(results) == 4
    assert all(r.status == "ok" for r in results)
    assert len(list(out_dir.iterdir())) == 4


def test_run_batch_forces_png_extension(tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    _write_png(in_dir / "photo.jpg")  # input extension JPG but content PNG
    pal = lego_palette()
    results = run_batch(in_dir, out_dir, pal, jobs=1)
    assert results[0].dst.name == "photo.png"
    assert results[0].dst.is_file()


def test_run_batch_empty_dir(tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    pal = lego_palette()
    results = run_batch(in_dir, out_dir, pal, jobs=1)
    assert results == []


def test_run_batch_with_resize(tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    _write_png(in_dir / "a.png")
    pal = lego_palette()
    results = run_batch(in_dir, out_dir, pal, resize=(4, 4), jobs=1)
    assert results[0].status == "ok"
    out = cv2.imread(str(results[0].dst))
    assert out.shape == (4, 4, 3)


@pytest.mark.slow
def test_cli_batch_mode_end_to_end(tmp_path):
    """End-to-end CLI batch run with parallel workers."""
    from legome.cli import main

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    for i in range(3):
        _write_png(in_dir / f"img{i}.png", value=20 + 10 * i)
    rc = main([str(in_dir), str(out_dir), "--no-display", "--jobs", "2"])
    assert rc == 0
    outputs = sorted(p.name for p in out_dir.iterdir())
    assert outputs == ["img0.png", "img1.png", "img2.png"]


def test_cli_batch_mode_rejects_file_output(tmp_path):
    """Input is a directory but output exists as a file -> exit 2."""
    from legome.cli import main

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    _write_png(in_dir / "a.png")
    out_file = tmp_path / "not-a-dir.png"
    out_file.write_text("placeholder")
    rc = main([str(in_dir), str(out_file), "--no-display"])
    assert rc == 2


def test_cli_batch_mode_reports_failures(tmp_path, caplog):
    """A directory with a malformed image should exit 5 and log the failure."""
    import logging

    from legome.cli import main

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    _write_png(in_dir / "ok.png")
    (in_dir / "bad.png").write_text("not an image")
    with caplog.at_level(logging.ERROR):
        rc = main([str(in_dir), str(out_dir), "--no-display", "--jobs", "1"])
    assert rc == 5
    assert any("decode_failed" in m for m in caplog.messages)


def test_batch_result_repr():
    r = BatchResult(src=Path("a"), dst=Path("b"), status="ok")
    assert "ok" in repr(r)
