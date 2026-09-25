# Wave B: map-data physics fixes (P1-1, P1-2, P1-3, P1-5)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2`
Route base `295690b` · branch `codex/wave-b-mapdata-physics-20260924` · worktree sibling of main
Risk: low(green) · Write owner: `general_implementer`

## Problem

Four audited defects where runtime physics disagrees with the TMX Collision data (numbers from
`engineering/reports/exolon-full-audit-20260920-v3.md` and issues #5/#6/#7/#9):

- **P1-2** spawn vs marker vs surface: relative to the `vitorc` MARKER feet, 37/125 maps land on a
  Collision top, 59 spawn +16 px above it and 29 −16 px below (audit control split 37/59/29,
  reproduced by `spawn_old_rule_hist`); by the runtime true-landing criterion only ~34 maps were
  ever exact — so the fix must remove the ±16 marker-vs-surface skew, bounded per amended AC-001.
- **P1-3** bullets culled at x>528 while the player clamp is x=544 (`Player.swift:128`) and 61
  maps carry Collision right of x=512 — a dead corridor where shots vanish. The born-dead half of
  the same defect (amended AC-004): the blaster origin is player x+34, so shots from x ∈ (494,544]
  were culled at the first update under the old 528 bound, and from x ∈ (526,544] their origin
  exceeds even clamp+width (560); grenades carried an inline x>536 cull against reachable throw
  origins up to 548.
- **P1-5** beam_up/beam_down: each side instantiates its own 25-hit-point field → 50 per beam;
  expected behavior per issue #9 is 25 total. Note: ORIGINAL_MECHANICS.md:26/:121-127 words one
  field per source marker; the pair reading is ruled from issue #9 + data (adjacent sourceX
  columns, 32 px box overlap on 10/10 beam maps) and cited as such.
- **P1-1** 46 pistons on 27 maps: anchor taken from the object marker row, not the Collision
  surface below it — issue #5: world-bottom sits BELOW the player's foot line. Measured truth
  (corrected control): 40 anchors −64 px under the standing surface (tread exposes edge-only,
  never intersects), 3 at −48, 3 columns hold no cell under the tread and anchor to the fallback
  plane; only 6/46 were lethal at the old anchor.

## Outcome

Every one of the four is computed from the same Collision data the renderer/collider uses — no
per-map magic offsets — and each has a committed self-checking meter over all 125 maps whose
reverted control fails.

Runtime-exposure disclosure (AC-001 amendment 2): the resolved spawn Y is consumed by the game
only at stage-start entries, app start and death respawns — ordinary zone transitions carry the
previous zone's Y (`GameScene.swift:638-646`), i.e. ~5-6 entries per playthrough see the fix
directly. The P1-2 repair remains worth shipping at that exposure; the deeper entry-position
walk-locks measured in `analysis-p1-2-spawn.md` §3 are explicitly out of this bounded wave
(factory data regeneration / separate engine change).

## Scope

### In scope

- Spawn/ground alignment: derive spawn Y through the same surface query used at runtime.
- Bullet culling bound ≥ player max x (544) + bullet width; screen-transition trigger (x>510)
  unchanged.
- One shared 25-hit-point model per beam pair (sides become visual segments of one field entity).
- Piston `groundY` from the Collision cell under the piston base; hitbox reaches the foot band.
- Meters: extend/reuse the merged P1-1 probe and the spawn measurement into
  `evidence/wave_b_check.py` (stdlib Python over TMX + Swift loader-harness checks).

### Out of scope

- Event log and state-machine fixes (wave A, parallel), content/factory (wave C), spec/release
  (wave D), any TMX data edits.

## Design rulings

1. Fixes are **code-side, derived from Collision data**; patching map files is forbidden
   (data is canonical from the original; the renderer already agrees with Collision).
2. **P1-5 semantics**: the pair shares one HP pool of 25 (issue text "ожидаемое суммарное
   поведение — 25"); per-side 50 is a defect. Destroying the field removes both sides together.
3. **P1-3 bound**: derived from the existing player clamp constant, never a new magic number;
   culling may be later (e.g. viewport width + margin) but must be ≥ 544 + bullet width.
4. **P1-2/P1-1 use one shared surface-query API** (single source of truth for "ground at x");
   a second ad-hoc ground computation is forbidden.
5. Wave-A event log will rebase over this branch; keep changed seams narrow (spawn configure,
   bullet update/cull, beam init, piston anchor) so rebase is mechanical.

## Constraints

- Backward compatibility: no gameplay rule changes except the four defects; difficulty of the 125
  maps must not silently shift (meter prints per-map deltas; any map whose piston/beam reach
  changes beyond the defect rectification must be explained in evidence).
- Data/privacy: n/a. TMX files read-only.
- Performance: full-tree meters ≤ 60 s.
- Operational: rollback = revert (pure data/logic change, no schema/state).

## Analysis

Repo facts (exact functions, current formulas, harness entry points) go to
`evidence/analysis-*.md` produced by the route's read agents or the implementer's exploration.
