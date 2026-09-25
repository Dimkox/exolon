# Review: release_reviewer — release readiness of the wave-D branch

- Change: `20260924-complete-wave-d-specification-and-release-audit-8341b7`
- Tree reviewed: `codex/wave-d-spec-release-20260924` @ `84b7813f0dc9c8f25c93967908df2410dc385da2`
  (= PR #17 head, `headRefOid` verified equal to the reviewed SHA; base = GitHub `main`
  `817bf5253ba9062960b27f60ee2e6b04b2a023d9`)
- Mode: read-only. The only write is this file. **Every number below was produced by my own runs**
  in a disposable `git clone --no-hardlinks` at `/home/pall/projects/.review-wave-d/clone`
  (checked out at `84b7813`), never copied from checker output that I had not executed.
- Route (`route.json`): intent `release`, risk `high`, required evidence
  `verification` + `security_review` + `release_review`.

**Verdict: FAIL as submitted — documentation-only. No product, contract or verification defect was
found.** All five review items pass on substance; three release-facing artifacts are unfilled or
stale, and two of them are exactly the artifacts a human merge-approver reads. Detail and the exact
repair list are in §6 and §7.

---

## 1. Stage-end sequence vs `ORIGINAL_MECHANICS.md:138-148` — clause by clause

Norm file is byte-identical to the route base (my `git diff 295690b..HEAD -- ORIGINAL_MECHANICS.md`
= empty), so every `OM:` citation in the package still resolves. Line numbers below are on the
reviewed head.

| OM | Clause | Implementation (file:line) | Status | Linux enforcement |
| --- | --- | --- | --- | --- |
| :140 | Reaching the stage-end trigger opens the bonus sequence | `GameScene.swift:793-799` (`checkScreenExit` → `applyOriginalStageBoundaryIfNeeded`); zone set `StageBoundaryLedger.swift:154` (`[24, 49, 74, 99, 124]`), guard `:225`; product arms the full sequence at `GameScene.swift:832` (`awardSequence: …waveD`), sequence data at `StageBoundaryLedger.swift:40-41` | **DONE** | `sequence_components_identity` |
| :141 | 1000 points per **remaining** life | `StageBoundaryLedger.swift:48-49` (`lives * 1_000`, `lives` = the value passed in at `GameScene.swift:827`); applied at `GameScene.swift:842` **before** `:844` writes `award.livesAfter` | **DONE, order correct** | `sequence_components_identity`, `single_funnel` |
| :142 | 10 000 bravery if no exoskeleton was **taken** | `StageBoundaryLedger.swift:50-51` + `GameConstants.swift:98` (`braveryBonus = 10_000`); latch is an *event*: `StageBoundaryLedger.swift:180-187` (`noteExoskeletonActivated`), recorded only at the single activation site `GameScene.swift:366-368`; cleared per stage at `:189-193` / `GameScene.swift:885` | **DONE as an activation latch — disclosed ruling** | `bravery_latch_distinguishes` |
| :143 | Timed bonus 0/1000/3000/5000/7000 by selected phase | `StageBoundaryLedger.swift:52-54` + `:62-64` (`min(4, elapsed / phaseTicks)`), `GameConstants.swift:113` (`phaseTicks = 1_800`), `:117` (`[7_000, 5_000, 3_000, 1_000, 0]`) | **DONE as an owner-approved deterministic ladder, NOT the cursor minigame** — `GameConstants.swift:100-112` carries "**OWNER-APPROVED DEVIATION — NOT CANONICAL** … UNCONFIRMED vs original" | `timed_ladder_deterministic`, `ladder_is_declared_deviation` (FORBID-003) |
| :144 | Add one life, capped at 9 | `StageBoundaryLedger.swift:248` (`min(maxLives, lives + 1)`); `GameConstants.swift:95` (`maxLives = 9`, explicit, no longer borrowed from `startingLives`); passed at `GameScene.swift:828` | **DONE** | `lives_and_refill_semantics` |
| :145 | Clear exoskeleton | `StageBoundaryLedger.swift:252` (`clearsExoskeleton: true`) → `GameScene.swift:848-853` `player.setExoskeleton(false, cause: .stageBoundary)` → `Player.swift:280-284` (witnessed transition); own cause code `GameplayEventSink.swift:1041-1049` (table grew 3→4), schema `gameplay-event-v1.schema.json:182` | **DONE with its own cause code** | Deviation 11 + `component_stream_identity` |
| :146 | Restore ammo=99, grenades=10 | `StageBoundaryLedger.swift:249-251` → `GameScene.swift:845-846`, shared `GameState.swift:81-83` (`99`/`10`/`9`); the same constants now back the pickups at `GameScene.swift:696` and `:706` (bare literals gone) | **DONE, shared constants incl. pickups** | `lives_and_refill_semantics` |
| :147 | Stage starting positions | Not this change: `brief.md` "Explicitly deferred" and `tasks.md` "Deferred" both name OM:147; spawn comes from `currentLevel.spawnCenter` (`GameScene.swift:887-890`) | **DEFERRED (recorded, not silent)** | — |
| :148 | Zone 124 shows FULL COMBAT ABILITY, returns to beginning | Pre-existing and unchanged by wave D: `GameScene.swift:1004`, `:1014`; wave A's once-key (`StageBoundaryLedger.swift:113-121`, enforced at `:231-232`) is what makes the loop non-farmable | **OUT OF SCOPE, still true** | wave A's `p1_8_fixed_passes_and_revert_fails` |

Identity, clamp and the single funnel: `points` is the sum of components by construction
(`StageBoundaryLedger.swift:96`), emitted per component alongside the total
(`GameScene.swift:1336-1343`); the only scoring path is `awardPoints` (`GameScene.swift:907-917`,
10 call sites, INV-001), ceiling `min(999_999, …)` at `:910`.

My own runs on the head tree: `stage_boundary_check.py` → `SUMMARY checks=10 failed=0 phase=D1`,
rc=0. `ledger-xcheck/run.sh` (compiles the **shipped** Foundation-only product files with
`swiftc -O` and prints the real ledger's table) reproduced
`evidence/ledger-xcheck-executed.txt` **byte-identically** (`diff` → empty, rc=0), i.e. the
committed executed artifact is not stale after the B+C rebase.

**Falsification I ran myself** (the standing rule that a verification must have a control that
flips): mutating `GameConstants.braveryBonus` 10 000 → 11 000 in a scratch copy reddened
`executed_ledger_matches_model` (`executed bravery=10000 disagrees with the model 11000`, rc=1)
while `sequence_components_identity` stayed green — which proves the numbers are pinned by the
*executed* Swift, not by a Python restatement of them.

---

## 2. P1-11 scope accounting — done vs permanently blocked; PR wording; cutover red set

| Scope item | State | Evidence I produced |
| --- | --- | --- |
| Track A **probe contract** (extension committed) | **DONE (Linux-decidable)** — the probe grew 210 → 789 lines (`+633`), `bash -n` rc=0, Linux run exits **75** with the Darwin-guard FATAL, emit-keys **46 → 127, zero lost** (measured with the checker's own `emit_keys`, base `295690b` vs head) | my run + `probe_contract_green`, `verdicts_machine_readable` PASS |
| Cutover registry | **DONE** — `evidence/cutover.md` records the measured diff, the retired control and the liveness argument | my runs below |
| Handout contract `exolon.macos-probe-report/1` | **DONE** — schema committed (562 lines), 10 rules each with a reddening fixture, `ABSENT` distinct from `FAIL` | `handout_controls_flip`, `absent_is_unverified` PASS |
| Hardened runtime + entitlements + `CODE_SIGN_ENTITLEMENTS` | **DONE** — pbxproj delta is exactly 5 added lines (2×`ENABLE_HARDENED_RUNTIME`, 2×`CODE_SIGN_ENTITLEMENTS`, 1×`SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` in the project Debug block only); `Exolon/Exolon.entitlements` tracked, `plistlib` → **`[]`**, zero `get-task-allow` anywhere under `Exolon/` | my `grep`/`plistlib`/`git diff` counts: 2, 1, 2, `[]` |
| Track A **actual run** (C-00, C-10…C-16) | **PERMANENTLY BLOCKED** — no Apple hardware (owner, 2026-09-25); documented as structurally unrunnable, not deferred | `cutover.md` §6, `macos-handout/README.md:20-36` |
| Track B run (Developer ID sign + notarize, C-20…C-31) | **PERMANENTLY BLOCKED, twice** — no hardware and no identity/notary credentials, and the contract keeps those outside any agent's reach | `agent_boundary`, `no_track_b_claim` PASS |
| Issue states | **#14 OPEN** (closes on merge — legitimate: #14's body names exactly bravery + timed); **#15 OPEN and explicitly *not* closable here** | `gh issue view 14/15`; PR body "Do not close #15 from this PR" |

`MACOS_EVIDENCE` steady state, on the head tree:
`macos_handout_check.py --report` → `MACOS_EVIDENCE=ABSENT (unverified)`, **rc=1**. Confirmed.

**Merged `release_layer_check.py`, my own run on the clone (unmodified, `--root .`):**

```
rc=1   RESULT: NOT_READY (red_ac=1 bad_controls=1)
red AC key : hardened_runtime_key_count  expected=0 measured=2   (line 24, the only "RED")
control that stops flipping : hardened_key_mutation_detected    (the only "BAD" of 29)
hardened_deferral_recorded = 1 (green) · runbook_stale_gap_claims = 0 · runbook_archive_step_present = 1
all 28 other controls OK · mismatches: 1
```

That is **exactly** `{hardened_runtime_key_count}` + the one retired control per `cutover.md`
§2-§3, and nothing else moved. `macos_handout_check.py` → 10/10 PASS rc=0, including
`cutover_set_exact`; `--phase D2` correctly fails 2 controls (so the phase claim is not
self-serving). Second falsification: stripping both `ENABLE_HARDENED_RUNTIME` lines from a scratch
tree flipped `entitlements_and_hardening_shape=FAIL` (rc=1) — the repayment cannot silently
un-repay and keep the gate green.
Immutability holds independently: `git diff --name-only 817bf52..HEAD` touches **no** file under
any other `engineering/changes/**` package.

**PR body (read live from GitHub, PR #17) — overclaim check.** The macOS/Track-B half is honest
and, if anything, stricter than required: it states the cutover red set, states the retired control,
states "no Apple machines, no Developer ID", and says #15 must stay open. No artifact of this
change anywhere claims P1-11 closure, "notarization Accepted", or "release-ready" — my grep over the
package + PR body for those patterns returned only the *prohibitions* of them. Three wording
defects do remain, all in §6.

---

## 3. Merge-order dependency and the cross-wave meter story

`git merge-base HEAD origin/main` = `817bf52` = GitHub `main` = "Merge pull request #18 (wave C)".
So the branch is D-2 + D-1 + rebind sitting on A+B+C merged, and PR #17 is `MERGEABLE`. The
"branch on `817bf52`" precondition in the brief is satisfied by the rebind commit `84b7813`.

I ran all three foreign meters myself on the head tree, with their own files untouched:

| Meter | Claim (`tasks.md` "Final rebase") | My measured result | Match |
| --- | --- | --- | --- |
| wave A `gameplay_log_check.py` | 28/28 | `RESULT: PASS (28/28 checks passed)`, rc=0 | ✅ |
| wave C `wave_c_check.py` | 9/9 | `ALL_WAVE_C_PROBES_PASS \| probes=9 failed=0` (+2 self-declared WARNINGs about `v3_measurements.py`/`linux_static_audit.py` still printing 76/127, explicitly "not a failure of this change") | ✅ |
| wave B `wave_b_check.py` | 8 behavioural green + by-design floor red (Deviation 14) | 8× `PASS`, and the single `FAIL no_magic_offsets` reason is exactly `added-lines скан странно пуст: файлов=5 строк=124` — the same 5 files / 124 code lines Deviation 14 names | ✅ |

Reproduction hazard I hit and must record, because it can silently fake a green B:
`wave_b_check.py`'s added-lines base is `git merge-base HEAD origin/main` with a **fallback to the
historical `295690b`** (`wave_b_check.py:647-660`). A plain `git clone` of this repo has no
`origin/main` ref, so my first B run measured 2938 lines / 16 files (all four waves) and reported
`PASS no_magic_offsets` — a false green. After binding `refs/remotes/origin/main` to `817bf52` the
run reproduced the documented floor red above. Anyone re-verifying Deviation 14 must check that ref
first.

---

## 4. Rollback coherence with the actual commits

`rollback.md` is an **empty template** (0 content lines under its four headings; sibling packages
A/B/C/`2e7698` all carry 22-38 filled lines). The *substance* exists elsewhere and is true:

- **Warp off by default:** `GameScene.swift:214` / `:222` return immediately when
  `EXOLON_DEBUG_WARP` is unset; a malformed value is refused on stderr (`:225-227`) and only a
  member of `includedLevels` (125 names) is accepted (`:216-217`), so nothing caller-shaped reaches
  `TMXLevelRuntime`.
- **Structural kill switch:** the whole warp lives inside `#if DEBUG` (`:200-240`), and
  `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` occurs **exactly once**, in the project Debug block
  — measured by me, asserted by `warp_debug_only`. It is absent from Release by construction, not by
  convention.
- **No persisted state:** `git diff 817bf52..HEAD` touches no persistence type;
  `GameCheckpoint` (`GameScene.swift:947-953`) is unchanged (level/ammo/grenades/points/lives); the
  new latch and stage clock live only in `StageBoundaryLedger` process memory; startup
  `persistence.clearCheckpoint()` (`:940`) makes the checkpoint-resume path unreachable, which is
  also what keeps the stage clock honest (`:967-969` comment verified against `:961-969`).
- **One-step forward-fix/revert:** matches `change-spec.yaml` `rollback: {strategy: forward_fix,
  maximum_steps: 1}` and `brief.md:39`.

So: the rollback story is coherent **with the tree** and incoherent **with the artifact that is
supposed to carry it**.

---

## 5. Honesty of release.md / requirements.md on the two known soft spots

- **`phaseTicks` cadence unconfirmed.** Correctly and forcefully disclosed *in product and in
  evidence* — `GameConstants.swift:100-112` ("UNCONFIRMED vs original", the docs_researcher SILENT
  ruling, and the deliberate non-derivation from the `:131-136` 700-loop pursuer), `cutover.md`,
  `brief.md` ruling 2, and FORBID-003's `ladder_is_declared_deviation`. But `requirements.md`
  AC-006's line and the file's **empty** `Non-functional requirements → Performance` slot say
  nothing about it, and `release.md` has no Go/no-go section to carry it.
- **M3 / load sensitivity.** `tasks.md:145-147` discloses it ("wave A's … M3 append-timing assert
  tripped twice under host load 18.9 and passed on the third clean run — pre-existing sensitivity").
  Traceability checked: the assert is wave A's `emission_cost_budget [AC-006]`
  (`gameplay_log_check.py:762-782`, `producer_ns_per_event` ≤ 5 % budget, `drain_capacity_ev_per_s`
  ≥ 8× realtime), and "M3" is the architect's measurement id for `beginTick`+`emit`
  (`analysis-architect.md:54`), not a check name — so a reader of `tasks.md` alone cannot find the
  control. It is absent from `release.md` ("Metrics and alerts" / "Go/no-go criteria" are both empty)
  and from `requirements.md`. My run passed under load average 8-12, so the caveat is real but not
  currently biting; it belongs in the gate instructions.

---

## 6. Findings (most severe first)

1. **[Critical-for-this-review, documentation] `release.md` is empty** (803 bytes = title + 4
   headings, 0 content lines). For a route with `intent: release`, risk `high`, this is the artifact
   that should state: PR-only delivery and merge position; "no runtime flag — the sequence is armed
   at `GameScene.swift:832`; `EXOLON_DEBUG_WARP` is Debug-only and absent from Release"; the
   observable signals (`RESULT` lines of the three verifiers, `MACOS_EVIDENCE=ABSENT`,
   `bonus.stage_points` component identity); and the go/no-go list (App-owned
   `adaptive-trust-ci/verified@<policy-sha12>` on the exact head SHA + both review receipts + a
   re-recorded verification receipt). Every sibling package in `engineering/changes/` fills the same
   file with 22-38 lines, so this is a repo-norm violation, not a house style.
   *Failure mode if left as is:* the release receipt is recorded over an empty release plan, and the
   next auditor has nothing to contradict.
2. **[Major, documentation] `rollback.md` is empty** — same shape as finding 1; the true content
   (single `git revert` of the merge; warp needs no unwind because it is not compiled in Release;
   no persistence or migration to recover because `GameCheckpoint` is unchanged; the schema code
   tables are append-only so a revert restores codes 1-3 / 1-1 without stranded persisted values)
   exists only in `brief.md:39` and `change-spec.yaml`. AGENTS.md requires the rollback/forward-
   recovery story to be written down for a production-facing change.
3. **[Major, PR wording] PR #17 body is stale and one clause-range claim overstates.**
   (a) "Merge position … **Requires one more rebase onto C-merged main** before the final
   gate/receipt cycle (D-1 rebased onto A+B-era main `17a742a`)" is false at head `84b7813`, which
   *is* rebased onto `817bf52` — a human gate-reader is told work remains that is already done, and
   told the receipts predate a rebase that already happened.
   (b) "**Complete** ORIGINAL_MECHANICS:**138-148** sequence" is wider than delivered: the change
   implements `:140-146` (as every code comment and the probe's own E16 text say), `:147` is
   explicitly deferred in `brief.md`/`tasks.md`, and `:148` is pre-existing. The deferral appears
   nowhere in the body.
   (c) "Review wave (security+**test** per route)" — the route selects `security_reviewer` +
   `release_reviewer` and requires evidence kinds `security_review` + `release_review`; a "test
   review" would not satisfy it.
4. **[Minor, internal consistency] `evidence/cutover.md` §2, `tasks.md` Deviation 9 and `tasks.md`
   D-1-readiness §7 all attribute a two-member declared set
   (`{hardened_runtime_key_count, hardened_deferral_recorded}`) to `change-spec.yaml` FORBID-002, but
   the typed file has declared exactly the measured one-member set in **every** commit of this branch
   (`c402526`, `7929818`, `84b7813`, and the pre-rebase `e0169e5`, `68eda03` — all checked).
   Deviation 9's sentence "The spec text was not silently 'fixed'" therefore describes an edit that
   never happened. Direction of risk is safe (the typed authority is the *stricter* of the two, so
   nothing can be laundered), but the deviation record is unanchored and should quote the spec
   correctly.
5. **[Minor, documentation] `requirements.md:77` is an orphaned fragment** —
   `  29/29 controls, on the extended tree).` sits as a dangling line after the citation-rebind
   table (leftover from the rebinding edit). `decisions.md`'s 2026-09-24 probe entry says "46 before,
   126 after"; the measured value on head is **127** (the PR body is the one that is right).
6. **[Nice to have, latent coupling] OM:144's +1 life rides inside the OM:146 guard**:
   `GameScene.swift:843-847` applies `gameState.lives = award.livesAfter` inside
   `if award.refillsAmmoAndGrenades { … }`, a flag named for the refill clause and hard-coded `true`
   at `StageBoundaryLedger.swift:249`. Today correct; if a future component ever returns
   `refillsAmmoAndGrenades: false`, the boundary silently stops granting lives, and **no Linux
   control can see it** (`GameScene` cannot execute there — `stage_boundary_check.py` docstring says
   so), only play observation E16. Suggest moving the life assignment out of that branch, or
   renaming the flag.
7. **[Nice to have, gate hygiene] `macos_handout_check.py` derives its phase from the tree it is
   guarding**: with both `ENABLE_HARDENED_RUNTIME` lines stripped, my scratch run reported
   `phase=D2` and `cutover_set_exact=PASS` (vacuously — "cutover not due yet"), while
   `entitlements_and_hardening_shape=FAIL` kept rc=1. The gate still fails closed; the
   cutover-specific claim just stops being evaluated on a de-repaid tree. Recording the default to
   `--phase D1` in the go/no-go line (finding 1) removes the ambiguity.

---

## 7. Conditions to clear before the release receipt is recorded

1. Fill `release.md` (Deployment / Flags / Metrics / Go-no-go) — content is available verbatim from
   §1-§5 of this report and `evidence/cutover.md` §6.
2. Fill `rollback.md` (triggers / one-step revert / why no data recovery is needed / post-rollback
   verification: the same three meters plus `wave_b_check.py`'s floor behaviour).
3. Update PR #17 body: drop the "requires one more rebase" paragraph (head is on `817bf52`), narrow
   the norm range to `ORIGINAL_MECHANICS:140-146` and add the deferred list (`:147`,
   `stageExitMarkers`, cursor minigame, `VERSION`/README), and name the review wave correctly
   (security + release).
4. Correct the FORBID-002 narrative in `cutover.md` §2 / Deviation 9 (quote the one-member declared
   set that the typed spec actually contains), the orphan line `requirements.md:77`, and
   `decisions.md`'s "126" → 127 if it is being restated as a current measurement.
5. Re-run `python3 scripts/grok_verify.py --mode pr` and record the receipt **after** the review
   reports land: the current `pass` receipt is bound to tree fingerprint
   `ecff8744067d5579…` @ 2026-09-25 02:13:36Z (05:13 GMT+3). I verified that fingerprint was still
   current when this review started, and measured it drift to
   `ff51022786375dbe…` as soon as `review-release.md` and `review-security-1.md` appeared — so the
   verification receipt is stale **right now** by construction, and the re-record must be the last
   write in this tree.
6. Request the App-owned external check on the exact head SHA. As of this review **no
   `adaptive-trust-ci/verified@*` check run exists on `84b7813`, `7929818` or `e0169e5`** — the only
   check ever recorded on the current head is GitGuardian. Local receipts and this report are not
   merge authority.

If a change to the product tree is made to satisfy findings 6/7 (the two code-level suggestions),
the head SHA moves and items 5 and 6 must be redone against the new SHA.

---

## 8. What this review does **not** certify

No macOS fact of any kind. `MACOS_EVIDENCE=ABSENT (unverified)` (rc=1, measured here) is the
steady state of this repository, per the owner's 2026-09-25 statement — there is no Apple hardware
and no Developer ID, so Track A and Track B are structurally unrunnable, not pending. Audit #15's
signing/notarization clause stays open for that reason alone, and this verdict says nothing about
archived bundles, `codesign`, `spctl`, `notarytool`, `stapler`, or a play-through of E1…E16.
Nothing in this report constitutes merge authority.
