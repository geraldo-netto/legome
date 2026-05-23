"""Smoke tests for `python -m legome` entrypoint."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_python_m_legome_version():
    res = subprocess.run(
        [sys.executable, "-m", "legome", "--version"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert res.returncode == 0
    assert "legome" in res.stdout


@pytest.mark.slow
def test_python_m_legome_help():
    res = subprocess.run(
        [sys.executable, "-m", "legome", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert res.returncode == 0
    assert "input" in res.stdout
    assert "output" in res.stdout


@pytest.mark.slow
def test_python_m_legome_end_to_end(tmp_path):
    """`python -m legome <in> <out>` runs end-to-end against the bundled palette."""
    import cv2
    import numpy as np

    src = tmp_path / "in.png"
    dst = tmp_path / "out.png"
    cv2.imwrite(str(src), np.full((4, 4, 3), 64, dtype=np.uint8))
    res = subprocess.run(
        [sys.executable, "-m", "legome", str(src), str(dst), "--no-display"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert res.returncode == 0, res.stderr
    assert dst.is_file()
