# analysis-repo_explorer — tree /home/pall/projects/.exolon-wave-e1/exolon @ 0b0dea9 (route 8f7b02)

Saved verbatim by the controller from the read-only lane's report (that lane had no write tool).
All six E1 targets confirmed on this HEAD; two minor anchor drifts noted inline.

## T1 — 20260919 harness run.sh missing GameConstants.swift → rc=1 — CONFIRMED
- `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/run.sh:50-51` —
  step-4 file list is verbatim `swiftc -I "$BUILD" -L "$BUILD" -lCoreGraphics \` /
  `"$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/loader"`: two translation units,
  **no GameConstants.swift**.
- Sole declaration `enum GameConstants` at `Exolon/GameCore/GameConstants.swift:4`; neither
  compiled file declares it.
- run.sh compiles a byte-identical copy of `Exolon/GameCore/Levels/TMXMapLoader.swift` +1 import
  (run.sh:37-45); that file uses `GameConstants.*` at `TMXMapLoader.swift:107,110-112,120,167,
  234-236` — introduced by `6c7dfe5` (wave B), `git log -S` on that file returns that one commit.
- Read-only lane did not execute run.sh (it mkdir's /tmp); reproduced non-writingly:
  `swiftc -typecheck` over the exact run.sh:51 file-set **exits 1** (first diagnostic
  `TMXMapLoader.swift:1:8: error: no such module 'CoreGraphics'` — the missing-module error
  aborts before name lookup; the two-file set provably cannot link the only GameConstants
  declaration). With `set -euo pipefail` (run.sh:11) step-4 nonzero aborts rc=1. Committed
  `last-run.txt:3` records `HEAD=52795d1 rc=0` — pre-regression (verified by merge-base);
  wave-C's review-test.md "Ran it: rc=0" is likewise pre-wave-B. **rc=1 is the correct current
  expectation.**

## T2 — v3_measurements.py:89 HANDLED — CONFIRMED at exact line
- `.../7db1f3/evidence/v3_measurements.py:89` — `HANDLED = ("beam_", "blinker", "changing_room",
  "stage_end", "beacon_base", "control_beacon", "topdown_electro")` — hand-copied mirror of
  `Exolon/GameCore/Levels/TMXMapLoader.swift:655-661` (same 7 families, different order).
- Consumers `marker_split` :224-241, beam-drop control :246, feeding EXPECTED
  markers_total/read/lost = 127/76/51 (:43-48). Docstring :2-13 binds every v3 report number to
  this program's EXPECTED — any matcher or HANDLED change obligates regeneration. Also
  characterized in `.../2e7698/evidence/analysis-p1-7-markers.md:289-290`.

## T3 — wave_b_check.py wave_base() fallback — CONFIRMED (anchor drift from "~:65")
- `...35bac2/evidence/wave_b_check.py:646` def wave_base(), docstring :647-653,
  `git merge-base HEAD origin/main` :654-657, absent-origin fallback `return "295690b"` :660.
- On this tree origin/main == HEAD → merge-base = HEAD → added-lines scan (:1130/:663) sees an
  EMPTY diff; the wide fallback fires only in clones without the remote ref.

## T4 — wave-A M3 timing assert + untouchable hard allocation check — CONFIRMED
- ~4 µs assert lives in the Swift harness: `...32f59c/evidence/harness/main.swift:1142-1143`
  `Harness.check(producerNs > 1 && producerNs * 60 < 5_000, "60 locked appends must stay near
  4 us (M3)…")`; band = M2/M3 sizing 55–70 ns (:1140-1141,:1150-1151), 0.5 %/5 % gates
  :1146-1149, exported as `emission_cost` :1152-1158; M3 source figure 69.6 ns/pair
  (`analysis-architect.md:54`).
- Python mirror `emission_cost_budget` at `gameplay_log_check.py:758` (AC-006, :1895): budget
  :765-766, alarm margin :770-772, sane-band 0<producer<1000 :773-775, formatting control ≥5×
  :776-778, drain ≥8×3600 :779-780.
- **Must NOT be softened**: `hot_path_is_allocation_free` at :1281 (INV-004, :1907) — static
  scan of 4 hot-path frames (:1285-1290), ALLOCATION_PATTERNS :1306-1311, offenders
  :1313-1314. Adjacent distinct: frame_step_budget (SIG-003) :1818.

## T5 — warp_debug_only GUID-anchored regex — CONFIRMED (anchor drift)
- `...8341b7/evidence/stage_boundary_check.py:628` def warp_debug_only (AC-007); reviewer hint
  ":640-645" now corresponds to the pbxproj block :652-659.
- Regex :657-658 binds project-level Release GUID `800000000000000000000002` only. Cross-check
  with `Exolon.xcodeproj/project.pbxproj`: project list `900…001` (:1081) owns `800…001 Debug`
  (:1416; the single SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG at :1424) and `800…002 Release`
  (:1429); native target list `900…002` (:1053) owns `800…003 Debug` (:1441) and `800…004
  Release` (:1462) — **target-level `…004` is outside the anchor**, currently caught only
  indirectly by the exactly-once count :653-655. Function in place.

## T6 — wave_scan input set — 20 Swift files
Product (16): FixedTickDriver (+152), GameplayEventLog (+1186), GameplayEventSink (+1199),
LauncherBonusState (+57), StageBoundaryLedger (+264), GameConstants (+86/−2), GameScene
(+559/−94), InputState (+27/−3), TMXLevelRuntime (+168/−33), TMXMapLoader (+338),
TMXTileMapRenderer (+7/−38), LevelObstacles (+43/−23), Player (+73/−10), BlasterBullet
(+14/−3), Grenade (+8/−2), AppDelegate (+38).
Evidence harness (4): D ledger-xcheck/main.swift (+90), B wave_b_harness/main.swift (+125),
A harness coregraphics_shim.swift (+11), A harness main.swift (+1202).
Working tree clean; untracked = only this E1 package's .md/.yaml/.json → union == the same 20.
295690b confirmed ancestor of HEAD.

## Unresolved
None — all six targets present on 0b0dea9. Caveats: T3/T5 line-hints drifted as noted; T1's
rc=1 reproduced via write-free `swiftc -typecheck` (exit 1) + static declaration chain rather
than full run.sh execution (read-only lane forbids its /tmp writes).
