# Tasks — wave D (single write owner, phases ordered by owner ruling 3)

## Phase D-2 (start now; does not depend on wave A)
1. [x] `evidence/stage_boundary_check.py` L0 characterization: current 3/6 clause table pinned
      (green now, must FAIL when D-1 changes behavior — that's its role), per-component controls.
2. [x] Probe extension: Track A steps C-10…C-16 per `analysis-integration_architect.md` §2 —
      mandatory archive + `.xcarchive` inspection (plist versions, codesign -vv on archived bin,
      entitlements read), 5-valued verdicts as `key=value`, exits 77/78, Darwin guard preserved,
      M-8 flush barrier (`report_flush_verified` line-count), M-9 out-of-tree SYMROOT/OBJROOT
      contract, all old tokens/guards load-bearing preserved (merged checker rc invariance).
3. [x] `engineering/contracts/schemas/macos-probe-report-v1.schema.json` + handout template dir
      layout (`analysis-integration_architect.md` §3; §10 architect handout shape).
4. [x] `evidence/macos_handout_check.py`: schema validate, 10 consistency rules, binding checks
      (head/blob/artifact), ABSENT→unverified, STALE-not-green, contradictory synthetic handouts
      flip red, commit-then-receipts order encoded; runs merged `release_layer_check.py` as
      subprocess asserting rc invariance EXCEPT after-D-1 cutover set is not yet triggered (D-2
      tree has no hardened edits yet → merged checker must still be rc 0).
5. [x] Agent/human boundary: Track B requires WITH_SIGNING=1 && EXOLON_HUMAN_SIGNING_RUN=1 &&
      interactive tty confirm; off-tty exit 77; forbidden-argv/env abort scan (list from
      analysis §5) BEFORE exec; no credential code path; Team ID/cert hashed into handout.
6. [x] Local validation on Linux: `bash -n`, probe dry-run path where possible,
      `stage_boundary_check.py` + `macos_handout_check.py` green with controls flipping.

## Phase D-1 (ONLY after wave A merges into main; rebase this branch first)
7. [x] Rebase onto new main; run wave-A `gameplay_log_check.py` + merged release checker to
      confirm base state; record any cutover reds expected.
8. [x] Ledger sequence (data-driven components): bravery 10 000 activation-latch (+
      `tookExoskeletonInStage` sampled on changing-room/exo activation; falsifiable OM:142-vs-118
      test), timed tick-ladder `phase=min(4,(tick−stageStartTick)/PHASE_TICKS)` ladder
      [7000,5000,3000,1000,0], `PHASE_TICKS=1800` with owner-deviation comment, lives×1000 pre-+1,
      `maxLives=9` explicit constant (replace borrowed cap; also pickups literals :526/:533 →
      shared constants), exo clear at boundary, clamp identity case.
9. [x] Debug warp: `EXOLON_DEBUG_WARP=LxxSyy`, `#if !DEBUG`, routes through `transition(to:)`,
      stderr echo + event after sink exists; unreachable when flag unset.
10. [x] pbxproj: `ENABLE_HARDENED_RUNTIME = YES` both target blocks; `Exolon.entitlements`
      (minimal: no get-task-allow in Release); `CODE_SIGN_ENTITLEMENTS` both configs; scheme
      untouched. Document expected cutover reds in `evidence/cutover.md`.
11. [x] Stream predicates: stage_points component identity (matches amended wave-A predicate
      wording), suppression witness intact, timed phase recomputed from ts_us relative-delta.
12. [x] `stage_boundary_check.py` extended to L1 pure-ledger table + mutation controls per
      component; all change-spec names exist and green; `grok_verify --mode pr` recorded last.
13. [x] `decisions.md`: timed-ladder owner deviation + cutover precedent entries (3 sentences max).
14. [ ] Reviews/PR by controller; NO git by writer.

## Deferred (explicit, not silent)
- Track B execution (human, clean machine, consumes handout).
- Interactive bonus cursor minigame; OM:147 stage-start coords; `stageExitMarkers` consumption;
  VERSION/README protected-path change.

## Phase D-2 result (2026-09-24, write owner)

* `evidence/macos_handout_check.py` - all nine change-spec names green on this tree, every
  control flipping: `probe_contract_green`, `flush_barrier`, `build_roots_out_of_tree`,
  `handout_controls_flip`, `absent_is_unverified`, `agent_boundary`, `no_track_b_claim`,
  `cutover_set_exact`, `verdicts_machine_readable`.
* `evidence/stage_boundary_check.py` - `l0_characterization_pinned` + `single_funnel` green;
  the six ledger-backed names exist and fail with `pending wave-A merge` (the runner treats a
  stub that passes as a failure, so a silent tautology cannot hide).
* Probe: 46 merged emit-keys preserved, 80 added; `bash -n` clean; Linux still exits 75; the
  unmodified merged `release_layer_check.py` still reports `RELEASE_LAYER_READY` with 29/29
  controls on this tree.
* `python3 scripts/grok_verify.py --mode pr --no-record` = PASS (recorded form belongs to the
  final controller gate, not to this phase).

## Deviations (bounded rulings, recorded here rather than silently applied)

1. **§6.3 rule 4 is enforced as "no positive Track-B claim", not "all Track-B fields are
   NOT_ATTEMPTED".** Steps C-12/C-13/C-14 of the same contract are Track A steps that must
   report `Signature=adhoc`, an absent `Timestamp=` and a rejected `spctl`; a literal reading
   of rule 4 would reject the probe's own Track A output. Enforced instead: notarization and
   stapling stay `NOT_ATTEMPTED`, and `notary_submit`/`signing_identity_class`/
   `secure_timestamp`/`spctl_assess` may never carry a positive Track B value in a Track A
   report (FORBID-001 unchanged in intent).
2. **The M-8 control is a deterministic lagging sink, not a natural race.** At the probe's own
   output volume the truncation did not reproduce on this host's bash 5.2 (0/20 runs), while
   M-8 measured 7/10 on the reference form. The shipped barrier is therefore exercised against
   a writer that is provably behind (`report_flush_verified=yes`, rc 0) and against a
   permanently short file (`no`, rc 73): the invariant "an incomplete --out cannot stand behind
   rc=0" is what is measured, and it is measured on the shipped bytes.
3. **The barrier writes its three verdict lines straight into the report file, bypassing the
   tee pipe**, so its own verdict cannot be the thing that gets truncated. `report_lines_expected
   == report_lines_written == wc -l` of the committed transcript is the consumer's check (R2).
4. **`EXOLON_NOTARY_PROFILE_RE` requires a leading alphanumeric** (`^[A-Za-z0-9._]`), so a
   flag cannot be passed off as a profile name; §5.2.3 asked for a name-only value, and a
   character class alone still accepted `--apple-id`.
5. **The ban list inside the probe is written with character classes** (`pass[-_]?word`,
   `p1[2]`, `-{5}BEGIN`), because §5.2.3 forbids the contiguous literals anywhere in the file -
   including in the scanner that has to detect them. `agent_boundary` checks both directions.
6. **E16 was added to the probe's manual list** (15 -> 16 items, and the section-F text now says
   E1-E16). It is the play observation of the stage sequence named in the test plan; it can only
   be answered fully on a D-1 build.
7. **PII and private-key greps are enforced over the files this phase adds** (`evidence_hygiene`:
   the probe, the schema, the handout README and the two checkers), with the banned patterns
   assembled from adjacent string literals so the checker does not trip its own scan. The
   analyst reports already in this package's `evidence/` predate the rule, are read-only input
   to it, and are deliberately out of scope.
8. **The full norm sequence is armed at the product seam, not by changing the ledger's default.**
   Wave A's merged auditor validates only the component ids its `COMPONENT_RULES` knows
   (`lives_x1000`); its own comment invites a later wave to append that table, which would mean
   editing another route's merged package. So `StageBoundaryLedger(awardSequence:)` keeps wave A's
   single-clause default (wave A's harness and auditor replay exactly the stream they were
   certified on) and `GameScene` names `GameplayStageComponentSequence.waveD` at the boundary
   call. `waveA` therefore remains a real, reachable configuration rather than dead code — which
   is what makes "the sequence is data" more than a phrase.
9. **FORBID-002's declared cutover set is a superset of the reachable one.** Measured on this
   tree: `hardened_runtime_key_count` reddens; `hardened_deferral_recorded` cannot (it reads PR
   #3's immutable plan text), and PR #3's control `hardened_key_mutation_detected` becomes
   unsatisfiable for the structural reason in `evidence/cutover.md`. Enforced instead: no red and
   no lost control outside the declared sets, each declared member proven live through the merged
   checker's own in-memory revert. The spec text was not silently "fixed"; this is the record.
10. **`waveA` context carries no clock observation, so the ladder pays zero rather than guessing.**
    `StageBoundaryContext.stageElapsedSteps` is optional and `nil` means "unobserved". Without it a
    default context would silently compute phase 0 = 7 000 points and wave A's certified numbers
    would change under a wave-D signature change.
11. **Two contract code tables grew by appending** (`stage_component_id` 1→3 with the two new ids,
    `exoskeleton_cause` 3→4 with `stage_boundary`), per the schema's own `x-extension-rule`. The
    boundary clear needed a cause: with `.reset` only, a stage clear would be indistinguishable
    from a restart on the wire, and `:145` is one of the six clauses being claimed.
12. **`requirements.md` records the line-number drift and the exit-code/verdict semantics** that
    the extended probe introduced, so the next audit pass does not re-open them as citation
    defects (dated evidence was not touched).

## D-1 readiness (what phase D-1 must do, and what is already paid for)

1. `git fetch --all --prune`, rebase this branch onto the new main, then confirm the base
   state before writing anything: merged `release_layer_check.py` (expect the two
   hardened-runtime cutover reds and nothing else) and wave A's `gameplay_log_check.py`.
2. Run both checkers with `--phase D1`. Until the ledger exists they fail by design:
   `stage_boundary_check.py` reports `PENDING_OK` for the six ledger names, and
   `macos_handout_check.py` refuses a D-1 claim on a tree whose merged checker is green.
3. `StageBoundaryLedger.swift` must expose, or wave D must amend wave A to expose
   (analysis-architect.md §4): `completedZone`, `lives`, `points`, `tookExoskeletonInStage`,
   `stageElapsedTicks` in; `livesBonus/bravery/timed/timedPhase/earned/livesBefore/livesAfter/
   refill/clearExoskeleton` out, plus `noteExoskeletonActivated(atTick:)`,
   `noteStageStarted(atTick:)`, `beginPlaythrough(atTick:)`. Field ownership is the only place
   the rebase can fail; file the mismatch as a blocking amendment, never as a parallel type.
4. Replace each stub body with the L1 table and keep the names identical - the change-spec
   evidence refs are name-bound (`spec.py` resolves `path::symbol` at gate time).
5. Retire L0, do not fix it: snapshot `stage_boundary_check.py --table` into
   `evidence/l0-before-d1.txt` before the sequence changes, because after D-1 that
   characterization must go red (architect §7). `single_funnel` stays and must stay green.
6. `ladder_is_declared_deviation` needs `PHASE_TICKS = 1_800` in `GameConstants.swift` with the
   owner-deviation comment; the deviation comment is what the check reads, not the number.
7. pbxproj/entitlements (task 10) then re-check `cutover_set_exact --phase D1`: the declared
   set is {hardened_runtime_key_count, hardened_deferral_recorded}; `hardened_deferral_recorded`
   is proven live through the merged checker's own `undo_records` path, because the 2e7698 plan
   text is immutable and cannot itself be rewritten to make that key red.
8. `engineering/contracts/schemas/` merges next to the other waves' `contracts/` subdirs
   (main already has `asyncapi/`, `openapi/`; wave C adds `level-content-v1.json`): no filename
   collision, but the rebase must not drop `macos-probe-report-v1.schema.json`, because the
   change-spec `contracts.json_schema` ref and `agent_boundary` both require the file to exist.

## Phase D-1 result (2026-09-25, same write owner; rebased D-2 commit e0169e5)

Rebased onto wave A (`origin/main` 17a742a); only `decisions.md` conflicted and it was resolved
by keeping both entries. Wave A's own auditor stays green on the changed product:
`gameplay_log_check.py` = 28/28, including `p1_8_fixed_passes_and_revert_fails` (predicate B on
the compiled ledger) — wave A's file was **not** edited to get there.

* `StageBoundaryLedger.swift` now carries the whole sequence as data: `waveD = [lives_x1000,
  bravery_no_exoskeleton, timed_phase_ladder]`, a `StageBoundaryContext` (stage-relative step delta
  + the activation latch), `noteExoskeletonActivated/StageStarted`, `clearsExoskeleton`,
  `timedPhase`. `GameConstants` gained `maxLives = 9`, `braveryBonus = 10_000`,
  `phaseTicks = 1_800` (owner-deviation comment) and `timedBonusLadder`; `updatePickups` and the
  boundary refill share `GameState.startingAmmo/Grenades`; the bare 999 999 clamp stays a literal
  in `awardPoints` but is now read from the source by the verifier rather than restated.
* Wave A's constructed default sequence stays `waveA`, and the **product seam names `waveD`
  explicitly**: wave A's merged auditor knows only `lives_x1000` and its own comment says a new
  component must be appended to its rule table — which would have meant editing another route's
  package. Arming at the call site keeps both true. Recorded as Deviation 8.
* `EXOLON_DEBUG_WARP=LxxSyy`: `#if DEBUG`-compiled end to end, bounded by `includedLevels`,
  stderr echo, and it goes through `transition(to:)`, so P1-9's accumulator reset and the
  `isStageStart` spawn rule are the production ones. `SWIFT_ACTIVE_COMPILATION_CONDITIONS =
  DEBUG` is declared once, in the project's Debug configuration: it cannot go into the target
  blocks, which must stay byte-equal (`target_cfg_symmetric`).
* pbxproj: `ENABLE_HARDENED_RUNTIME = YES` + `CODE_SIGN_ENTITLEMENTS` in both target configs,
  `Exolon/Resources/Exolon.entitlements` tracked and deliberately an **empty** key set (no
  debugger entitlement; the hardened runtime is switched by its own setting). Identity, team and
  any signing material are untouched: `CODE_SIGN_IDENTITY = "-"`, `Manual`, `DEVELOPMENT_TEAM = ""`.
* Modelled and executed agree: `evidence/ledger-xcheck/run.sh` compiles the shipped
  Foundation-only product files (wave A's file list and CoreGraphics shim) and prints the `waveD`
  table from the real `StageBoundaryLedger`; `executed_ledger_matches_model` diffs 100 awarded rows
  plus the once-key, latch, cap and wave-A-shim assertions against the committed
  `ledger-xcheck-executed.txt`, with a control that reddens if the cadence drifts. The table that
  the Swift type produces is therefore the table the Python verifier models.
* Cutover measured, not quoted: the merged checker's diff is exactly
  `red_ac = {hardened_runtime_key_count}` plus the control `hardened_key_mutation_detected`
  structurally unable to pass on a repaid tree. Both, and the reason `hardened_deferral_recorded`
  cannot redden at all, are in `evidence/cutover.md`.

## macOS-side validation is permanently out of reach for this repository

The owner has no Apple hardware and no Developer ID ("нет у меня маков", 2026-09-25). Nothing in
phase D-1 — nor in any future phase of this project — will be confirmed on a Mac: no archive read,
no `codesign`/`spctl`/`notarytool`/`stapler` observation, no play-through of E1…E16. Mitigations
actually in force, and the only ones this repository has:

1. wave A's executed-Swift Linux contour (real product types, `swiftc`, 28/28 with flipping
   controls) plus `swiftc -frontend -parse` as a declared **syntax** gate, never a "compiles" claim;
2. `stage_boundary_check.py` — L0 characterization, L1 ledger table, per-component mutation
   controls, and the wire identity against wave A's real lane names and the frozen schema;
3. `macos_handout_check.py` — the probe's text contract, the M-8/M-9 fixes measured on shipped
   bytes, the ten handout rules with contradictory fixtures, and `MACOS_EVIDENCE=ABSENT
   (unverified)` as the steady state rather than a to-do;
4. audit issues #14/#15 stay honest: #14 closes with the owner-ruled ladder (deviation recorded,
   cursor minigame out of scope forever in this change), #15's signing/notarization clause stays
   open **because of the hardware, not because of unfinished work**.
