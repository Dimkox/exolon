# Requirements — Complete wave-D specification and release audit findings in the Exolon game: P1-10 (end-of-stage bonuses are incomplete versus ORIGINAL_MECHANICS - bravery bonus 10000 and timed bonus 0/1000/3000/5000/7000 at stage boundaries 24/49/74/99/124, plus-one-life capped at 9, exoskeleton cleared and ammo refilled 99/10 - restore the full stage-end sequence in coordination with the wave-A StageBoundaryLedger) and the remaining P1-11 scope (extend the committed release-layer verifier and engineering/runbooks/macos-probe.sh so signing, notarization and archive are checked end-to-end on a clean macOS machine; Linux-decidable parts committed, the macOS run documented as an external handout).

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

Typed ids live in [`change-spec.yaml`](change-spec.yaml); this is the phase status of each, as
measured on the current tree (both checkers report per-name `RESULT` lines; nothing here is a
promise about a future run).

- [x] AC-001 Track A probe contract: mandatory archive + `.xcarchive` inspection, 5-valued
      `key=value` verdicts, exits 77/78, Darwin guard, merged checker rc-invariant —
      `macos_handout_check.py::probe_contract_green`.
- [x] AC-002 M-8 flush barrier and M-9 out-of-tree build roots — `::flush_barrier`,
      `::build_roots_out_of_tree`.
- [x] AC-003 handout contract `exolon.macos-probe-report/1`: schema committed, ten rules each with
      a reddening fixture, binding fields, `ABSENT` distinct from `FAIL` —
      `::handout_controls_flip`, `::absent_is_unverified`.
- [x] AC-004 structural agent/human boundary (double gate + tty, abort-not-redact argv/env scan,
      no credential path, identity only as hashes) — `::agent_boundary`.
- [x] AC-005 ledger sequence as data, per-boundary identity, award before +1, `maxLives`, exo
      clear, shared refill constants, clamp case — `stage_boundary_check.py::sequence_components_identity`,
      `::lives_and_refill_semantics`.
- [x] AC-006 bravery activation latch + owner-approved deterministic ladder, auditor recomputation
      — `::bravery_latch_distinguishes`, `::timed_ladder_deterministic`.
- [x] AC-007 bounded debug warp, Debug-compiled, real `transition(to:)` path, stderr echo
      — `::warp_debug_only`.
- [x] INV-001 single `awardPoints` funnel — `::single_funnel`.
- [x] INV-002 verdicts are `key=value` only — `macos_handout_check.py::verdicts_machine_readable`.
- [x] FORBID-001 no Track B claim — `::no_track_b_claim`.
- [x] FORBID-002 cutover set — `::cutover_set_exact`; see Deviation 9 for the measured difference
      from the literal declaration.
- [x] FORBID-003 no approximate canonical claim — `::ladder_is_declared_deviation`.
- [ ] macOS observation (probe C-00/C-10…C-16, Track B) — **permanently out of reach**: no Apple
      hardware and no Developer ID exist for this project, so `MACOS_EVIDENCE=ABSENT (unverified)`
      is the steady state and not a to-do. The protocol and the checker stay in the tree for a
      hypothetical future machine.

## Failure and edge cases

- Probe exit codes are operational, never verdicts: `0` ran, `2` usage, `66` no project, `73`
  cannot write `--out` or the transcript never finished flushing, `75` not macOS, `77` refused
  (Track-B gate unsatisfied, off-tty, or credential-shaped argv/env), `78` misconfiguration
  (in-clone scratch root, unparsable profile name). A `FAIL` verdict still exits `0` so the
  operator can capture it with `--out`.
- `MACOS_EVIDENCE=ABSENT (unverified)` (rc 1) is a third state next to `FAIL`: a missing Mac run
  can never be laundered into a pass, and a bound-to-a-nonexistent-commit report is `STALE`,
  never green.
- A report whose `archive_rc` is non-zero must classify the failure: `NO_SCHEME` next to
  `showdestinations_rc=0` is a contradiction and is rejected; `SIGNING` keeps the signing clause
  open without blaming the scheme.
- **Citation rebind (documentation-only; no dated file was edited).** This route was cut at
  base `295690b` and has been rebased twice since (wave A, then waves B+C). Every line number
  quoted by the brief/analysis documents of this package still describes the **base** tree, so
  they are listed here with their current positions instead of being rewritten in place:

  | cited fact | base `295690b` | this branch |
  | --- | --- | --- |
  | `applyOriginalStageBoundaryIfNeeded` (the 3/6 clause body, "deliberately dormant") | `GameScene.swift:622-631` | `:825-856` (now the ledger seam; the false comment is gone, the frozen table is `evidence/l0-before-d1.txt`) |
  | lives x 1000 award / borrowed life cap | `GameScene.swift:627` / `:628` | moved into `StageBoundaryLedger.outcome` |
  | points ceiling literal `999_999` | `GameScene.swift:662` | `:910` (still a literal; read from the source by the verifier) |
  | screen-exit trigger `x > 510` | `GameScene.swift:610` | `:794` (now `GameConstants.screenExitX` at the emit site) |
  | `includedLevels` 125-level set | `GameScene.swift:53` | `:99` |
  | pickup refills as bare `10` / `99` | `GameScene.swift:526` / `:533` | `:687-708`, now `GameState.startingGrenades` / `startingAmmo` |
  | only `setExoskeleton(false)` (restart) | `GameScene.swift:963` | `:1245`, plus the new boundary clear at `:852` and the activation edge at `:367` |
  | `toggleExoskeleton` / `setExoskeleton` | `Player.swift:243-246` / `:248-250` | `:274-278` / `:280-284` |
  | `startingAmmo/Grenades/Lives = 99/10/9` | `GameState.swift:81-83` | unchanged, `:81-83` |
  | probe size | `macos-probe.sh` 210 lines | 789 lines |
  | codesign-flags observation comment | `macos-probe.sh:119-123` | `:375-377` (section B) |
  | archive step (was optional) | `macos-probe.sh:132-142` | `:388-403` (section B2, mandatory) |

  `ORIGINAL_MECHANICS.md` is byte-identical to the base (verified), so every `OM:` citation in
  this package still resolves unchanged. The verification the drift note promised is re-asserted
  on every run: the unmodified `release_layer_check.py` still measures the release layer of the
  extended probe (red only on the declared cutover member, `evidence/cutover.md`).

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
