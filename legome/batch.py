"""SCAL-01 + CONC-01: parallel batch processing for directory inputs.

When the CLI is given a directory as the input path, every image file in
that directory is quantized with the chosen palette and written to the
corresponding name in the output directory (extension forced to `.png`,
since JPEG is lossy for quantized palettes — see REL-14).

Parallelism: a `concurrent.futures.ProcessPoolExecutor` spreads the work
across `--jobs` workers (default: `os.cpu_count()`). Each worker
processes one image end-to-end. The palette is pickled to the workers
once, then re-used for every image they handle.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .palette import Palette

log = logging.getLogger("legome.batch")

SUPPORTED_INPUT_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
)


@dataclass(frozen=True)
class BatchTask:
    src: Path
    dst: Path
    palette: Palette
    resize: tuple[int, int] | None


@dataclass(frozen=True)
class BatchResult:
    src: Path
    dst: Path
    status: str  # "ok" | "decode_failed" | "write_failed"
    message: str = ""


def discover_inputs(in_dir: Path) -> list[Path]:
    """Return sorted list of image files in `in_dir` (non-recursive)."""
    return sorted(
        p
        for p in in_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
    )


def _process_one(task: BatchTask) -> BatchResult:
    import cv2

    from .processor import apply_palette
    from .resize import resize_image

    image = cv2.imread(str(task.src))
    if image is None:
        return BatchResult(task.src, task.dst, "decode_failed", "cv2.imread returned None")
    if task.resize is not None:
        image = resize_image(image, task.resize)
    recolored = apply_palette(image, task.palette)
    if not cv2.imwrite(str(task.dst), recolored):
        return BatchResult(task.src, task.dst, "write_failed", f"cv2.imwrite refused {task.dst}")
    return BatchResult(task.src, task.dst, "ok")


def run_batch(
    in_dir: Path,
    out_dir: Path,
    palette: Palette,
    resize: tuple[int, int] | None = None,
    jobs: int | None = None,
) -> list[BatchResult]:
    """Run the quantizer over every image in `in_dir` and write to `out_dir`.

    Output filenames mirror the input stems with a forced `.png` extension.
    `jobs` defaults to `os.cpu_count()`; pass 1 to run sequentially.
    """
    inputs = discover_inputs(in_dir)
    if not inputs:
        log.warning("no supported images found in %s (looked for %s)", in_dir, sorted(SUPPORTED_INPUT_EXTENSIONS))
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        BatchTask(src=p, dst=out_dir / f"{p.stem}.png", palette=palette, resize=resize)
        for p in inputs
    ]
    n_workers = jobs if jobs is not None else (os.cpu_count() or 1)
    n_workers = max(1, n_workers)
    log.info("batch: %d files, %d workers", len(tasks), n_workers)
    if n_workers == 1:
        return [_process_one(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(_process_one, tasks))
