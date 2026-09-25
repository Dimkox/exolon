# Review: security_reviewer — part 1 (product / build-settings scope)

- Change: `20260924-complete-wave-d-specification-and-release-audit-8341b7`
- Tree: `/home/pall/projects/.exolon-wave-d/exolon` @ `84b7813f0dc9c8f25c93967908df2410dc385da2`
- Base compared against: `295690b` (confirmed ancestor via `git merge-base --is-ancestor`)
- Receipt bound by the brief: `ecff8744067d5579` @ 2026-09-25 02:13:36Z
- Mode: read-only over the tree; the only write is this file. Mutations ran in a
  `git clone --no-hardlinks` at `/tmp/secd-mut` (restored to pristine afterwards).
- Verification harnesses run on the pristine tree:
  - `engineering/.../evidence/stage_boundary_check.py` → 10/10 PASS, rc=0 (phase D1)
  - `engineering/.../evidence/macos_handout_check.py` → 10/10 PASS, rc=0 (phase D1)
  - `engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/wave_c_check.py` → `ALL_WAVE_C_PROBES_PASS | probes=9 failed=0`, rc=0

## Item 1 — Build identity untouched — **PASS**

Measured base→HEAD, not from checker output:

- `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` at base
  `295690b` pbxproj `:1415/:1416/:1419` and `:1434/:1435/:1438`; at HEAD
  `84b7813` `:1445/:1446/:1449` and `:1466/:1467/:1470`. Byte-identical lines, exactly 2
  occurrences per revision.
- A sorted-line count diff of all `CODE_SIGN*`/`DEVELOPMENT_TEAM` lines between the two
  revisions shows exactly one delta: the added `CODE_SIGN_ENTITLEMENTS = Exolon/Exolon.entitlements;`
  (×2). No value change, no team id, no real identity.
- The full pbxproj build-settings delta base→HEAD is exactly five added lines and no other
  setting edits: `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` (project Debug),
  `CODE_SIGN_ENTITLEMENTS` (×2, target configs), `ENABLE_HARDENED_RUNTIME = YES` (×2, target configs).
- `OTHER_CODE_SIGN_FLAGS` / `CODE_SIGN_INJECT_BASE_ENTITLEMENTS`: 0 occurrences at HEAD.
- Independently enforced by the checker: `macos_handout_check.py:1653-1659` fails if the ad-hoc
  sentinel stops being `"-"` or `DEVELOPMENT_TEAM` becomes non-empty ("a signing identity would
  now be in the tree, which this change must not introduce").

**Ruling:** the change does NOT introduce any signing identity. Ad-hoc + Manual + empty team are
preserved verbatim; hardened runtime and an empty entitlements plist were added, identity was not.

## Item 2 — ENABLE_HARDENED_RUNTIME exactly in both target blocks — **PASS**

Parsed per `XCBuildConfiguration` block (not grep counts):

- Block map: `800000000000000000000001/2` are project-level and `800000000000000000000003/4`
  target-level, per the `XCConfigurationList` bindings at pbxproj `:1486-1503`
  (`900…001` "for PBXProject", `900…002` "for PBXNativeTarget \"Exolon\"").
- In-file occurrences of `ENABLE_HARDENED_RUNTIME`: exactly 2, at `:1450` (inside the `800…003`
  Debug block spanning `:1442-1461`) and `:1471` (inside `800…004` spanning `:1463-1482`).
  A block-body parse confirms neither project block contains the key.
- The two target blocks are byte-identical modulo their `name = …;` line (measured: True),
  so the INV-001 Debug/Release symmetry holds with the key present in both.

**Flip test (in `/tmp/secd-mut`):** deleting exactly the `:1471` line (one-sided removal) →
`macos_handout_check.py --only entitlements_and_hardening_shape` FAILs rc=1:
"must appear exactly twice … found 1 | 800000000000000000000004 lacks ENABLE_HARDENED_RUNTIME = YES".
The checker also carries its own in-memory one-sided control (`macos_handout_check.py:1674-1680`).
Green-on-pristine control run confirmed immediately before the mutation.

## Item 3 — Exolon/Exolon.entitlements — **PASS**

- Tracked: `git ls-files Exolon/Exolon.entitlements` → the path.
- Parses via `plistlib` to a `dict` with **0 keys** — the file body is `<dict>\n</dict>` only;
  no `get-task-allow`, no `-----BEGIN`, no sandbox key (also enforced at
  `macos_handout_check.py:1661-1671`, which requires `sorted(keys) == []`).
- Referenced identically (`Exolon/Exolon.entitlements`) by `CODE_SIGN_ENTITLEMENTS` in both
  target configs: pbxproj `:1444` and `:1465`. These are the file's only two pbxproj mentions —
  it is **not** added to any Resources `PBXBuildFile` phase, so it is consumed as signing input
  only, not bundled.
- Location `Exolon/Exolon.entitlements` is outside `Exolon/Resources`, so it cannot touch wave C's
  blob-territory guard (`wave_c_check.py:18`: "Exolon/Resources is blob-identical to the route base").
- **C's no_invented_content stays green:** full `wave_c_check.py` run at HEAD →
  `ALL_WAVE_C_PROBES_PASS | probes=9 failed=0` (probe list includes `no_invented_content`,
  `wave_c_check.py:1972`).

## Item 4 — Debug warp gating — **PASS**, with one Suggestion (checker gap, not a product defect)

Product-side, all measured in `Exolon/GameCore/GameScene.swift` at HEAD:

- Call site wrapped: `#if DEBUG` / `applyDebugWarpIfNeeded(...)` / `#endif` at `:186-188`.
  The whole feature (doc, `debugWarpTarget`, `applyDebugWarpIfNeeded`) lives in a single
  `#if DEBUG … #endif` spanning `:191-240`; no `EXOLON_DEBUG_WARP` reference exists outside it
  (asserted by `stage_boundary_check.py:628-631`, green).
- Release cannot contain the code path: `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` is declared
  **exactly once**, in the project-level **Debug** block only (pbxproj `:1424`, block `800…001`
  bound to `900…001` "for PBXProject"); the project Release block `800…002` and both target blocks
  carry no such key (block-body parse, Item 2 method). A Release-configuration build therefore has
  no `DEBUG` condition and `#if DEBUG` strips the warp at compile time.
- Runtime inert without the env var: `guard environment["EXOLON_DEBUG_WARP"] != nil else { return }`
  at `:222`; unset ⇒ no jump, no output.
- Message free of literal map names: the only two strings are the refusal
  `"…must be one of the shipped level names, format LxxSyy"` (`:225-226` — placeholder, not a name)
  and the echo `"EXOLON_DEBUG_WARP=\(target) … via transition(to:)"` (`:230-231` — interpolated
  caller value). The three literal `"L01S01"`s in the file (`:12, :942, :1235`) are the pre-existing
  default start level, outside the warp block.
- Routes through `transition(to:)`: `transition(to: target)` at `:232`, the real production
  transition at `:859-902` — P1-9 witnesses fire inside it: `emitZoneTransition` (`:861`),
  `tickDriver.reset(reason: .zoneTransition)` (`:866`), zone record + `isStageStart` spawn rule
  (`:876-889`), `saveCheckpoint()` (`:901`).
- Bounded target: value must pass `allowed.contains(target)` against `includedLevels` (`:99, :216-218, :224`);
  the checker executes the bound with adversarial controls (`stage_boundary_check.py:652-667`:
  `../Secret`, `L05S99`, lowercase, short forms all refused).

**Mutation test (in `/tmp/secd-mut`):** moved `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` out of
the project Debug block into the **target Release** block (count stays 1, placement makes a Release
build compile the warp). Result on the wave-D suite: **rc=1 — red, as required**:
`macos_handout_check.py` FAILs `probe_contract_green` and `cutover_set_exact`, both triggered by
the release-layer `target_cfg_symmetric` red (the target Debug/Release blocks stop being identical).

**Suggestion (low severity, checker-coverage, product tree not affected):** the guard that
`GameScene.swift:196` names as the warp's own validator — `stage_boundary_check.py::warp_debug_only` —
does *not* independently catch this move: its `count == 1` test (`:640-643`) passes on a move, and
its block regex (`:644-645`) binds only the project-GUID Release block `800…002`, never the target
Release block `800…004`. Detection currently relies on a different invariant (config symmetry) in a
different script. A copy (count=2) *is* caught by `:640`. Fix would be one more assertion binding the
setting's owning GUID (must be `800…001`); worth a follow-up ticket, not blocking this change.

## Verdicts

| Item | Scope | Verdict |
|---|---|---|
| 1 | identity byte-equal to base, no signing identity introduced | **PASS** |
| 2 | hardened runtime in exactly both target blocks; flip test red | **PASS** |
| 3 | empty tracked entitlements plist, dual reference, outside Resources, C green | **PASS** |
| 4 | warp Debug-compiled, inert, name-free messages, real transition path; mutation reddens D suite | **PASS** (1 Suggestion: `warp_debug_only` target-Release blind spot) |

Overall part 1: **PASS**. No security-relevant product defect found in the build-settings scope at
`84b7813`; the single finding is a checker-coverage suggestion with the exposure already closed by
`target_cfg_symmetric` in the same suite.
