"""CLI entry point for Legome."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .batch import run_batch
from .imageio import reconcile_input_extension, reconcile_output_extension
from .palette import (
    Palette,
    default_palette_path,
    lego_palette,
    load_palette,
)
from .resize import PAPER_SIZES, parse_resize_arg, resize_image

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

log = logging.getLogger("legome")

_EPILOG = """\
examples:
  legome photo.jpg mosaic.png                  # single image, real Lego brick palette (default)
  legome photo.jpg mosaic.png --palette p.json # custom JSON palette
  legome photo.jpg mosaic.png --no-display     # skip preview window (headless / scripts)
  legome photos/ mosaics/ --jobs 8             # batch a directory in parallel

palette modes:
  * default: every pixel snaps to its nearest color in `legome.lego_colors.LEGO_COLORS`
    (currently 49 real solid brick colors). Output is buildable from real pieces.
  * --palette PATH: load any JSON palette (`colors` or legacy `lut` schema) or any
    GIMP .gpl palette (auto-detected by extension).

batch mode:
  When the input path is a directory, every image inside it is processed in
  parallel and written to the output directory with the same stem and a `.png`
  extension. `--jobs N` (default os.cpu_count()) controls worker count.

exit codes:
  0  success
  2  input/output/palette validation error (also: cv2.imread decoded None)
  3  OpenCV (cv2) not installed
  4  cv2.imwrite refused to write the requested output path
  5  batch had one or more per-file failures (see logs for which files)
"""


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="legome",
        description="Quantize an image to a Lego brick color palette so it can be built as a mosaic.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="input image path or directory (any format OpenCV can decode)")
    p.add_argument(
        "output",
        help="output image path (PNG recommended; JPEG is lossy) — must be a directory when input is a directory",
    )
    p.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=None,
        help="parallel workers for batch mode (default: os.cpu_count())",
    )
    p.add_argument(
        "--palette",
        default=None,
        metavar="PATH",
        help="path to palette JSON (default: the bundled real-Lego brick palette)",
    )
    p.add_argument(
        "--resize",
        default=None,
        metavar="WxH|preset",
        help=(
            "resize the input image before quantization. Accepts an explicit "
            "`WxH` (e.g. `--resize 256x256`) or a preset from "
            f"{sorted(PAPER_SIZES)} (paper sizes assume 64-px-per-brick at "
            "common mosaic densities)."
        ),
    )
    p.add_argument(
        "--build-plan",
        default=None,
        metavar="PATH",
        help=(
            "also write an annotated build-plan PNG to PATH. Each cell shows the "
            "color name, Bricklink ID, and grid coordinate; a legend lists brick "
            "counts. Single-image mode only — ignored in batch."
        ),
    )
    p.add_argument(
        "--build-plan-cell-px",
        type=int,
        default=None,
        metavar="N",
        help="build-plan cell width in pixels (default 78; minimum 48).",
    )
    p.add_argument(
        "--no-display",
        action="store_true",
        help="do not show a preview window after writing output",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="enable INFO-level logging")
    p.add_argument("--version", action="version", version=f"legome {__version__}")
    return p


def _resolve_palette(palette_arg: str | None) -> Palette:
    if palette_arg is None:
        return lego_palette()
    # SEC-01: match how `input`/`output` are normalized — expand `~` and
    # resolve to an absolute path so `~/p.json` works and relative paths
    # are unambiguous in error messages.
    p = Path(palette_arg).expanduser().resolve(strict=False)
    if p.suffix.lower() == ".gpl":
        from .gpl import load_gpl

        return load_gpl(p)
    return load_palette(p)


def _validate_input_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve(strict=False)
    if not p.is_file():
        raise FileNotFoundError(f"input image not found: {raw}")
    return p


def _validate_output_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve(strict=False)
    if p.is_dir():
        raise IsADirectoryError(f"output path is a directory: {raw}")
    parent = p.parent
    if not parent.exists():
        raise FileNotFoundError(f"output directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise PermissionError(f"output directory not writable: {parent}")
    return p


def _load_and_log_palette(args: argparse.Namespace) -> Palette:
    """DUP-01: resolve palette + log the standard summary line.

    Shared between single-image and batch modes so the two stay in lockstep.
    Raises `FileNotFoundError` / `ValueError` from the underlying loader.
    """
    palette = _resolve_palette(args.palette)
    log.info(
        "palette '%s' with %d colors (%d unique)",
        palette.name,
        len(palette.colors),
        len(palette.unique_colors()),
    )
    return palette


def _acquire_image(args: argparse.Namespace, in_path: Path) -> np.ndarray:
    """Decode the input image and apply `--resize` if requested.

    Raises ImportError if cv2 is unavailable, ValueError if cv2 refuses
    to decode the file or the resize spec is malformed.
    """
    import cv2

    image = cv2.imread(str(in_path))
    if image is None:
        raise ValueError(f"could not decode input image: {in_path}")
    if args.resize is not None:
        target = parse_resize_arg(args.resize)
        log.info("resizing %s -> %s", image.shape[:2][::-1], target)
        image = resize_image(image, target)
    return image


def _render_and_write_plan(args: argparse.Namespace, recolored: np.ndarray) -> np.ndarray:
    """Render and write a build-plan PNG. Raises OSError if cv2.imwrite refuses."""
    import cv2

    from .build_plan import DEFAULT_CELL_W_PX, render_build_plan

    cell = args.build_plan_cell_px if args.build_plan_cell_px is not None else DEFAULT_CELL_W_PX
    plan = render_build_plan(recolored, cell_w_px=cell)
    plan_path = Path(args.build_plan).expanduser().resolve(strict=False).with_suffix(".png")
    if not cv2.imwrite(str(plan_path), plan):
        raise OSError(f"could not write build plan: {plan_path}")
    log.info("wrote build plan %s", plan_path)
    return plan


def _maybe_show(args: argparse.Namespace, recolored: np.ndarray, plan: np.ndarray | None) -> None:
    if args.no_display:
        return
    from .display import show_image

    if plan is not None:
        show_image(plan, title="LegoMe build plan")
    else:
        show_image(recolored)


def run_single(args: argparse.Namespace) -> int:
    """Single-image pipeline: validate I/O → load palette → decode → quantize → write."""
    try:
        in_path = _validate_input_path(args.input)
        out_path = _validate_output_path(args.output)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
        log.error("%s", exc)
        return 2

    reconcile_input_extension(in_path)
    out_path = reconcile_output_extension(out_path)

    try:
        palette = _load_and_log_palette(args)
    except (FileNotFoundError, ValueError) as exc:
        log.error("palette load failed: %s", exc)
        return 2

    try:
        image = _acquire_image(args, in_path)
    except ImportError:
        log.error("OpenCV (cv2) not installed: pip install opencv-python")
        return 3
    except ValueError as exc:
        log.error("%s", exc)
        return 2

    import cv2

    from .processor import apply_palette

    recolored = apply_palette(image, palette)
    if not cv2.imwrite(str(out_path), recolored):
        log.error("could not write output image: %s", out_path)
        return 4
    log.info("wrote %s", out_path)

    plan: np.ndarray | None = None
    if args.build_plan is not None:
        try:
            plan = _render_and_write_plan(args, recolored)
        except ValueError as exc:
            log.error("%s", exc)
            return 2
        except OSError as exc:
            log.error("%s", exc)
            return 4

    _maybe_show(args, recolored, plan)
    return 0


def _report_batch_results(results: list) -> int:
    bad = [r for r in results if r.status != "ok"]
    for r in bad:
        log.error("%s: %s (%s)", r.src, r.status, r.message)
    log.info("batch: %d ok, %d failed", len(results) - len(bad), len(bad))
    return 5 if bad else 0


def _run_batch_mode(args: argparse.Namespace, in_dir: Path) -> int:
    out_raw = Path(args.output).expanduser()
    if out_raw.exists() and not out_raw.is_dir():
        log.error("input %s is a directory, but output %s is not", in_dir, out_raw)
        return 2

    try:
        palette = _load_and_log_palette(args)
    except (FileNotFoundError, ValueError) as exc:
        log.error("palette load failed: %s", exc)
        return 2

    target = None
    if args.resize is not None:
        try:
            target = parse_resize_arg(args.resize)
        except ValueError as exc:
            log.error("%s", exc)
            return 2

    results = run_batch(in_dir, out_raw, palette, resize=target, jobs=args.jobs)
    if not results:
        log.warning("no images processed")
        return 0
    return _report_batch_results(results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    # No arguments → print help and exit 0 (more discoverable than argparse's
    # default "missing required argument" stderr noise).
    effective_argv = list(sys.argv[1:]) if argv is None else list(argv)
    if not effective_argv:
        parser.print_help()
        return 0
    args = parser.parse_args(effective_argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    in_raw = Path(args.input).expanduser()
    if in_raw.is_dir():
        if args.build_plan is not None:
            log.warning("--build-plan is ignored in batch mode (single-image only)")
        return _run_batch_mode(args, in_raw)
    return run_single(args)


# Re-exported so tests can patch `legome.cli.default_palette_path` if needed.
__all__ = ["main", "run_single", "default_palette_path"]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
