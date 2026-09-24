# Release plan — wave C

## Deployment
PR-only delivery (`codex/wave-c-content-factory-20260924` → `main`), merged LAST in series
A → B → C. Merge only after the external App-owned Trust CI check on the exact head SHA and both
route review receipts (code, test) are present. No deployable artifact; the next release train
(wave D remainder) packages.

## Feature flags / staged rollout
- No runtime flag needed: classifier changes are additive (`classify()` preserves the original
  test ORDER; the exhaustive switch removes the silent-drop path); safe models render only in the
  F1 debug overlay, so shipped visuals change only where content was previously LOST (32 maps,
  3 families).
- Beam-arm goldens: after wave B merges, run the committed fail-closed protocol
  (`evidence/ac005-rebase-protocol.txt`: `--record-baseline --base <ref>`, exact digest, cited
  ruling, no wildcards) and nothing else — drift reddens before any excuse exists.

## Metrics and alerts
- `python3 evidence/wave_c_check.py` (9 probes / 59 controls, ≤3 s, stdlib) green on the head
  (local preflight; the external exact-SHA check remains merge authority).
- Harness `run.sh`: REAL MAPS 125/125 failures=0 (loader contour; the classifier itself is
  compiled AND executed inside `wave_c_check.py`, not by run.sh — test-review F4 attribution fix).
- `git status Exolon/Resources` empty at every rebase step (FORBID-001 guard).

## Go/no-go criteria
- **HARD CONDITION (test review delta):** macOS `xcodebuild` of the shared scheme must run and its
  result be recorded in this PR **before merge** — two of three changed Swift files have zero
  semantic verification on Linux; without the macOS build, residual F3 is blocking, not accepted.
- AC-001..AC-005 green on the final fingerprint (verification receipt recorded —
  `.grok-stack/runtime/receipts/`); code_review + test_review receipts bound to the same
  fingerprint (census after F1/F6 round: 59 assertions / 58 distinct names — `bogus_substring_rejected`
  asserted in two probes); Deviations D1/D4 acknowledged (no new .swift files → no pbxproj edits; legacy
  `v3_measurements.py` mirrors belong to another route and stay untouched);
- residual risks carried in the PR body with owner actions:
  R1 (v3 mirrors still encode 76/51 — cannot detect regressions of this fix),
  R2 (`GameScene.swift` is parse-gated only; `addDebugRect(...label:)` needs one macOS type-check).
