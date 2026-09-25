# Test plan — wave C

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Marker resolution **127 of 127 `source_marker` objects** (that is 127 *instances*; the corpus holds 11 distinct `sourceBlock` values, all 11 claimed) over all 125 maps; the three formerly-ignored types produce typed objects or labeled safe models; baseline 76-of-127 table retained as control | `wave_c_check.py::marker_coverage_all_maps`, `::marker_baseline_reproduced` |
| P0 | Digest manifest: all 24 declared-identical pairs hash-equal; all non-declared pairs differ; uniqueness count == 101 | `wave_c_check.py::level_pair_manifest_pinned` |
| P1 | Negative control: a declared pair that is **not** identical in the shipped data is rejected, and every tampered manifest declaration is rejected **even after the forger recomputes `body_sha256`** | `wave_c_check.py::manifest_selfcheck` (`declare_nonidentical_pair_rejected`, `unkeyed_reseal_rejected`, 10 controls; corroborated by `::level_pair_manifest_pinned`) |
| P1 | FORBID-002 rendering clause: the debug overlay must consume `safeModelMarkers` and carry the label; deleting the loop or stripping the label reddens the probe | `wave_c_check.py::safe_models_are_labeled` (`overlay_deletion_detected`, `overlay_label_strip_detected`) |
| P1 | Syntax gate for all three changed Swift files is executed, and proven able to fail | `wave_c_check.py::safe_models_are_labeled` (`swift_parse`, `parse_gate_detects_a_broken_file`) |
| P1 | Regression: output for the 76 already-covered markers byte-identical pre/post change | `wave_c_check.py::unchanged_marker_output` |

## Automated checks
- Integration: stdlib Python meters over the tree (factory invoked in-process).
- Unit: marker-classifier per-type decisions (typed vs safe vs error).
- Contract: `engineering/contracts/level-content-v1.json` validated for shape + counts.
- E2E: one map from each newly-fixed type renders on macOS build (manual, recorded in PR).
- Static: `swiftc -frontend -parse` touched Swift; `grok_verify --mode pr`.

## Manual checks
- macOS spot: L03S09 vs L04S11 render identically, as **ruled** in change f2d90a (the pair is stage 3→4
  and the recolored-stage-2 premise does not reach it — see the manifest's `pair_notes`); a
  waggon/gunMachine/mushroom map shows the new safe-model outlines in the hitbox debug overlay where the
  factory previously dropped them.
- Status wording for the PR: findings P1-7/P1-12 are resolved **by ruling pending merge**; issues #11 and
  #16 remain OPEN (`blocked-on-owner`) until the owner accepts it.

## What "127/127 resolved" does not mean

The meter counts a marker as resolved when the product classifier claims its `sourceBlock`. Per
AC-001 the disposition column is normative evidence: of the 127 `source_marker` **objects** (11
distinct `sourceBlock` **values**), 50 reach gameplay, 51 are labeled safe models (recorded, not
animated), 21 are documented no-ops (`blinker` 19, `topdown_electro` 2) and 5 are write-only
(`stage_end`). "Resolved" is never "behaviour implemented".

## Residuals the net cannot close on this host (measured, not assumed)

- **Swift type-checking covers 1 of 3 changed files.** `TMXMapLoader.swift` (which owns the
  classifier) is genuinely **compiled and executed** by `wave_c_check.py::swift_product_evidence`
  over all 125 maps, with a no-shim build negative control. `TMXLevelRuntime.swift` and
  `GameScene.swift` cannot be type-checked here: `swiftc -typecheck` stops at
  `error: no such module 'SpriteKit'` (`TMXLevelRuntime.swift:1:8`), and the only Linux contour in
  the tree is a CoreGraphics type-rename shim that cannot substitute SpriteKit. Both are now
  **syntax**-gated by the meter (`swift_parse`, with `parse_gate_detects_a_broken_file` proving the
  gate can fail), which is the most `-frontend -parse` can do. Verified: injecting a *type* error
  (`forceFields.append(field.thisIsNotAMember)`) leaves all 9 probes green. A hand-written SpriteKit
  stub was rejected on purpose — type-checking against an API I invented would prove agreement with
  my stub, not with Apple's. Closing this needs `xcodebuild` (E2E below).
- **FORBID-002's rendering clause is source-structural, not visual.** The probe now reddens if the
  overlay loop is deleted or the label is stripped (independently reproduced: the reviewer's case
  R2, which previously stayed green), but it cannot prove the outline actually draws on a Mac.
- **AC-005 is a source-text golden, not an executed-output golden.** It pins the marker records and
  each branch's body (mutations, nodes, textures, balanced-paren `CGRect` geometry, numeric
  literals). A behaviour change reached *through a collaborator's own file* is invisible to it:
  verified that `LevelObstacles.swift` `var hitPoints = 25 → 1` leaves all 9 probes green (the
  reviewer's case R3). That file is untouched by this diff; the gap is in how AC-005 may be read,
  not in what this change shipped. Do not cite AC-005 as "no gameplay regression can ship".
- **The stale mirrors in the other package publish pre-fix numbers about the post-fix tree.**
  See `tasks.md` R1; the meter now reports the divergence instead of leaving it silent.
