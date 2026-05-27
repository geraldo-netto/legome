"""SCAL-01 + CONC-01: parallel batch processing for directory inputs.

When the CLI is given a directory as the input path, every image file in
that directory is quantized with the chosen palette and written to the
corresponding name in the output directory (extension forced to `.png`,
since JPEG is lossy for quantized palettes — see REL-14).

Parallelism: a `concurrent.futures.ProcessPoolExecutor` spreads the work
across `--jobs` workers (default: `os.cpu_count()`). SEC-02: the palette
is pickled once per worker via the pool `initializer=` and stashed in a
module-level slot; per-task pickles only carry the lightweight
`BatchTask` (paths + resize spec). This avoids re-shipping the full
`Palette` (and its color tuple) with every image dispatched to the pool.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .palette import Palette

log = logging.getLogger("legome.batch")

SUPPORTED_INPUT_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


@dataclass(frozen=True)
class BatchTask:
    src: Path
    dst: Path
    resize: tuple[int, int] | None


@dataclass(frozen=True)
class BatchResult:
    src: Path
    dst: Path
    status: str  # "ok" | "decode_failed" | "write_failed"
    message: str = ""


# SEC-02: populated once per worker (or once for the main process when running
# sequentially) by `_init_worker`. `_process_one` reads from this slot instead
# of receiving the palette through `BatchTask`.
_WORKER_PALETTE: Palette | None = None


def _init_worker(palette: Palette) -> None:
    """Pool initializer — stash the palette in the worker's module state."""
    global _WORKER_PALETTE
    _WORKER_PALETTE = palette


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

    palette = _WORKER_PALETTE
    if palette is None:
        raise RuntimeError(
            "_init_worker(palette) must run before _process_one — call it via "
            "the pool initializer= or directly before sequential dispatch"
        )

    image = cv2.imread(str(task.src))
    if image is None:
        return BatchResult(task.src, task.dst, "decode_failed", "cv2.imread returned None")
    if task.resize is not None:
        image = resize_image(image, task.resize)
    recolored = apply_palette(image, palette)
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
        log.warning(
            "no supported images found in %s (looked for %s)",
            in_dir,
            sorted(SUPPORTED_INPUT_EXTENSIONS),
        )
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = [BatchTask(src=p, dst=out_dir / f"{p.stem}.png", resize=resize) for p in inputs]
    n_workers = jobs if jobs is not None else (os.cpu_count() or 1)
    n_workers = max(1, n_workers)
    log.info("batch: %d files, %d workers", len(tasks), n_workers)
    if n_workers == 1:
        _init_worker(palette)
        return [_process_one(t) for t in tasks]
    with ProcessPoolExecutor(
        max_workers=n_workers, initializer=_init_worker, initargs=(palette,)
    ) as ex:
        return list(ex.map(_process_one, tasks))
