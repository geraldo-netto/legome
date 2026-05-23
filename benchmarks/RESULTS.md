# Benchmark results

Run with `python3 -m benchmarks.bench_perf`. Times are minimum of N repeats.

## PERF-05 output_pixels_in_palette

| pixels | python set | vectorized | speedup |
|--------|-----------:|-----------:|--------:|
| 262144 | 674.81 ms | 4.15 ms | 162.7x |

## PERF-06 match_palette_to_lego

| palette colors | python loop | vectorized | speedup |
|---------------:|------------:|-----------:|--------:|
| 112 | 3.26 ms | 0.60 ms | 5.4x |

## PERF-04 quantizer (broadcast vs 3D LUT)

Breakeven threshold: 1,000,000 pixels.

| image size | broadcast | 3D LUT | faster? |
|-----------:|----------:|-------:|:--------|
| 64x64 (4,096 px) | 16.9 ms | 8367.0 ms | broadcast |
| 256x256 (65,536 px) | 313.7 ms | 7886.8 ms | broadcast |
| 1024x1024 (1,048,576 px) | 4791.7 ms | 7952.9 ms | broadcast |
| 2048x2048 (4,194,304 px) | 18321.7 ms | 8231.5 ms | lut3d |
