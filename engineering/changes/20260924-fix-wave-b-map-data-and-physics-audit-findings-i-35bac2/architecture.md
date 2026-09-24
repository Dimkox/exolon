# Architecture — wave B (map-data physics)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Current behavior
Ground/spawn math, bullet culling (x>528), beam instantiation (per-side 25 HP fields) and piston
anchoring are computed independently per subsystem; none queries a shared Collision surface API.
Measurements: issues #5/#6/#7/#9 and merged evidence `20260921-...2e7698/evidence/`.

## Proposed behavior
One SpriteKit-free surface-query primitive (ground_y(x) over Collision cells) feeds spawn,
piston anchor and foot-band math. Beam pairs become one field entity (25 HP shared). Bullet cull
bound derives from the player clamp constant.

## Components and boundaries
- Collision/surface query: `TMXMapLoader`/`TMXLevelRuntime` (loader is already SpriteKit-free and
  harness-tested — extend it, don't fork).
- Bullets: `BlasterBullet.swift` cull guard + `GameScene` update path.
- Beams: `LevelObstacles.swift` force-field init/hit accounting.
- Pistons: `LevelObstacles.swift` anchor computation.
- Meters: `evidence/wave_b_check.py` (stdlib) + reuse `evidence/harness/run.sh` pattern of wave A
  and the loader harness of `20260919-...7db1f3`.

## API and event contracts
No wire contracts. Public invariants: ground_y(x) returns the top of the highest solid cell at x
in scene coordinates (bottom-left origin, 512×384 logical — the same coordinate-space rule 6 of
`engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/analysis-integration_architect.md` §7).

## Governance context
No `governance/` in tree — n/a.

## Bitrix-specific impact
n/a.

## Decisions
Brief rulings 1–5 are binding; spec gap on beam per-side visuals (issue #9 silent) → ruling: keep
both segments visible, one HP pool, single destruction.

## Risks and mitigations
- Difficulty shift on 125 maps → per-map delta table in evidence, reviewed;
- rebase collision with wave A (`GameScene`, `LevelObstacles`) → narrow seams + rebase onto A
  after A merges;
- ±16 px traps from the audit (0-based zone formula, half-tile offsets) → the meter must reuse
  `int(zoneNumber)==(stage-1)*25+(scene-1)` validation before trusting names.
