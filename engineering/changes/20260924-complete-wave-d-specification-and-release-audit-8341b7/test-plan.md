# Test plan — wave D

Layers (per `analysis-architect.md`): L0 characterization → L1 pure-ledger table (Linux) →
L2 stream predicate (after rebase onto wave A) → L3 macOS handout observation generated from the
L1 table. Every layer carries per-component mutation controls; an assertion that cannot flip is
itself a failure.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Stage sequence identity: points == lives×1000 + bravery(0|10000) + timed(0|1000|3000|5000|7000), once per completed_zone per playthrough, suppression witness intact, clamp case applied==min(earned, 999999−before) | `stage_boundary_check.py::sequence_components_identity` |
| P0 | Bravery activation-latch falsifies OM:142-vs-118: toggling exo in one changing room of the stage forfeits bravery at boundary even if suit is OFF at boundary | `stage_boundary_check.py::bravery_latch_distinguishes` |
| P0 | Handout contract: valid synthetic green; each of 10 consistency rules flips red on its contradictory fixture; tampered binding (head/blob/artifact) → STALE, never green | `macos_handout_check.py::handout_controls_flip` |
| P0 | No machine evidence → `MACOS_EVIDENCE=ABSENT (unverified)` rc=1 (distinct from FAIL semantics) | `macos_handout_check.py::absent_is_unverified` |
| P1 | Agent boundary: Track B refuses off-tty (exit 77), forbidden argv/env aborts scan matches list, no code path accepts credentials | `macos_handout_check.py::agent_boundary` |
| P1 | Probe back-compat: merged `release_layer_check.py` (unmodified, subprocess) rc unchanged on D-2 tree; verdicts parse as key=value only; M-9 out-of-tree roots enforced; M-8 flush barrier verified by local bash simulation loop | `macos_handout_check.py::probe_contract_green`, `::flush_barrier`, `::build_roots_out_of_tree` |
| P1 | Timed ladder determinism: phase recomputed from (tick−stageStartTick)/1800 matches emitted component; absolute ticks only in pure harness | `stage_boundary_check.py::timed_ladder_deterministic` |
| P2 | Warp: absent in Release (`#if !DEBUG`), off without env, routes through transition(), stderr echo | `stage_boundary_check.py::warp_debug_only` |
| P2 | Cutover exactness: after D-1, merged checker reds ONLY the measured {hardened_runtime_key_count}; observed⊆declared, non-empty, per-member liveness | `macos_handout_check.py::cutover_set_exact` |

## Automated checks
- Unit (Linux): L0/L1 ledger tables, consistency-rule synthetics, bash simulation for M-8,
  argv-scan fixtures.
- Integration: subprocess run of merged checker; schema validation stdlib-only.
- Contract: `engineering/contracts/schemas/macos-probe-report-v1.schema.json` vs handout fixtures.
- E2E (macOS, human): Track A full run per handout protocol → receipts committed AFTER the run;
  Track B only under the double env gate by the owner.
- Static: `bash -n` probe; `swiftc -frontend -parse` D-1 files; `grok_verify --mode pr` recorded last.

## Manual checks
- Owner run on clean macOS: C-10…C-16 (Track A) and optionally C-20…C-31 (Track B, Developer ID).
  Play-observation E16 via `EXOLON_DEBUG_WARP=L05S25` instead of an 11-minute walk.
