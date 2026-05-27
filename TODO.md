# TODO

Review findings per `AGENTS.md` categories. Format: `id | status | effort | description`.

Status: `open` | `in-progress` | `done` | `wontfix`. Effort: `S` (<1h) | `M` (1-4h) | `L` (>4h).

Last rescan: 2026-05-23 (fresh-repo scan; no prior history).

## security

| id | status | effort | description |
|----|--------|--------|-------------|
| SEC-01 | open | S | `_resolve_palette` accepts any user-supplied `--palette` path; `Path(...).expanduser()` is not called, so `~/p.json` is treated as a literal relative path that may surprise users. Apply `Path(arg).expanduser().resolve(strict=False)` before `load_palette` / `load_gpl` for parity with how `input`/`output` are handled in `legome/cli.py`. |
| SEC-02 | open | S | `ProcessPoolExecutor` pickles `BatchTask` (which embeds the full `Palette`) per task in `legome/batch.py`. Workers receive trusted data — but switch to passing the palette once via `initializer=` to shrink the pickle surface and avoid re-shipping the same `Palette` per file. |

## performance

| id | status | effort | description |
|----|--------|--------|-------------|
| PERF-07 | open | S | `_build_3d_lut` rebuilds the 256³ BGR→palette table (~64 MB + KDTree query) on every `apply_palette` call when `n_pixels >= LUT3D_BREAKEVEN_PIXELS`. In batch mode the same palette is used for every image; cache the LUT keyed on `palette_bgr_unique(palette).tobytes()` (or per-worker module-level memo). |
| PERF-08 | open | S | `render_build_plan` counts bricks via a nested Python `for row/col` loop over `quantized_bgr`. Replace with `np.unique(quantized_bgr.reshape(-1, 3), axis=0, return_counts=True)` for O(N) numpy instead of O(N) Python. |

## scalability

_(no open findings)_

## concurrency

_(no open findings — `ProcessPoolExecutor` workers share no mutable state.)_

## code complexity

| id | status | effort | description |
|----|--------|--------|-------------|
| COMP-01 | open | M | `cli.main()` in `legome/cli.py` is ~90 lines and weaves input/output validation, palette resolve, cv2 import, decode, resize, quantize, write, build-plan, and display — well above the `<= 10` complexity target in `AGENTS.md`. Extract a `run_single(args) -> int` helper and let `main` only parse + dispatch. |

## code duplication

| id | status | effort | description |
|----|--------|--------|-------------|
| DUP-01 | open | S | Palette resolution + `log.info("palette '%s' with %d colors...")` is duplicated between `main` and `_run_batch_mode` in `legome/cli.py`. Lift into a `_load_and_log_palette(args)` helper. |

## architecture/modularity/SOLID

_(no open findings — modules are small, single-purpose, lazy-imported.)_

## decoupling

_(no open findings — cv2/numpy/scipy imports are localized to the call sites that need them.)_

## business/design patterns/DDD

| id | status | effort | description |
|----|--------|--------|-------------|
| PAT-02 | wontfix | S | Factory not added — `load_palette()` already is the factory; further indirection would be ceremony. Recorded to avoid re-litigating in future scans. |

## reliability/correctness

| id | status | effort | description |
|----|--------|--------|-------------|
| REL-15 | open | S | `apply_palette(method="lut3d")` silently ignores the `chunk_pixels` argument (the LUT path indexes the whole image at once). Either raise `ValueError` when both are passed non-default, or log a one-line warning, so users don't think they tuned a knob that did nothing. |
| REL-16 | open | S | `_run_batch_mode` in `legome/cli.py` is typed as `(args, in_dir: Path)` with no return annotation and `args` untyped. Add `-> int` and import `argparse.Namespace` for the annotation; matches `main`'s contract. |
| REL-17 | done | S | `legome/processor.py:77` imported `scipy.spatial.cKDTree`, which is a deprecated alias and not exposed by current scipy type stubs (pyright/Pylance `reportAttributeAccessIssue`). Switched to `scipy.spatial.KDTree` (same C-backed implementation since scipy 1.6). |

## observability

| id | status | effort | description |
|----|--------|--------|-------------|
| OBS-03 | wontfix | S | Built-in `--timing` flag rejected. Users who need wall-clock numbers can wrap the CLI in `time legome ...` (single-image) or measure inside their batch loop. Adding a bespoke flag is maintenance cost for negligible payoff. |

## lego authenticity

| id | status | effort | description |
|----|--------|--------|-------------|
| LEGO-04 | open | M | Expand the Lego DB beyond solid colors (transparent, metallic, glow). Requires sourcing canonical RGB values for each new entry; deferred until those references can be verified. |

## build plan

| id | status | effort | description |
|----|--------|--------|-------------|
| BUILD-02 | wontfix | M | Multi-page A4 PDF layout for very large mosaics. PDF output explicitly rejected for v1; a single high-resolution PNG covers every mosaic size used in practice and avoids a new dependency. Kept on the board so future scans do not re-propose it. |

## file format / ergonomics

| id | status | effort | description |
|----|--------|--------|-------------|
| FMT-01 | done | S | Evaluated JSON vs TOML, YAML, CSV, `.py`, `.npy`, `.gpl`. JSON kept as canonical (stdlib, structured metadata, diff-friendly). `.gpl` adopted as secondary in SCAL-06. Kept on the board so the trade-off is not re-litigated. |

## packaging

| id | status | effort | description |
|----|--------|--------|-------------|
| PKG-01 | open | S | `processor._build_3d_lut` uses `scipy.spatial.cKDTree` for the fast path (with a documented numpy fallback), but `scipy` is absent from both `dependencies` and `optional-dependencies` in `pyproject.toml`. Add `scipy>=1.11` to a `perf` extra so the fast path is reproducible from a wheel install. |
| PKG-02 | open | S | `pyproject.toml` `Source = "https://github.com/legome/legome"` is a placeholder; the org does not exist. Update to the real upstream URL once known, or drop the entry. |

## ci/automation

| id | status | effort | description |
|----|--------|--------|-------------|
| CI-04 | done | S | `.github/workflows/ci.yml` added: matrix runs ruff, mypy, and pytest on Python 3.10/3.11/3.12. |
| CI-05 | open | S | `README.md` advertises `.pre-commit-config.yaml`, but the file does not exist. Either add the file (ruff + ruff-format + mypy hooks) or remove the line from the README "Project layout" block. |
| CI-06 | done | S | `.gitignore` added covering `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.coverage`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, virtualenvs, and common editor/OS junk. |

## quality assurance

| id | status | effort | description |
|----|--------|--------|-------------|
| QA-01 | open | S | `AGENTS.md` mandates cyclomatic complexity ≤ 10, but `[tool.ruff.lint] select` only lists `E,F,W,I,UP,B,SIM`. Add `"C90"` and `tool.ruff.lint.mccabe.max-complexity = 10` so the rule is enforced (would surface COMP-01). |
| QA-02 | open | S | No coverage gate is wired into CI; `pytest-cov` is a dev dep but nothing fails the build below a threshold. Add `--cov=legome --cov-fail-under=95` to the pytest step once CI-04 is wired up. |

## documentation

| id | status | effort | description |
|----|--------|--------|-------------|
| DOC-01 | wontfix | S | Dedicated `CHANGELOG.md` rejected. `git log` and the per-commit messages already document the change history at a finer granularity than a Keep-a-Changelog file would; maintaining both would risk drift. Recorded so future scans do not re-propose it. |
| DOC-03 | open | S | Well-known Bricklink IDs are populated in `legome.lego_colors.LEGO_COLORS`, but ~10 niche entries (e.g. `Earth Green`, `Earth Blue`, `Flame Yellowish Orange`) still have `bricklink_id=None`. Verify against https://www.bricklink.com/catalogColors.asp and fill in the remaining IDs. |
| DOC-04 | open | S | `README.md` CI badge URL (`https://github.com/legome/legome/actions/workflows/ci.yml`) points at a placeholder org/repo. Update once the canonical upstream is published (paired with PKG-02). |
| DOC-05 | open | S | `README.md` "Tests, lint, type-check" section claims `95 tests, 99% cov` and the "Project layout" block separately claims `131 tests, ~99% coverage`. Pick one source of truth (the pytest run) and align both lines. |
