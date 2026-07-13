# TODO

Review findings per `AGENTS.md` categories. Format: `id | status | effort | description`.

Status: `open` | `in-progress`. Effort: `S` (<1h) | `M` (1-4h) | `L` (>4h).

Closed items (done / wontfix) are removed from this board — the commit history is the record. Add new findings under the matching category before reporting in chat.

Last rescan: 2026-07-04 (full re-scan, all categories).

## security

_(no open findings)_

## performance

_(no open findings)_

## scalability

_(no open findings)_

## concurrency

_(no open findings — `ProcessPoolExecutor` workers share no mutable state.)_

## code complexity

_(no open findings — enforced by ruff `C90` at max-complexity 10.)_

## code duplication

_(no open findings)_

## architecture/modularity/SOLID

_(no open findings — modules are small, single-purpose, lazy-imported.)_

## decoupling

_(no open findings — cv2/numpy/scipy imports are localized to the call sites that need them.)_

## business/design patterns/DDD

_(no open findings)_

## reliability/correctness

_(no open findings)_

## observability

_(no open findings)_

## lego authenticity

| id | status | effort | description |
|----|--------|--------|-------------|
| LEGO-04 | open | M | Expand the Lego DB beyond solid colors (transparent, metallic, glow). Requires sourcing canonical RGB values for each new entry; deferred until those references can be verified. |

## build plan

_(no open findings)_

## file format / ergonomics

_(no open findings)_

## packaging

_(no open findings)_

## ci/automation

_(no open findings)_

## quality assurance

_(no open findings)_

## documentation

| id | status | effort | description |
|----|--------|--------|-------------|
| DOC-03 | open | S | Well-known Bricklink IDs are populated in `legome.lego_colors.LEGO_COLORS`, but ~10 niche entries (e.g. `Earth Green`, `Earth Blue`, `Flame Yellowish Orange`) still have `bricklink_id=None`. Verify against https://www.bricklink.com/catalogColors.asp and fill in the remaining IDs. |
