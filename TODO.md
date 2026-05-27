# TODO

Review findings per `AGENTS.md` categories. Format: `id | status | effort | description`.

Status: `open` | `in-progress` | `done` | `wontfix`. Effort: `S` (<1h) | `M` (1-4h) | `L` (>4h).

Last rescan: 2026-05-27 (post pyright + C90 sweep).

## security

| id | status | effort | description |
|----|--------|--------|-------------|
| SEC-01 | open | S | `_resolve_palette` accepts any user-supplied `--palette` path; `Path(...).expanduser()` is not called, so `~/p.json` is treated as a literal relative path that may surprise users. Apply `Path(arg).expanduser().resolve(strict=False)` before `load_palette` / `load_gpl` for parity with how `input`/`output` are handled in `legome/cli.py`. |
| SEC-02 | open | S | `ProcessPoolExecutor` pickles `BatchTask` (which embeds the full `Palette`) per task in `legome/batch.py`. Workers receive trusted data — but switch to passing the palette once via `initializer=` to shrink the pickle surface and avoid re-shipping the same `Palette` per file. |

## performance

| id | status | effort | description |
|----|--------|--------|-------------|
| PERF-07 | done | S | `_build_3d_lut` now memoizes the (256³,3) LUT in a 1-slot module-level cache keyed on `palette_bgr.tobytes()`. Batch mode pays the ~64 MB build + KDTree query once per palette instead of once per image. |
| PERF-08 | done | S | `render_build_plan` brick counts switched from a nested Python `for row/col` loop to `np.unique(flat, axis=0, return_counts=True)` — O(N+M) numpy instead of O(N) Python tuple construction. |

## scalability

_(no open findings)_

## concurrency

_(no open findings — `ProcessPoolExecutor` workers share no mutable state.)_

## code complexity

| id | status | effort | description |
|----|--------|--------|-------------|
| COMP-01 | done | M | `cli.main()` split into `main` (parse + dispatch) + `run_single` (single-image pipeline) + small helpers (`_acquire_image`, `_render_and_write_plan`, `_maybe_show`). All ≤10 mccabe, enforced via ruff `C90` (QA-01). `load_gpl` was also split (`_parse_color_row`, `_parse_palette_entries`) to satisfy the same gate. |

## code duplication

| id | status | effort | description |
|----|--------|--------|-------------|
| DUP-01 | done | S | `_load_and_log_palette(args)` helper in `legome/cli.py` now owns palette resolution + the info-line log; both `run_single` and `_run_batch_mode` call it. |

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
| REL-15 | done | S | `apply_palette(method="lut3d", chunk_pixels != DEFAULT)` now raises `ValueError`; the lut3d path indexes the whole image at once, so the knob had no effect. |
| REL-16 | done | S | `_run_batch_mode` and the new CLI helpers (`run_single`, `_acquire_image`, `_render_and_write_plan`, `_maybe_show`) are fully typed with `argparse.Namespace` / `np.ndarray` / `-> int` annotations. |
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
| PKG-01 | done | S | `pyproject.toml` now declares `[project.optional-dependencies] perf = ["scipy>=1.11"]`; `pip install legome[perf]` enables the cached 3D-LUT fast path. |
| PKG-02 | done | S | `pyproject.toml` `Source` URL points at the real upstream `https://github.com/geraldo-netto/legome`. |

## ci/automation

| id | status | effort | description |
|----|--------|--------|-------------|
| CI-04 | done | S | `.github/workflows/ci.yml` added: matrix runs ruff, mypy, and pytest on Python 3.10/3.11/3.12. |
| CI-05 | open | S | `README.md` advertises `.pre-commit-config.yaml`, but the file does not exist. Either add the file (ruff + ruff-format + mypy hooks) or remove the line from the README "Project layout" block. |
| CI-06 | done | S | `.gitignore` added covering `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.coverage`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, virtualenvs, and common editor/OS junk. |

## quality assurance

| id | status | effort | description |
|----|--------|--------|-------------|
| QA-01 | done | S | `pyproject.toml` ruff lint now selects `C90` with `mccabe.max-complexity = 10`; surfaced and forced fixes for `cli.main` (COMP-01) and `gpl.load_gpl`. |
| QA-02 | done | S | `.github/workflows/ci.yml` runs fast tests then slow tests with `--cov-append`; the slow step adds `--cov-fail-under=95`. Combined coverage is currently 96%. |

## documentation

| id | status | effort | description |
|----|--------|--------|-------------|
| DOC-01 | wontfix | S | Dedicated `CHANGELOG.md` rejected. `git log` and the per-commit messages already document the change history at a finer granularity than a Keep-a-Changelog file would; maintaining both would risk drift. Recorded so future scans do not re-propose it. |
| DOC-03 | open | S | Well-known Bricklink IDs are populated in `legome.lego_colors.LEGO_COLORS`, but ~10 niche entries (e.g. `Earth Green`, `Earth Blue`, `Flame Yellowish Orange`) still have `bricklink_id=None`. Verify against https://www.bricklink.com/catalogColors.asp and fill in the remaining IDs. |
| DOC-04 | done | S | `README.md` CI badge + clone URLs updated to `geraldo-netto/legome` (matches PKG-02). |
| DOC-05 | done | S | `README.md` "Project layout" and "Tests, lint, type-check" now both report `162 tests, 96% cov` from a single combined pytest run. |
