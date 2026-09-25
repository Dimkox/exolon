# Release plan — Complete wave-D specification and release audit findings in the Exolon game: P1-10 (end-of-stage bonuses are incomplete versus ORIGINAL_MECHANICS - bravery bonus 10000 and timed bonus 0/1000/3000/5000/7000 at stage boundaries 24/49/74/99/124, plus-one-life capped at 9, exoskeleton cleared and ammo refilled 99/10 - restore the full stage-end sequence in coordination with the wave-A StageBoundaryLedger) and the remaining P1-11 scope (extend the committed release-layer verifier and engineering/runbooks/macos-probe.sh so signing, notarization and archive are checked end-to-end on a clean macOS machine; Linux-decidable parts committed, the macOS run documented as an external handout).

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Rollback: [`rollback.md`](rollback.md).
> Consequences of the product edits on merged verification: [`evidence/cutover.md`](evidence/cutover.md).

## Merge position

Last in the wave series. This branch is rebased onto `origin/main` after waves A, B and C merged
(`817bf52`), so the stage sequence sits on the `StageBoundaryLedger` it extends, and the
release-layer repayment sits on the release verifier it repays. Nothing here is a precondition for
another open wave.

## Deployment

Pull-request only, per the repository contract: no direct push to a protected branch, no tag, no
GitHub Release, no deploy, no external mutation. **This change ships no artifact.** It changes game
logic, release *settings* and verification tools; it never signs, archives, notarizes or publishes.
The `.xcarchive`, any container and any release object stay out of scope for this repository
entirely — `evidence/cutover.md` §6.

So "released" here means: the tree gains the completed stage-end sequence, the hardened-runtime
settings and two Linux verifiers. It does not mean a publishable build exists, and no wording in
this package may imply one.

## Feature flags / staged rollout

Nothing to stage, and no runtime flag gates gameplay:

| switch | default | who can flip it | effect |
| --- | --- | --- | --- |
| `EXOLON_DEBUG_WARP=LxxSyy` | unset | nobody in a shipped build: the whole feature lives inside `#if DEBUG` and is **absent from a Release binary by construction** | jumps to one of the 125 shipped level names through the real `transition(to:)`, so a stage-end observation (probe item E16) does not cost an 11-minute walk |
| `EXOLON_EVENT_LOG` | off in shipped builds (wave A's kill switch) | operator; unrelated to this change | the award path never reads the sink: the timed ladder consumes `FixedTickDriver.stepCount`, not `events.tick`, so an uninstrumented run awards identically |
| `WITH_SIGNING=1` + `EXOLON_HUMAN_SIGNING_RUN=1` + tty | unset | human only, all three at once | requests Track B in the probe; anything else refuses with `exit 77` before any external command runs |
| `EXOLON_PROBE_SCRATCH` | `$TMPDIR/exolon-probe-<UTC>` | operator | out-of-tree `SYMROOT`/`OBJROOT`/archive paths; a value inside the clone refuses with `exit 78` (defect M-9) |

The full award sequence is not flag-gated: `GameplayStageComponentSequence.waveD` is armed at the
product seam while the ledger's constructed default stays `waveA`, so wave A's certified harness and
auditor replay exactly their stream (deviation 8). `waveA` therefore remains a real, reachable
configuration rather than dead code.

## Metrics and alerts

Steady-state expectations; every one is an assertion in a committed checker, not a hope:

* `macos_handout_check.py --report` → `MACOS_EVIDENCE=ABSENT (unverified)`, **rc 1, permanently**.
  ABSENT is distinct from FAIL and from STALE. This is the repository's state, not a queue.
* Merged `release_layer_check.py` on this branch → `red_ac=1 bad_controls=1`, namely exactly
  `hardened_runtime_key_count` red and exactly `hardened_key_mutation_detected` retired. Any other
  red or any other lost control is a regression; `cutover_set_exact` enforces the four clauses of
  FORBID-002 as the typed spec words them.
* Probe back-compat: merged emit-keys **46 → 127, zero lost** (`probe_contract_green`);
  `runbook_stale_gap_claims=0`, `runbook_archive_step_present=1`, Linux still `exit 75`.
* Verification suite: `stage_boundary_check.py` 10/10 and `macos_handout_check.py` 10/10 with every
  control flipping, wave A `gameplay_log_check.py` 28/28, wave C `wave_c_check.py` 9/9; wave B's
  semantic probes pass and its added-lines size floor reports its documented by-design mismatch
  (deviation 14).
* **Clone hygiene for anyone re-running a sibling meter:** `wave_b_check.py` resolves its added-lines
  base as `git merge-base HEAD origin/main` and falls back to the much wider `295690b` when
  `origin/main` is absent — so a plain `git clone` of a local path, or a bundle without
  `refs/remotes/origin/main`, silently scans a different diff and can produce a false result for
  reasons unrelated to the code. Run those meters in a tree that carries the remote ref (a real
  clone from the URL, or `cp -a` of a working copy). Wave B's package is not edited here; the
  finding is queued for wave E.

## Go/no-go criteria

Go requires all four, on the exact head SHA to be merged:

1. **Security review part 1 PASS** — the structural agent/human boundary: Track B unreachable
   without the double env gate plus the typed tty attestation; credential-shaped argv/env aborts
   rather than redacting; no code path that accepts or stores a credential; identity material only
   as hashes; no secret and no operator PII in anything this change adds.
2. **Security review part 2** — the repayment's own surface: the entitlements file grants nothing,
   `CODE_SIGN_IDENTITY`/`CODE_SIGN_STYLE`/`DEVELOPMENT_TEAM` untouched,
   `SWIFT_ACTIVE_COMPILATION_CONDITIONS` absent from Release, and the probe's notary call limited
   to a profile **name**.
3. **Release review re-check on the amended documents** — this file and `rollback.md` matching what
   the checkers measure, `evidence/cutover.md` quoting FORBID-002 verbatim, and the macOS posture
   stated as permanently unrunnable rather than pending.
4. **Machine gates green at that SHA**, with the phase named explicitly — a tree whose hardened
   lines were removed would auto-detect as D-2 and evaluate the cutover claim vacuously (review
   finding 7; recorded in `evidence/cutover.md` §2 "Limits"), so the release command set is:

   ```bash
   python3 scripts/grok_verify.py --mode pr                # PASS, then record the receipt
   python3 …/8341b7/evidence/macos_handout_check.py   --root . --phase D1   # 10/10
   python3 …/8341b7/evidence/stage_boundary_check.py  --root . --phase D1   # 10/10
   bash    …/8341b7/evidence/ledger-xcheck/run.sh                          # table identical
   python3 …/32f59c/evidence/gameplay_log_check.py --artifacts <contour run>  # 28/28
   python3 …/f2d90a/evidence/wave_c_check.py                               # 9/9
   python3 …/2e7698/evidence/release_layer_check.py --root .   # red on the declared set only
   git diff --check && git status --porcelain=v1                           # clean
   ```

   Run the sibling meters in a tree that carries `refs/remotes/origin/main` (see Metrics above).

No-go made explicit: this change does **not** close P1-11's signing/notarization clause, and no
summary of it may read as release-ready. Issue #15 stays open because there is no Apple hardware and
no Developer ID; issue #14 closes with the owner-ruled tick ladder, whose divergence from the
cursor norm is recorded in `GameConstants.phaseTicks` and policed by
`stage_boundary_check.py::ladder_is_declared_deviation`.
