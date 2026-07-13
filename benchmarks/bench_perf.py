"""Benchmarks for PERF-04/05/06 — print before/after timings.

Run:
    python3 -m benchmarks.bench_perf

Each benchmark uses a fixed seed so results are reproducible. The output
file `benchmarks/RESULTS.md` is updated with the latest numbers.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from legome.lego_colors import LEGO_COLORS, match_palette_to_lego
from legome.palette import default_palette_path, lego_palette, load_palette
from legome.processor import (
    LUT3D_BREAKEVEN_PIXELS,
    apply_palette,
    output_pixels_in_palette,
)

RNG = np.random.default_rng(20260523)
REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "benchmarks" / "RESULTS.md"


def _time(label: str, fn, repeats: int = 3) -> float:
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return min(samples)


# ---- PERF-05: output_pixels_in_palette ---------------------------------------


def _slow_output_pixels_in_palette(image, palette):
    """Legacy O(N) Python-set implementation, for comparison."""
    flat = image.reshape(-1, 3)
    pal_bgr = {(b, g, r) for r, g, b in palette.colors}
    seen = {tuple(int(c) for c in px) for px in flat}
    return seen.issubset(pal_bgr)


def bench_output_check():
    pal = lego_palette()
    img = RNG.integers(0, 256, size=(512, 512, 3), dtype=np.uint8)
    img = apply_palette(img, pal, method="broadcast")  # output IS in palette
    old = _time(
        "slow set comprehension", lambda: _slow_output_pixels_in_palette(img, pal), repeats=2
    )
    new = _time("vectorized np.isin", lambda: output_pixels_in_palette(img, pal), repeats=3)
    return {"old": old, "new": new, "size": img.size // 3}


# ---- PERF-06: match_palette_to_lego ------------------------------------------


def _euclid_sq(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _slow_match_palette_to_lego(palette_colors, threshold=40.0):
    out = []
    for c in palette_colors:
        best = min(LEGO_COLORS, key=lambda lc: _euclid_sq(lc.rgb, c))
        d = _euclid_sq(best.rgb, c) ** 0.5
        out.append(
            {
                "palette_rgb": c,
                "lego_name": best.name,
                "lego_rgb": best.rgb,
                "distance": d,
                "match": d <= threshold,
            }
        )
    return out


def bench_lego_match():
    pal = load_palette(default_palette_path())
    colors = pal.unique_colors()
    old = _time("python min loop", lambda: _slow_match_palette_to_lego(colors), repeats=5)
    new = _time("vectorized numpy", lambda: match_palette_to_lego(colors), repeats=5)
    return {"old": old, "new": new, "n": len(colors)}


# ---- PERF-04: 3D LUT quantizer ----------------------------------------------


def bench_quantizer(size_hw):
    pal = lego_palette()
    h, w = size_hw
    img = RNG.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    broadcast = _time(
        "chunked broadcast", lambda: apply_palette(img, pal, method="broadcast"), repeats=3
    )
    lut3d = _time(
        "3D LUT (build + apply)", lambda: apply_palette(img, pal, method="lut3d"), repeats=3
    )
    return {"size": f"{h}x{w}", "pixels": h * w, "broadcast": broadcast, "lut3d": lut3d}


def main():
    out_lines = [
        "# Benchmark results",
        "",
        "Run with `python3 -m benchmarks.bench_perf`. Times are minimum of N repeats.",
        "",
    ]

    print("PERF-05: output_pixels_in_palette")
    r = bench_output_check()
    line = f"  {r['size']:>8} pixels — slow {r['old'] * 1000:8.2f} ms  vectorized {r['new'] * 1000:8.2f} ms  speedup {r['old'] / r['new']:6.1f}x"
    print(line)
    out_lines += [
        "## PERF-05 output_pixels_in_palette",
        "",
        "| pixels | python set | vectorized | speedup |",
        "|--------|-----------:|-----------:|--------:|",
        f"| {r['size']} | {r['old'] * 1000:.2f} ms | {r['new'] * 1000:.2f} ms | {r['old'] / r['new']:.1f}x |",
        "",
    ]

    print()
    print("PERF-06: match_palette_to_lego")
    r = bench_lego_match()
    line = f"  N={r['n']:>4} palette colors — slow {r['old'] * 1000:6.2f} ms  vectorized {r['new'] * 1000:6.2f} ms  speedup {r['old'] / r['new']:6.1f}x"
    print(line)
    out_lines += [
        "## PERF-06 match_palette_to_lego",
        "",
        "| palette colors | python loop | vectorized | speedup |",
        "|---------------:|------------:|-----------:|--------:|",
        f"| {r['n']} | {r['old'] * 1000:.2f} ms | {r['new'] * 1000:.2f} ms | {r['old'] / r['new']:.1f}x |",
        "",
    ]

    print()
    print("PERF-04: quantizer (chunked broadcast vs 3D LUT)")
    out_lines += [
        "## PERF-04 quantizer (broadcast vs 3D LUT)",
        "",
        f"Auto-route threshold: {LUT3D_BREAKEVEN_PIXELS:,} pixels (above this `apply_palette` builds a 256^3 LUT once and indexes per pixel; below this it uses the chunked broadcast quantizer).",
        "",
        "| image size | broadcast | 3D LUT | faster? |",
        "|-----------:|----------:|-------:|:--------|",
    ]
    for size in [(64, 64), (256, 256), (1024, 1024), (2048, 2048)]:
        r = bench_quantizer(size)
        faster = "lut3d" if r["lut3d"] < r["broadcast"] else "broadcast"
        line = f"  {r['size']:>10}  broadcast {r['broadcast'] * 1000:8.2f} ms  lut3d {r['lut3d'] * 1000:8.2f} ms  winner: {faster}"
        print(line)
        out_lines.append(
            f"| {r['size']} ({r['pixels']:,} px) | {r['broadcast'] * 1000:.1f} ms | {r['lut3d'] * 1000:.1f} ms | {faster} |"
        )

    RESULTS.write_text("\n".join(out_lines) + "\n")
    print()
    print(f"Wrote {RESULTS}")


if __name__ == "__main__":
    main()
