# Rollback plan — Complete wave-D specification and release audit findings in the Exolon game: P1-10 (end-of-stage bonuses are incomplete versus ORIGINAL_MECHANICS - bravery bonus 10000 and timed bonus 0/1000/3000/5000/7000 at stage boundaries 24/49/74/99/124, plus-one-life capped at 9, exoskeleton cleared and ammo refilled 99/10 - restore the full stage-end sequence in coordination with the wave-A StageBoundaryLedger) and the remaining P1-11 scope (extend the committed release-layer verifier and engineering/runbooks/macos-probe.sh so signing, notarization and archive are checked end-to-end on a clean macOS machine; Linux-decidable parts committed, the macOS run documented as an external handout).

> Change-spec rollback field: `strategy: forward_fix`, `maximum_steps: 1`. This plan honours that:
> one operation, no data step.

## Trigger conditions

Any of these is reason to take the change back; none of them needs a decision from a human about
state, because there is no state to reconcile:

* A stage boundary awards the wrong total, or pays bravery/timed where `ORIGINAL_MECHANICS.md:140-146`
  says otherwise (the identity is asserted per boundary by `sequence_components_identity`, so a
  regression is detectable before a player sees it).
* Wave A's idempotency or witness behaviour breaks at a boundary — a silent repeat, or a second
  award in one playthrough (predicate B, `p1_8_fixed_passes_and_revert_fails`).
* The release-layer repayment turns out to break an Apple build (a first real archive somewhere in
  the future failing on the hardened runtime or on the entitlements path).
* A merged checker reddens on any key outside the set declared in `evidence/cutover.md`, or a second
  control stops flipping.

## Application rollback

**One step: `git revert` the wave-D commits** (the D-1 product commit, and the D-2 tooling commit if
the verifiers are wanted too). No configuration, no migration, no restart ordering, no cache flush.

Why one step is genuinely sufficient:

* **The ledger change is additive.** `StageBoundaryLedger` kept wave A's `outcome(zone:lives:
  startingLives:startingAmmo:startingGrenades:)` signature as a delegating shim and wave A's
  constructed `waveA` default sequence; the D-1 components, context and helpers are new members.
  Reverting removes the `waveD` sequence and the seam argument and leaves wave A's file working for
  wave A's callers — no other wave calls anything this change introduced.
* **No persisted state exists or changes.** `GameCheckpoint` (`levelName`, `ammo`, `grenades`,
  `points`, `lives`) is untouched by this change, and no ledger/tick/latch field is persisted — the
  exoskeleton latch and the stage clock are in-memory only. A checkpoint written by a wave-D build
  loads in a rolled-back build exactly as any other checkpoint: same keys, same shape. Nothing to
  migrate, nothing to drain, nothing to invalidate.
* **The debug warp needs no flag-off.** It is inside `#if DEBUG` end to end and is absent from a
  Release binary by construction, so there is no shipped surface to disable; `EXOLON_DEBUG_WARP` in
  someone's environment is inert after the revert. It is orthogonal to `EXOLON_EVENT_LOG` (wave A's
  kill switch), which keeps working either way — the award path reads `FixedTickDriver.stepCount`,
  never the sink, so rolling back cannot desync gameplay from logging or vice versa.
* **The release settings revert with the code.** Both `ENABLE_HARDENED_RUNTIME` lines and both
  `CODE_SIGN_ENTITLEMENTS` lines are inside the two target blocks; `Exolon/Exolon.entitlements` is a
  new file, not referenced by any build phase. Reverting removes all five and the project returns to
  PR #3's deferred-but-recorded posture.

## Data recovery / forward-fix

No data. There is no migration, no backfill, no queue, no cache key, no external system, no stored
artifact, and no persisted schema in this change; the transactional state of the game is the same
four-value checkpoint it was. Recovery from a partially-applied merge is the same operation as the
rollback itself: `git revert`, because the change is pure source.

Forward-fix path if the ladder cadence (or the bravery reading) is later judged wrong rather than
merely tunable: `GameConstants.phaseTicks` is one named constant, `timedBonusLadder` one array, and
the sequence is a list armed at the seam — re-tuning or re-targeting the cadence, or replacing the
ladder with an interactive cursor, is a change to that constant and to `waveD`, not to the
boundary, the once-keys or the witness plumbing. That is the reason the ladder was landed as data.

## Verification after rollback

Expect, in this order, on the reverted tree:

* **Wave-D checks go red, deliberately:** `stage_boundary_check.py` fails on
  `sequence_components_identity`, `lives_and_refill_semantics`, `bravery_latch_distinguishes`,
  `timed_ladder_deterministic`, `warp_debug_only` and `ladder_is_declared_deviation` (the ledger
  rules, the constants and the warp are gone); `macos_handout_check.py` fails 4 of 11 (measured; the named two being
  `entitlements_and_hardening_shape` and `cutover_set_exact`'s D-1 posture, plus two
  transitive guards that read the same settings) — and `ledger-xcheck/run.sh` stops
  compiling once the D-1 ledger members are gone. The stage_boundary list above names six
  of the eight measured reds: these lists understate, never overstate. A rollback that
  turned any of them green would mean they never measured
  the fix.
* **`l0_characterization_pinned` stays GREEN after the rollback, by design.** It is a historical
  characterization read from base `295690b` via `git show`, with `evidence/l0-before-d1.txt` as its
  frozen table — that is what lets it survive its own subject being fixed, and it is the deliberate
  difference from the D-2 draft, which read the working tree. (The review's expectation "L0 must be
  red after rollback" belongs to the L1 table above, not to L0.)
* **The merged release verifier returns to PR #3's posture:** `rc=0`, `RELEASE_LAYER_READY`, 29/29
  controls green again — `hardened_runtime_key_count` back to its deferred expectation of 0 and
  `hardened_key_mutation_detected` flippable once more, which is the clearest evidence that the
  cutover described in `evidence/cutover.md` was caused by exactly this change.

  Both halves of that sentence were measured before being written, on the current tree with wave D's
  five project lines removed in memory (`ENABLE_HARDENED_RUNTIME` ×2, `CODE_SIGN_ENTITLEMENTS` ×2
  plus the file itself): ACs red = `[]`, and control 8's one-sided install is asymmetric again. The
  same experiment is reproducible without a revert:

  ```bash
  python3 - <<'EOF'
  import importlib.util, pathlib, re
  root = pathlib.Path(".").resolve()
  mp = root / "engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698" \
             / "evidence/release_layer_check.py"
  spec = importlib.util.spec_from_file_location("m", mp); m = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(m)
  ctx = m.load_inputs(root)
  t = re.sub(r"^\t{4}(ENABLE_HARDENED_RUNTIME = YES|CODE_SIGN_ENTITLEMENTS = "
             r"Exolon/Exolon\.entitlements);\n", "", ctx["pbx"], flags=re.M)
  got, det = m.measure(dict(ctx, pbx=t))
  print("red ACs:", sorted(k for k, v in m.EXPECTED.items() if got.get(k) != v))
  add = "\n\t\t\t\tENABLE_HARDENED_RUNTIME = YES;"
  one = t.replace("\t\t\t\tCODE_SIGN_STYLE = Manual;", "\t\t\t\tCODE_SIGN_STYLE = Manual;" + add, 1)
  both = t.replace("\t\t\t\tCODE_SIGN_STYLE = Manual;", "\t\t\t\tCODE_SIGN_STYLE = Manual;" + add)
  ph, pb = m.detect_pbxproj(one), m.detect_pbxproj(both)
  print("control 8 flippable:", ph["target_cfg_symmetric"] == 0 and ph["hardened_symmetric"] == 0
        and pb["target_cfg_symmetric"] == 1 and pb["hardened_symmetric"] == 1)
  EOF
  ```
* **Siblings unaffected:** wave A's contour still `28/28` (its `waveA` default sequence and its
  shim signature were never replaced), wave C `9/9` (the content directory was untouched after the
  entitlements file moved to `Exolon/`), wave B's semantic probes as before.
* **Gameplay smoke:** the five stage ends award `lives × 1000` only, the suit is no longer cleared at
  a boundary, and repeat triggers keep emitting `bonus.stage_boundary_suppressed` — i.e. the tree
  behaves exactly as it did before wave D, which is the definition of a clean revert, not a defect.
