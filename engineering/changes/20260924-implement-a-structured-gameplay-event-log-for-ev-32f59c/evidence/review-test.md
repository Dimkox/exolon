# Test review — wave A structured gameplay event log + P1-9/P1-4/P1-8/P1-6 stream predicates

- Change: `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c` (route `32f59cc7dcb6`,
  tier yellow, domain event). Baseline `295690b`; reviewed content = the working tree (uncommitted).
- Role: `test_reviewer`, read-only over the tree. **Files written by this review: only
  `engineering/changes/…/evidence/review-test.md`.** Every mutation below happened in
  `/tmp/ctl/cases/*` (copies of harness artifacts) or `/tmp/shadow/*` (a copy of `Exolon/`,
  `Exolon.xcodeproj/`, `engineering/contracts/`, the change dir) — never in tracked files.
- Host: Linux, Python 3.12.3, Swift 6.4 (`/opt/swift/usr/bin/swiftc`), 14 physical cores.
  `xcodebuild` is absent here, so no macOS build is observable in this review.
- Reproduction run: `python3 evidence/gameplay_log_check.py` (self-build) →
  **`RESULT: PASS (23/23 checks passed)`**, exit 0. Transcript kept at
  `/tmp/mine/full-run.txt`; artifacts at `/tmp/exolon-harness-9dtcwqsx/artifacts`.
- Side effect observed: that run rewrote `evidence/harness/last-run.txt` (gameplay_log_check.py:1292)
  inside the tree. A second reviewer's run rewrote it again while this review was in flight
  (hot-path now reads 54.0/54.8/56.2 ns; mine 53.9/54.3/54.8; the author's 54.1/55.4/65.3).
  I left the newest transcript in place rather than restoring a stale copy. See R-8.

VERDICT: **fail** (evidence quality, not product behaviour)

Meaning: the four wave-A fixes **are** genuinely gated — both revert knobs are real product-code
switches, and predicate A and predicate B go red on the reverted streams for the right reason
(proved below, not taken from the report). What fails this review is the *coverage claim*: six named
checks assert less than their own spec sentence (AC-001, AC-003, AC-004, INV-001, INV-003, INV-004 —
R-2…R-5, R-7), and `test-plan.md:33` lists a static `swiftc -frontend -parse` gate that does not exist
while 692 changed lines of SpriteKit-bound product code are compiled by nothing on this host. All
eleven findings are fixable inside `evidence/gameplay_log_check.py` + `evidence/harness/main.swift`
(+ `test-plan.md`, `release.md`, `change-spec.yaml`) without touching `Exolon/`.

---

## 1. Spec → symbol map (all 19 bound symbols resolve; executed 23/23)

Verified mechanically: imported `gameplay_log_check.py`, resolved every `test` path in
`change-spec.yaml`, and ran the suite. Zero unresolved symbols.

| Spec id | `evidence/gameplay_log_check.py::symbol` | Line | Verdict of this reviewer |
| --- | --- | --- | --- |
| AC-001 | `harness_level2_complete` | 499 | asserts, but one clause is a tautology → **R-2** |
| AC-002 / FORBID-002 | `p1_9_fixed_passes_and_revert_fails` | 525 | asserts; revert control flips for the right reason |
| AC-003 / FORBID-001 | `p1_8_fixed_passes_and_revert_fails` | 566 | asserts; "never silence" arm has zero executed coverage → **R-4** |
| AC-004 | `p1_4_stream_predicate` | 603 | asserts, but not causally → **R-5** |
| AC-005 | `p1_6_stream_predicate` | 636 | partially: "subsequent zone load" never executed → **R-6** |
| AC-006 | `emission_cost_budget` | 657 | asserts (band far wider than the reported figure, see §4) |
| AC-007 | `pbxproj_registration_complete`, `native_target_count` | 678, 729 | asserts; extra independent flip also red (§3 S5) |
| INV-001 | `stream_invariants` | 925 | asserts gap/monotonicity; **blind to a torn tail → R-3** |
| INV-002 | `ts_us_derivation` | 981 | asserts (131 796 records) |
| INV-003 | `counters_never_reset`, `kind_enum_append_only` | 999, 1060 | assert; `= 0` exemption lets a rewind through → **R-7** |
| INV-004 | `hot_path_is_allocation_free`, `diagnostics_import_boundary` | 1093, 1132 | assert; grep gate skips the middle callee → **R-7** |
| FORBID-003 | `forbid_wallclock_fields`, `forbid_log_in_clone` | 784, 847 | assert |
| FORBID-004 | `drops_are_counted` | 878 | asserts with real arithmetic (5 008 declared vs 512 written = 4 496) |
| SIG-001 | `session_signal_health` | 1209 | **not bound in change-spec.yaml** (`observability[]` carries only `id/metric/proves`; nothing in `scripts/` references `observability`) → R-9 |
| SIG-002 | `kill_switch_no_file` | 1268 | same binding gap; executes programmatic `.off`, never an env launch → R-10 |
| SIG-003 | *no dedicated symbol* — inline in `predicate_a` (318, budget at 350-356) reached via `p1_9…` and `forbid_post_transition_steps` (769) | — | branch works (§3 C8) but is never exercised by data: max observed motion/frame = 2 |
| (unbound extras) | `envelope_schema_valid`, `rotation_linkage` | 1159, 1232 | run and assert; not tied to any spec id |

---

## 2. Are the named checks actually asserting? (code read + 27 independent flips)

Nothing in the suite is a bare `print`. `main()` (1326-1380) converts *any* exception from a check
into `FAIL`, so a crash cannot masquerade as a pass. The decoration I found is narrower than
"no assertion": four checks assert a property that is either unsatisfiable-by-construction, dead, or
weaker than the sentence they are bound to. Each is demonstrated below by a flip that **should** have
redden them and did not.

### Contradictory controls executed by this reviewer

Flips of artifacts-only cases were made on copies in `/tmp/ctl/cases/<name>` and re-checked with
`python3 gameplay_log_check.py --artifacts <copy> --only <check>`; source flips on `/tmp/shadow`.
Full logs: `/tmp/ctl/controls.out`, `/tmp/ctl/controls2.out`, §3 below.

| # | Independent flip (not the shipped control) | Target check | Result |
| --- | --- | --- | --- |
| C1 | 50 % truncation of `session-level2` tail | `stream_invariants` | **STILL-GREEN → R-3** |
| C1b | same file, `--only harness_level2_complete,stream_invariants` | AC-001 | FAIL ("simulated only 633 ticks") |
| C1c | last 3 records (incl. `log.end`) torn off `p1-9-fixed` | `p1_9…`, FORBID-002, `envelope_schema_valid` | **STILL-GREEN → R-3** |
| C2 | one `player.motion` (tick 501) deleted from `session-level2` | `harness_level2_complete` | **STILL-GREEN → R-2** |
| C3 | 744 of 749 `bonus.stage_boundary_suppressed` removed, `seq` re-densified | `p1_8…` | **STILL-GREEN → R-4** |
| C4 | same removal **plus** `player_x` set to the real-scene value (2100 > 510·4) | `p1_8…` | FLIPPED-RED ("706 stage-end triggers but only 45 award/suppression records") |
| C5 | leaked `player.jump` after the held-latch teleport, no release edge, `after_teleport=false` | `p1_4…` | **STILL-GREEN → R-5** |
| C6 | identical leak but `after_teleport=true` | `p1_4…` | FLIPPED-RED (both predicate branches) |
| C7 | empty `off-*.jsonl` planted next to the kill-switch scenario | `kill_switch_no_file` | FLIPPED-RED |
| C8 | a 16th `player.motion` in one frame of `p1-9-fixed` (SIG-003) | `p1_9…` | FLIPPED-RED ("frames carrying more than the 15-step budget: {3: 16}") |
| C9 | one simulated step injected after `state.zone_transition` inside its frame | `forbid_post_transition_steps` | FLIPPED-RED |
| C10 | a second `bonus.stage_points` for zone 124 in one playthrough | `p1_8…` + `forbid_double_stage_bonus` | FLIPPED-RED |
| C11 | `lives_x1000` component 9000 → 8000 | `p1_8…` + FORBID-001 | FLIPPED-RED (sum identity **and** per-component rule) |
| C12 | award `lives_before` 9 → 8 with the component left at 9000 | `p1_8…` | FLIPPED-RED ("9000 != lives_before 8 x 1000") |
| C13 | `bonus.stage_component` record deleted entirely | `p1_8…` | FLIPPED-RED ("total 9000 != sum of its components 0") |
| C14 | every suppression witness re-labelled `not_stage_end` | `p1_8…` | FLIPPED-RED |
| C15 | envelope key order swapped (`tick` before `seq`) | `envelope_schema_valid` | FLIPPED-RED |
| C16 | `player.motion.zone` written as the string `"0"` | `envelope_schema_valid` | FLIPPED-RED |
| C17 | one `ts_us` drifted +12 µs | `ts_us_derivation` | FLIPPED-RED |
| C18 | `wall_utc` injected onto a `player.motion` | `forbid_wallclock_fields` | FLIPPED-RED (three separate clauses) |
| C19 | `player.motion` kind renumbered to an unused raw value in `contract.txt` | `kind_enum_append_only` | FLIPPED-RED ("raw values are not dense from 1") |

**20 of 27 controls flipped red.** The seven that stayed green are the findings, not noise: in every
case the *logic* exists (C4/C6/C1b prove the corresponding branch works when it is reached) — what is
missing is that the shipped data can never reach it, or the assertion is written against a
self-reported field.

Scope note for reproducibility: `fixed/p1-8-fixed` spans two rotation files, and the C3-C14 edits
touched the rotation-0 file only. That is why C3 reports "49 suppression witnesses" (5 kept in file 0
+ 44 untouched in file 1) and why C4's failure message reads "706 stage-end triggers but only 45
award/suppression records". Both numbers are consistent with the pristine merged stream
(750 triggers, 750 outcomes, 1 award + 749 witnesses) and neither weakens the conclusion: a stream
that loses 744 of its 749 witnesses is a green run.

### Revert knobs are product code, not harness theatre (AC-002 / AC-003 requirement)

- `EXOLON_REVERT` is read once (`main.swift:44`) and only feeds **initializer arguments of product
  types**: `Loop(… resetAccumulatorOnZoneTransition: !reverted)` (main.swift:451) →
  `FixedTickDriver.init` (FixedTickDriver.swift:37-47) whose `reset()` opens with
  `guard resetAccumulatorOnZoneTransition else { return }` (FixedTickDriver.swift:104); and
  `Loop(… awardsPerComponentPerZone: reverted ? 0 : 1)` (main.swift:533) →
  `StageBoundaryLedger.outcome` (StageBoundaryLedger.swift:105-121, once-key at 112).
  No stepping/award code is duplicated in the harness for the revert path.
- Flips observed in the **checker**, not only the harness: predicate A on `revert-p1-9` fails with the
  exact clause `"simulated step(s) ran in the new zone inside frame 2"` (14 post-transition steps of a
  15-step frame — measured independently: max motion/frame in `p1-9-reverted` = 15, 14 of them after
  the transition at seq 5), and the checker additionally demands the reverted stream carry **no**
  `tick.accumulator_reset` (gameplay_log_check.py:539-541). Predicate B on `revert-p1-8` fails with
  `{'124': 750}` double-awards, ≥100 awards and 0 suppression witnesses (566-600).

---

## 3. Product-source seam flips (`/tmp/shadow`, no rebuild needed for these checks)

| # | Flip to a shadow copy | Check | Result |
| --- | --- | --- | --- |
| S1 | `GameScene.swift:37` → `FixedTickDriver(events: events, resetAccumulatorOnZoneTransition: false)` | `p1_9…` | FLIPPED-RED ("GameCore/GameScene.swift opts out of the P1-9 fix") — the seam grep is real |
| S2 | `let diagnosticName = String(describing: rawKind)` inside **`appendRecord`** (GameplayEventLog.swift:439) | `hot_path_is_allocation_free` | **STILL-GREEN → R-7** |
| S3 | `import SpriteKit` added to `StageBoundaryLedger.swift` | `diagnostics_import_boundary` | FLIPPED-RED |
| S4 | new method `func rewindCountersForNewGame() { tickValue = 0 \n frameValue = 0 }` | `counters_never_reset` | **STILL-GREEN → R-7** |
| S5 | `LauncherBonusState.swift` removed from the PBXGroup children only (all other 3 markers intact) | `pbxproj_registration_complete` | FLIPPED-RED ("not a member of any PBXGroup children list") — covers a marker kind the shipped mutation control (708-710, PBXSourcesBuildPhase only) does not |
| S6 | `String(describing:)` directly in `emit()` | `hot_path_is_allocation_free` | FLIPPED-RED (gate sanity) |
| S7 | **syntax garbage in all four SpriteKit-bound changed files** (`GameScene`, `TMXLevelRuntime`, `LevelObstacles`, `AppDelegate`) → `swiftc -parse` reports 12 errors on that tree | full 23-check suite | **22/23 PASS** — only `p1_6_stream_predicate` fails, incidentally, because the AC-005 signature regex stopped matching → **R-1** |

---

## 4. Harness honesty

| Claim | Verified how | Outcome |
| --- | --- | --- |
| "compiles and runs the real Foundation-only product types" | `run.sh:33-43` compiles 9 product files with `-O`; `grep -n "class Player\|struct InputSnapshot\|enum GameplayEventKind\|final class InputState" evidence/harness/main.swift` → **no replica type defined** | TRUE |
| "motion records come from real product getters, not replicas" | `main.swift:257-265` `emitMotion()` reads `player.position`, `player.motionState`, `player.isGrounded`, `player.facing`, `player.hasExoskeleton`, `player.velocity` — all declared in `Exolon/GameCore/Player/Player.swift`, which is in the compiled subset; `player.events = events` is set in `Loop.init` (main.swift:193). `player.jump` is emitted **only** by product code (`Player.swift:340-344`), never by the harness except the deliberate hand-written control (`main.swift:520`) | TRUE (mechanically) |
| Scene-loop fidelity | `Loop.update` (main.swift:199-207) mirrors `GameScene.update` (GameScene.swift:184-196): `driver.beginFrame → events.beginFrame → while driver.beginStep`, and `checkScreenExit` (main.swift:276-…) reproduces `state.zone_exit → stage-boundary outcome → transition/enterContentComplete` in product order (GameScene.swift:739-752) | TRUE, with one scripted liberty: `armedExit` (main.swift:170) fires the exit without geometry, which is what leaves `player_x` at 352 and kills predicate B's trigger anchor → **R-4** |
| Diagnostics stay Foundation-only | independent `grep -n "^import" Exolon/GameCore/Diagnostics/*.swift` → five `import Foundation`, nothing else; S3 proves the gate bites | TRUE |
| No-shim negative control | `run.sh:71-75` (build without the shim must fail, else `exit 1`); my run's transcript: `OK: без стаба не собирается (…GameConstants.swift:1:8: error: no such module )` | EXECUTED and correct |
| Artifacts stay outside the clone | `run.sh:45-48` refuses an in-clone `EXOLON_HARNESS_OUT` (exit 73); `forbid_log_in_clone` scans `ROOT.rglob('*.jsonl')` + every `log.begin.path` | TRUE |
| "hot-path 54–68 ns/event ⇒ 0.019–0.025 %" (`tasks.md:58`) | reproduced by `scenarioCostBudget` (main.swift:786-870) and consumed by `emission_cost_budget` (657): two full self-build runs gave 53.9–56.2 ns, the author's 54.1–65.3 ns | REPRODUCIBLE. Note the *asserted* band is 0.5–1000 ns + `producerNs*60 < 5 000` + `percent ≤ 5` (main.swift:841-853) — far looser than the reported figure, so the 54–68 number is a measurement, not a gate. Acceptable against AC-006's wording; the formatting control (main.swift:820-832) is a synthetic string-interpolation loop, not the rejected design routed through the log |
| "1 award + 749 suppression witnesses / 750 awards reverted" | counted from the transcripts, not the report: `fixed/p1-8-fixed` = `bonus.stage_points` 1, `bonus.stage_component` 1, `bonus.stage_boundary_suppressed` 749; `revert-p1-8` = 750 awards (all `completed_zone` 124), 0 witnesses, 750 `state.title_enter` all `has_saved_checkpoint=true` → one playthrough under `playthroughs()` | TRUE; `test-plan.md:20` still quotes the older probe figure "1+524" (doc drift only) |
| AC-001 "at least one motion per simulated tick" | the Python clause is `motion < ticks` where `ticks` is the **distinct-tick set taken from the motion records themselves** (gameplay_log_check.py:502-506) | **TAUTOLOGY → R-2** |
| `.asynchronous` writer mode (the shipped Debug default) | only `.synchronous` and `.off` logs are ever constructed and run; async appears at `main.swift:94` (interval selection) and `691` (resolver assertion) | NOT EXECUTED → R-10 |

---

## 5. Findings

### R-1 (Critical, high confidence, category test-coverage, direction certifies-falsely) — the SpriteKit half of this change is compiled by nothing, yet `test-plan.md` claims a parse gate
`GameScene.swift` (+594), `AppDelegate.swift` (+38), `TMXLevelRuntime.swift` (+38),
`LevelObstacles.swift` (+22) are changed and are **absent from `run.sh:33-43`**;
`grep -c "GameScene.swift\|TMXLevelRuntime\|LevelObstacles\|AppDelegate" evidence/harness/run.sh` → 0.
No check in `gameplay_log_check.py` shells out to anything but `run.sh` (single `subprocess.run`,
line 1291), so nothing parses them either. `test-plan.md:33` nevertheless lists
"Static: `swiftc -frontend -parse` all touched Swift files" as an automated check, and `release.md:28`
leans on "parse + arity cross-check" for the accepted residual. S7 above: with 12 real parse errors in
those four files, 22/23 checks pass and `RESULT` says PASS for all of
`stream_invariants / ts_us_derivation / counters_never_reset / kind_enum_append_only /
hot_path_is_allocation_free / diagnostics_import_boundary / envelope_schema_valid /
session_signal_health / rotation_linkage / kill_switch_no_file / pbxproj_registration_complete /
native_target_count / forbid_wallclock_fields / forbid_log_in_clone / drops_are_counted /
harness_level2_complete / p1_9… / p1_8… / p1_4… / FORBID-001 / FORBID-002 / AC-006`.
The regression that ships: a typo, a renamed symbol or an `emit` arity drift in any of those four
files lands as "23/23 green, AC-007 pbxproj registration complete" and only breaks on someone's Mac.
Fix (cheap, proven available): `swiftc -parse` on the four files is **0 errors today** in this tree, so
add a `touched_swift_files_parse` check that runs `/opt/swift/usr/bin/swiftc -parse` over
`git diff --name-only` ∩ `*.swift` and requires empty stderr (with a control: an injected `(((` must
redden it). Failing that, delete the plan line — a gate that is documented but absent is worse than an
honest gap.

### R-2 (Suggestion, high confidence, category correctness-of-assertion) — AC-001's headline clause cannot fail
`harness_level2_complete` (499): `ticks = len({r['tick'] for r in records if name == 'player.motion'})`
and `motion = len([...player.motion...])`, then `if motion < ticks: raise`. A set built from a list is
never larger than that list, so the clause is unsatisfiable by construction; C2 (delete the motion
record of tick 501) leaves the check green and re-prints "1297 motion records over 1297 ticks".
The property *is* asserted one level down, in Swift, where `ticks` is the real counter
(`main.swift:434`, `Harness.check(motion >= Int(ticks))`) — but that only gates the self-build mode;
the documented reuse mode (`--artifacts`, used by every re-verification after a fix round) is blind.
The true value is already in the artifacts: `manifest.json → scenarios.harness_level2_complete →
"ticks=1298"`, read by `extras_for`/`numeric` (134-145) but never used for this scenario.
Fix: compare distinct motion ticks against `numeric(extras_for(artifacts,
'harness_level2_complete'), 'ticks')`, and keep a control that a removed motion record reddens it.

### R-3 (Suggestion, high confidence, category test-coverage) — INV-001 does not fail on a truncated log, while its own PASS line says it does
`stream_invariants` (925) checks density from the first record forward, monotonic `tick`/`frame` and
`schema_version == 1`; a **prefix** satisfies all three. The truncation control at 955-959 runs
`_seq_problems` (962) — a helper that additionally requires a closing `log.end` and
`log.end.events == len(body)` — and then reports "a truncated copy fails it". That sentence describes
the helper, not the shipped check. C1: half of `session-level2` removed → `PASS stream_invariants`.
C1c: `p1-9-fixed` missing its last 3 records → `p1_9…`, FORBID-002 and `envelope_schema_valid` all
PASS. `test-plan.md:24` ("Negative controls … 2. Truncated log FAILS seq continuity") is therefore not
implemented. Fix: run `_seq_problems` over every gameplay stream in `stream_invariants` (it already
exists and is exactly the right predicate), and drop `log.end`-only reliance from AC-001.

### R-4 (Suggestion, high confidence, category test-coverage) — "never silence" in AC-003/FORBID-001 is dead on the shipped data
Two branches of `predicate_b` carry the anti-silence requirement and neither can fire here:
- 433: `triggers = [r for r in records if name == 'state.zone_exit' and r.get('player_x',0) > 510*4
  and r.get('zone') in (24,49,74,99,124)]`. The harness arms the exit artificially (`armedExit`,
  main.swift:170/416/422/458/543) while the player stays at the spawn `x=88`, so all **750**
  `state.zone_exit` records in the merged `fixed/p1-8-fixed` stream carry `player_x = 352`
  (measured; 0 of them above 2040) → **triggers = 0** while `awards + suppressions = 750`, and
  `0 > 750` is never true. In a production stream the clause is exactly right (the scene only emits
  the record when `player.position.x > 510`, GameScene.swift:740).
- 430: `if not suppressions and counts and max(counts.values()) < 1` — `counts` values are award
  tallies, always ≥ 1, so the conjunction is unsatisfiable. The check is decoration.
Consequence: C3 removed 744 of 749 suppression witnesses (re-densifying `seq`) and `p1_8…` still
printed "fixed: 1 award(s) + 49 suppression witnesses" as a pass. The only live anti-silence clause is
`if not suppressions` (570-573), which catches total loss of the witness, not partial. C4 shows the
arithmetic is correct once anchored: the same removal with `player_x=2100` fails as designed.
Fix: count stage-end triggers as `state.zone_exit{zone ∈ stage-end set}` (drop the `player_x` term, or
park the harness player past 510 so the shipped evidence exercises the production shape), assert
`triggers == awards + suppressions` per playthrough, and delete line 430.

### R-5 (Suggestion, high confidence, category correctness-of-assertion) — AC-004's predicate is not decidable the way the spec words it
`predicate_c` (442) declares a leak only for jumps with `r.get('after_teleport') is True` (459), and its
second loop (465) also keys on that flag. AC-004's sentence is positional — "no `player.jump` occurs
until a fresh `input.action_edge{action:jump,pressed:false}` precedes it". C5 injected exactly that
defect (a `player.jump` one tick after `player.teleport{jump_latch_held:true}`, no release edge before
it, `after_teleport=false`) and `p1_4_stream_predicate` PASSED, reporting it as a "legitimate jump".
C6 (same record, flag `true`) fails. So the stream predicate can only see the defect in builds that
self-report it — and the pre-fix P1-4 shape is a build that never sets the flag
(`Player.swift:124-138`: `jumpedThroughContextHold = jumpJustPressed && contextHoldsJumpLatch`, and
`contextHoldsJumpLatch` exists only because of the fix). Real coverage today comes from the source
greps at 629-632 and the harness latch asserts at main.swift:764-779.
Fix: drop the `after_teleport` conjunct at 459 — any `player.jump` between a held-latch teleport and
the next `pressed:false` jump edge is the violation — and keep 465 as the signature clause.

### R-6 (Suggestion, high confidence, category test-coverage) — AC-005's "a subsequent zone load" clause is never executed, and the P1-6 product call sites are uncompiled
`p1-6-fixed` contains exactly `log.begin`, 1 `bonus.double_launcher`, 40 `entity.launcher_fire`,
`log.end` — **no `state.zone_load` and no `state.zone_transition`** (measured), so "the launcher keeps
firing *after a zone load*" is evidenced only as "after the payout, in the same zone". The records
themselves are harness-written (main.swift:578, 588) around the real product decision type
`LauncherBonusState`; the product emission sites
(`GameScene.swift:1280`, `TMXLevelRuntime.swift:153`) are outside the compiled subset, and AC-005's
TMX clause is a signature regex (640-643) — which is precisely why S7 caught it only by accident.
Fix: in `scenarioP16Launcher`, run the fire sweep after `loop.transition(to: …)` (or reconstruct the
runtime state the way a zone load does) so `predicate_d`'s "later fire" is a later-zone fire; state the
regex-vs-compile limitation in the deviation list if the uncompiled file stays out of scope.

### R-7 (Suggestion, high confidence, category correctness-of-assertion) — two grep gates miss the code they name
- INV-004: `hot_path_is_allocation_free` (1093) extracts `func emit(_ kind: … entity: UInt16` and
  `private func storeLocked` — but the hot path is `emit → appendRecord → storeLocked`
  (GameplayEventLog.swift:428/438/447). S2 put `String(describing:)` into `appendRecord` and the gate
  stayed green; S6 put it in `emit` and it went red. The "allocation-free hot path" is therefore only
  verified at 2 of its 3 frames. Fix: include `appendRecord` in the scanned set (or scan the whole
  transitive closure reachable from `emit` within the file).
- INV-003: `counters_never_reset` (1027-1030) flags counter assignments "outside the monotonic
  increment" by line shape, exempting anything ending in `= 0` — which exempts the initialiser *and*
  any rewind. S4 added `func rewindCountersForNewGame() { tickValue = 0; frameValue = 0 }` and the
  check stayed green, while INV-003's sentence forbids exactly that. Fix: restrict the `= 0` exemption
  to property declarations (`private var tickValue: UInt32 = 0`, line 309) — e.g. require the line to
  start with `private var`, and treat a bare `tickValue = 0` inside a function body as an offender.
  Secondarily: INV-003 enumerates death, respawn, pause, `beginFromTitle` and `restartFromBeginning`;
  the executed stream only crosses `state.zone_transition`/`zone_load`/`zone_loaded`. The harness does
  assert `reset(reason: .newGame)` leaves `frame` untouched (main.swift:720-721), but those three
  records appear only as part of the synthetic per-kind sweep in `contract-*.jsonl`
  (`game.game_over` 1, `state.restart` 1, `state.title_enter{has_saved_checkpoint:false}` 1 — and that
  file is deliberately excluded from gameplay evidence by `gameplay_streams` at 275-280 and never
  reaches `predicate_b`). So no executed *gameplay* stream crosses a playthrough boundary and the
  playthrough-split half of `playthroughs()` (360-383) is unexercised by data — which is what
  makes R-4's per-playthrough reasoning untestable here.

### R-8 (Nice to have, high confidence, category workflow) — the checker writes into the tree on every self-building run
`run_artifacts` (1286-1293) writes `evidence/harness/last-run.txt` — inside the repository — while the
change's own FORBID-003 argument for keeping logs out of the tree is "a non-tracked log inside the
tree stales every fingerprint-bound receipt". Two reviewers running the default mode concurrently
overwrite each other's transcript (observed in this session: three distinct hot-path triplets in ten
minutes). Fix: write the transcript next to the artifacts (`ARTIFACT_DIR`) and copy it in only when an
explicit `--record` flag is passed, or make the fingerprint exclude `evidence/harness/`.

### R-9 (Suggestion, high confidence, category spec-binding) — no observability signal is bound to an evidence symbol
`change-spec.yaml` gives `evidence[]` only to AC/INV/FORBID (19 symbols, all resolve); the three
`observability` entries carry `id/metric/proves` and nothing else, and no file in `scripts/` references
`observability` at all, so nothing binds SIG-001/002/003 to a receipt. SIG-003 has no dedicated symbol
even in the runner — it lives inside `predicate_a`. Consequence: the local receipt can show
"all spec evidence green" while every SIG is unbound. Fix (spec-side, no product risk): add
`evidence: [{"test": "…::session_signal_health"}]` / `…::kill_switch_no_file`, and either bind
SIG-003 to `forbid_post_transition_steps` + `p1_9_fixed_passes_and_revert_fails` or give it its own
symbol; if the spec writer rejects `evidence` under `observability`, that is a factory gap worth
filing separately.

### R-10 (Suggestion, high confidence, category test-coverage) — the two shipped-default postures are asserted, never executed
`scenarioContract` (main.swift:687-700) proves `EXOLON_EVENT_LOG=off` *resolves* to `.off` and that a
programmatically-`.off` log creates no file, and the checker asserts `offFiles=0` + no empty placeholder
(1268-1281, and my C7 flip). It never launches the product with the environment variable set, and
`AppDelegate.swift` — where that env read actually lives — is outside the compiled subset (R-1).
Likewise `.asynchronous`, which the resolver picks as the Debug default (main.swift:691), is never
constructed: every executed log is `.synchronous` or `.off`, so the queue/timer drain path
(`limits.drainInterval`, the inline-drain branch at GameplayEventLog.swift:448-451) has no Linux coverage.
The `drops_are_counted` arithmetic (878-923, verified: 5 008 declared − 512 written = 4 496 counted,
newest tick 5 000 retained) therefore validates the synchronous path only. Fix: add one scenario that
runs `.asynchronous` end-to-end and asserts zero drops at level 2, and record the macOS env-launch run
that `test-plan.md:39-41` already lists as manual.

### R-11 (Nice to have, low risk, forward-compat note) — the component whitelist is ahead of the frozen schema
`predicate_b` (425-428) accepts `lives_x1000`, `bravery`, `timed_ladder`, but
`gameplay-event-v1.schema.json` declares `component_id: ["lives_x1000"]`, so when wave B/C adds the
bravery or timed lane, `envelope_schema_valid` fails first ("not in the frozen enum") and the
amendment-aware identity is fine (C11-C13 prove sum + per-component rules hold with extra or missing
lanes). No action now; the deviation list should say the schema must be amended in the same commit as
a new component.

---

## 6. Which regression could ship through this net (answer to brief item 5)

1. **Any non-parsing/non-compiling edit in `GameScene.swift`, `AppDelegate.swift`,
   `TMXLevelRuntime.swift`, `LevelObstacles.swift`** — 22/23 green (R-1). Highest-impact hole; the
   macOS `xcodebuild` that would catch it is still outstanding per `release.md:21-22`.
2. **A partial-loss regression of the suppression witness** (P1-8 fixed at the ledger, but the scene
   stops emitting `bonus.stage_boundary_suppressed` on some paths) — AC-003 green (R-4).
3. **A P1-4 regression that drops the `after_teleport`/`contextHoldsJumpLatch` reporting** while
   letting a held-UP jump through — AC-004 green (R-5).
4. **A torn or unflushed log tail** (crash/quit path loses the closing records) — INV-001 green for
   every stream except `session-level2`, where AC-001 catches it incidentally via the tick-count floor
   and the `log.end` last-line rule (R-3).
5. **A tick whose step emits no `player.motion`** (the real scene has early `return`s in
   `fixedUpdate`, GameScene.swift:205-232) — AC-001 green (R-2). Note the harness `Loop.fixedStep`
   always emits motion, so this class is not representable in the current artifacts at all.
6. **A rewind of `tickValue`/`frameValue` on a new game or death** — INV-003 green (R-7).
7. **An allocation or a blocking call in `appendRecord`** (frame hitch from the hot path) — INV-004
   green (R-7).
8. **Async-mode drain regressions** (drops at level 2 in the shipped Debug posture) — nothing executes
   `.asynchronous` (R-10), and SIG-001's window is evidenced at 21.6 s (1 300 frames, 2 heartbeats)
   rather than the stated 10 minutes. The 600 s level-2 evidence does exist in the artifacts
   (`p1-8-fixed`: 35 999 ticks, 59 heartbeats, 0 `log.events_dropped`) — it is simply not the stream
   `session_signal_health` reads (1209-1230). Cheapest SIG-001 fix in the whole package.

## 7. What must change for this review to turn green

1. R-1: add the parse gate over the touched Swift files (0 errors today; control = injected garbage),
   or remove the claim from `test-plan.md:33` and re-state the residual honestly in `release.md:28`.
2. R-3 + R-4 + R-5 + R-2: four small edits inside `gameplay_log_check.py`
   (`_seq_problems` over all gameplay streams; `triggers == awards + suppressions` with the anchor
   fixed and line 430 deleted; drop the `after_teleport` conjunct at 459; use `manifest` ticks for the
   one-motion-per-tick clause), each with the contradictory control already written in this report
   (C1c, C3→C4, C5, C2 must all go red).
3. R-9: bind SIG-001/002/003 to symbols in `change-spec.yaml` (or state why they cannot be bound).
4. Point `session_signal_health` at the 600 s level-2 stream (R-6 item 8) and re-run the receipt after
   these edits — the current receipt's numbers stay valid, only the checker changes.

Items 1-4 touch only `evidence/gameplay_log_check.py`, `evidence/harness/main.swift`,
`test-plan.md`, `release.md` and `change-spec.yaml`; none requires a product-code change, and none of
the four wave-A fixes is shown to be wrong by this review.
