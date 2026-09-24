# Test review (delta re-review) — wave A gameplay event log, re-check after the FAIL round

- Change: `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c` (route `32f59cc7dcb6`),
  baseline `295690b`, working tree = the change under review.
- Scope of this pass: verify **on current bytes** that the 8 false-pass items + R-1 + R-8 + R-9 of
  `evidence/review-test.md` are closed, and that the closure is falsifiable — not that the suite is
  merely green again.
- Role: `test_reviewer`, read-only. **Only file written: this one.** All mutations ran in
  `/tmp/d2/cases/*` (copies of the fresh artifacts), `/tmp/sh2/*` (a copy of `Exolon/`,
  `Exolon.xcodeproj/`, `engineering/contracts/`, this change dir) and never in a tracked file.
  `git status --porcelain` shows the same 10 tracked ` M` product/doc files as at the start of the
  wave; nothing else was touched by me.
- Independent reproduction: `python3 evidence/gameplay_log_check.py` (self-build) →
  **`RESULT: PASS (28/28 checks passed)`, exit 0**; my transcript
  `/tmp/exolon-harness-6oe9ln7i/artifacts/last-run.txt`, harness scenarios `ran` = 13 (now including
  `async_writer` and `lane_round_trip`). Checker is now 1 981 lines (was 1 384), harness 1 202 (was 909).

VERDICT: **pass** (test story)

All seven of my false-pass controls now redden, R-1 has a working parse gate that my own garbage
trips, R-8's default run no longer moves the tree, and R-9's limitation is real and verified in the
factory schema. **None of my original items remains must-fix.** Two things stay outside the checker
and are named in §6: the outstanding macOS `xcodebuild` evidence (already a pre-merge item in
`release.md:21-22`) and a fresh verification receipt on the final fingerprint (the 23:06:32Z receipt
is stale now for a reason unrelated to this change — §5.3).

---

## 1. Item-by-item closure, each proven by a control of mine (not the writer's)

| # | Original finding | Fix claimed | My independent control on current bytes | Result |
| --- | --- | --- | --- | --- |
| R-2 | AC-001 "one `player.motion` per simulated tick" was `motion < len(set(motion ticks))` — unsatisfiable | denominator is now the declared counter: `declared_ticks = numeric(extras_for(…,'harness_level2_complete'),'ticks')` and `distinct != declared_ticks or motion != declared_ticks` (gameplay_log_check.py:557-566) + an in-check control that deletes tick 501 | **d1** delete the tick-501 motion; **d2** same delete **plus** re-densified `seq`, so no other check can be the reason | both **FLIPPED-RED**: `"AC-001 needs one player.motion per simulated tick: motion=1297, distinct ticks with motion=1297, simulated ticks=1298"`. Counts cross-checked in the transcript: 1298 motions, 1298 distinct ticks, manifest `ticks=1298` |
| R-3 | INV-001 passed a truncated log while its PASS text claimed the opposite | `_seq_problems` (1074) is now the shipped predicate — density + monotonicity + `schema_version` + **completeness** (must end in `log.end`, `log.end` last, and `events == body + declared drops` for `rot == 0`) — run over **every** stream (1046-1072), with three internal controls | **d3** half-truncate `session-level2`; **d4** tear the last 3 records (incl. `log.end`) off `p1-9-fixed`; **G1** remove the **first 600** records (head loss, seq still dense from its new start — the case nobody listed) | all **FLIPPED-RED**: `d3`/`d4` → `"stream ends without log.end - the tail is missing"`; `G1` → `"log.end declares 1332 events, the stream carries 733 records plus 0 declared drops"` |
| R-4 | AC-003 "every repeat witnessed, never silence" was unreachable (`triggers` anchored at `player_x > 2040` that `armedExit` never produced) + a provably dead `max(counts.values()) < 1` branch | harness now drives real geometry; predicate anchors on `state.zone_exit` past `SCREEN_EXIT_X_Q` (481) and asserts **equality** `triggers == awards + suppressions` (482-487); the dead branch is gone | transcript count: **749** stage-end triggers, **1** award + **748** witnesses = 749 (exact balance) → so a single loss must bite. **d5** strip 738 witnesses across *both* rotation files; **d5c** strip **exactly one** | both **FLIPPED-RED**: `"749 stage-end triggers but 1 awards + 10 suppression witnesses 11 - a trigger was answered silently or twice"` and `"… + 746 … 747 …"` respectively |
| R-5 | AC-004's leak scan keyed on the self-reported `after_teleport` flag | scan is positional now: `leaked = [player.jump where start < seq < release_seq]` (510), no flag term; the flag stays only as the separate signature clause | **d6** inject `player.jump` after the held-latch teleport with `after_teleport=false` and no release edge | **FLIPPED-RED**: `"player.jump at tick 20 followed player.teleport{jump_latch_held:true} at tick 5 with no release edge in between"` |
| R-6 | AC-005's "subsequent zone load" clause never executed | `p1-6-fixed` now carries `state.zone_transition`(seq 22) → `state.zone_load`(24) → `state.zone_loaded`(25) after the payout; predicate D requires fires for the same `object_id` after it | counted from the transcript: 40 `entity.launcher_fire`, **20 strictly after the zone-load block**, `launcher_active_after=true` | matches the check's own report ("40 later shot(s) … of which 20 after a zone load"); clause **executed** |
| R-7a | INV-004 grep skipped `appendRecord`, the real middle of the hot path | scans 4 frames: `emit`, `appendRecord`, `storeLocked`, `beginTick` (1281-1300) + control on a poisoned `appendRecord` | **X1** (shadow tree) `let diagnosticName = String(describing: rawKind)` inside `appendRecord` | **FLIPPED-RED**: `"constructs: ['String\\(', 'String\\(describing']"` |
| R-7b | INV-003 exempted any counter assignment ending in `= 0`, i.e. a rewind | assignment scan (`_counter_write_problems`, 1207) allows only the two property declarations and the two `x = x &+ 1` increments; plus two controls — an injected rewind must be flagged, a renamed declaration must not be | **X2** add `func rewindCountersForNewGame() { tickValue = 0; frameValue = 0 }` | **FLIPPED-RED**: `"counter write outside the monotonic increment: tickValue = 0"` (and `frameValue = 0`) |
| AC-006 | 54-68 ns was a measurement, not a gate | explicit alarm margin below the spec budget in `emission_cost_budget` (758+) | **F2** rewrite the manifest extras to `percent_of_tick=4.9`, `producer_ns_per_event=1361.11` | **FLIPPED-RED**: `"level-2 emission 4.9 % exceeds the 0.5 % alarm margin (spec budget 5 %)"` — the gate now bites *before* the spec ceiling. My own run measured 63.4 ns / 0.0228 %, inside the reported band |
| R-1 | four SpriteKit-bound files were parsed/compiled by nothing, while `test-plan.md` claimed a parse gate | new `touched_swift_files_parse_clean` (1548): `swiftc -frontend -parse` over `touched_swift_files()` (1521: git-diff ∪ untracked ∪ a fixed baseline, so committed-mode CI still covers them), a `required` floor that reddens if the set shrinks, and an injected-garbage control | **X3** garbage in `GameScene.swift`; **X4** garbage in `AppDelegate.swift` (not the file their control corrupts); **X6** hide a required file (`LauncherBonusState.swift`); **full suite** while all four SpriteKit files carry 15 real parse errors | X3/X4/X6 **FLIPPED-RED** with the offending file:line; broken-tree full suite → **`RESULT: FAIL (27/28 checks passed)`, exit 1**, the only red being the parse gate; green again after restore. `test-plan.md:51-53` now states the honest residual: `-frontend -parse` is not typecheck |
| R-8 | the checker rewrote `evidence/harness/last-run.txt` inside the tree on every run, so concurrent reviewers staled each other's receipts | transcript now goes to `ARTIFACTS/last-run.txt`; the in-tree copy happens only under `--record` (1926, 1953) through `_write_if_changed` (153-160), via `run_artifacts(…, record_to_tree)` (1871-1884) | recomputed `adaptive_grok.util.tree_fingerprint(root)` before and after my own self-building run in the **real** tree; and ran `--record` once in `/tmp/sh2` | real tree: fingerprint **unchanged** by my run (`9e2f0eab…` both before and after) → default mode no longer moves the receipt; shadow `--record`: file rewritten (mtime 23:21:41, new md5) → the opt-in works |
| R-9 | SIG rows had no evidence binding in the spec | documented as a schema limitation, symbols created (`frame_step_budget` for SIG-003, `session_signal_health` for SIG-001, `kill_switch_no_file` for SIG-002), no spec row weakened | diffed `change-spec.yaml` against the copy I reviewed (`/tmp/shadow/…`, byte-identical → **zero** AC/INV/FORBID wording or evidence edits); read `schemas/change-spec.schema.json` (`$id: urn:adaptive-grok:change-spec:v2`): `observability.items` is `additionalProperties: false` with only `id/metric/proves`, and `evidence[]` exists only under `$defs/criterion`, `invariants` and `forbidden_outcomes` → the claim is **true**, it is a factory-contract gap; re-resolved all 19 bound symbols (0 unresolved) | closed as far as this change can; the residual (9 of 28 checks unbound at receipt level) is the schema's, and is documented in `tasks.md:131` |
| R-10 | `.asynchronous` (the shipped Debug posture) was never executed | new `async_writer_healthy` (1769) + `async_writer` scenario: queue + drain timer + real file writer at level 2 | **d8** manifest lie `dropped=17`; **d9** delete every `player.motion` from the async stream | d8 **FLIPPED-RED** `"the asynchronous drain dropped 17 level-2 records"`; d9 **FLIPPED-RED** `"async stream carries 0 of 15600 motions - the flush barrier left records in the ring"` **and** `stream_invariants` reddened independently. Pristine extras: `motions=15600, dropped=0, ticks=1300` |
| R-11 | component whitelist was ahead of the frozen schema | `COMPONENT_RULES` table (398) keyed by the ids the schema declares + a coverage clause requiring the table and the schema's `x-code-tables` to agree | read + my earlier **C13** (component deleted) and **C11** (component value drift) still redden through the new table path | forward-compatible: an undeclared component id reddens rather than being waved through |

## 2. Falsifiability of the code I did *not* ask them to change (newest, least-reviewed paths)

| Control | Target | Result |
| --- | --- | --- |
| E1 plant a `log.events_dropped{count:9}` inside `session-level2` | `session_signal_health` (SIG-001, now reads all 3 level-2 streams) | FLIPPED-RED `"level-2 session reports drops"` |
| E2 widen a heartbeat gap to 700 ticks in the 600 s `p1-8-fixed` stream | `session_signal_health` | FLIPPED-RED `"heartbeat gap 700 ticks (11.67 s) > 10.5 s"` — my original gap note (SIG-001 evaluated on a 21.6 s stream) is gone: the check now takes the 35 999-tick stream too |
| E4 point a drop record's `first_seq` at a seq absent from the file | `drops_are_counted` + `stream_invariants` | both FLIPPED-RED (`"drop record names first_seq 999999, absent from the stream"`) |
| E5 invert a drop bracket (`last_seq` > `first_seq`) | same | both FLIPPED-RED (`"drop record brackets [302..300] - empty or inverted"`) |
| F3 bump one expectation value in `lane-roundtrip.tsv` | `lane_round_trip_is_exact` | FLIPPED-RED `"player.motion.x: wire '1201' != packed input '1202'"` |
| F4 delete the `entity.launcher_fire` row from that table | `lane_round_trip_is_exact` coverage clause | FLIPPED-RED `"lane table does not cover: ['entity.launcher_fire', 'tick.heartbeat']"` |
| X5 add a raw `events.emit(.playerMotion, entity: 0, …)` to `GameScene.swift` | `producer_sites_use_helpers_only` | FLIPPED-RED `"a raw lane-tuple emit call (use the named producer helper)"` |
| C8/C9-style repeat: 15 extra `player.motion` into one frame (16 total) | new `frame_step_budget` (SIG-003) | FLIPPED-RED `"frames over the 15-step budget {1300: 16}"` — SIG-003 now has its own symbol, as my §1 table asked |

Totals for this pass: **21 controls, 21 red, 0 still-green.** The revert knobs are unchanged in nature
and still flip in the predicates: `revert-p1-9` = 17 motion records with 14 post-transition steps in
frame 2 (predicate A red for the "simulated step(s) ran in the new zone" reason, zero
`tick.accumulator_reset`), `revert-p1-8` = 749 awards / 0 witnesses (predicate B red through the
double-award and >5-per-playthrough clauses — note the new trigger **equality holds** there at
749 == 749, so the silence clause is not what reddens the reverted stream; that is correct, since the
defect there is repeated *awards*, not missing witnesses).

## 3. Counts I re-derived from the artifacts rather than trusting any report

| Quantity | Value from my own count | Matches the checker's PASS line? |
| --- | --- | --- |
| `fixed/p1-8-fixed` stage-end triggers / awards / witnesses | 749 / 1 / 748 | yes ("1 award(s) + 748 suppression witnesses") |
| `revert-p1-8` triggers / awards / witnesses | 749 / 749 / 0 | yes ("749 awards, 0 witnesses") |
| `fixed/session-level2` motions / distinct ticks / manifest `ticks=` | 1298 / 1298 / 1298 | yes |
| `fixed/p1-6-fixed` fires total / after the zone-load block | 40 / 20 | yes |
| `fixed/async` motions / dropped / ticks | 15 600 / 0 / 1300 | yes |
| hot-path cost, three variants in one self-build | 63.4 ns/event = 0.0228 % (author band 54-68 ns) | inside the band |
| streams and records seen by INV-001 / envelope sweep | 39 streams, 179 671 records | yes |

## 4. Did anything get *weakened* to make the green easier?

No. Three specific probes:
1. `change-spec.yaml` is byte-identical to the version I reviewed — no AC/INV/FORBID sentence or
   evidence row was reworded or dropped.
2. Every assertion I re-tested got **stricter**, not looser: an inequality (`>`) became an equality,
   a self-reported flag became a positional predicate, a 2-frame grep became 4 frames, a
   0.5–1000 ns band gained a 0.5 % time budget, `stream_invariants` gained completeness.
3. `FORBID-001` (`forbid_double_stage_bonus`) still stays green in my strip-the-witnesses case (d5).
   That is **correct scoping**, not a hole: FORBID-001's sentence is "awarded twice for one
   completed_zone", the silence clause belongs to AC-003, and AC-003 does redden. Stated here so it is
   not re-reported as a finding in the next round.

## 5. Residuals worth the record (none blocking)

1. **No typecheck of the four SpriteKit-bound files** — `swiftc -frontend -parse` catches syntax, not
   types, link or arity-with-signature drift; the checker's own docstring says so and
   `test-plan.md:51-53` now states it as the accepted residual. The compensating gate is the macOS
   `xcodebuild` that `release.md:21-22` already lists as outstanding; a type error in `GameScene.swift`
   can therefore still be *pushed*, but not *merged* (the App-owned exact-SHA check plus the human
   gate stand in front of that). This is the single biggest thing the Linux net cannot see.
2. **AC-001's clause is now an equality** (`motion == declared_ticks`), stricter than "at least one"
   per the AC-001 sentence. Safe today; if a later wave legitimately emits two motions in one step the
   check turns falsely red. Direction: `motion >= declared_ticks and distinct == declared_ticks`.
   Also the denominator is harness self-reported (`manifest.json → ticks=`); it is not a soft spot in
   practice (a smaller `ticks=` collides with `log.end.events` in `_seq_problems`, and d2 shows the
   observed values still have to match), but cross-checking it against the last heartbeat's tick would
   remove the self-reference entirely.
3. **The 23:06:32Z verification receipt is stale right now, for an unrelated reason.** I recomputed
   `adaptive_grok.util.tree_fingerprint` (the real implementation — `scripts/_grok_audit.py` does not
   exist; `scripts/grok_artifacts.py:27` imports it from `.grok-stack/adaptive_grok/util.py`, and
   `scripts/grok_verify.py` reaches it through that module):
   - recorded `tree_fingerprint` = `9e2f0eabb7407c40cf577a6802eebf8499b3c4ffd25604907ff7230509917a39`,
     `criterion_ids` = AC-001..AC-005 — which is exactly the set of spec rows carrying
     `{"receipt": "verification"}`, so the list is right, not short;
   - my recomputation matched **byte-for-byte** at the start of this pass (41 files, HEAD `295690b`);
   - as of ~23:35 it computes to `ae7632aaf61eab9354ad4302cb3ab81ec9fbe6e4e56a14705fb25c7338641b32`,
     because two untracked files belonging to a **different** package
     (`…20260921-close-audit-finding-p1-11…/evidence/review-release_reviewer.md` and
     `review-security_reviewer.md`) were deleted after the receipt landed. 39 of the 41 hashed entries
     are unchanged; no file of this change was edited since.
   Action for whoever closes the wave: re-run `python3 scripts/grok_verify.py --mode pr` **after** the
   review writers (including this file) settle, since every reviewer's report is inside the fingerprint
   set by design.
4. **`touched_swift_files()` baseline is wave-A-specific.** In committed mode (`git diff HEAD` empty on
   a fresh clone of the merge), the union collapses to the fixed 13-file baseline; a *future* wave's new
   SpriteKit-bound file escapes the parse gate unless its author extends `SPRITEKIT_BOUND`/the baseline.
   The `required` floor makes today's set safe (X6 proves it bites). Worth a line in the factory's
   change-template so the next wave cannot forget.
5. **In-tree `evidence/harness/last-run.txt`** (mtime 23:02:23, 13 scenarios, current harness shape) is
   refreshed only under `--record`, and it is structurally in sync with the shipped checker. Note the
   hot path moved up inside the reported band: the in-tree transcript measures 64.1-64.5 ns/event and
   mine 63.3-64.3 ns (0.0228-0.0232 % of a tick), against 54.1/55.4/65.3 ns in the pre-fix-round
   transcript — still well inside both the 54-68 ns band of `tasks.md:58` and AC-006's budget, but the
   hot path sits ~10 ns/event higher than the pre-fix-round runs (I did not attribute a cause; the
   delta between rounds changed both the emitters and the scenarios), so the band's floor is no longer
   observed. Don't read the in-tree file as *this* run's transcript.

## 6. Must-fix list for the test story

**None from the previous round.** Open items, ordered, none of which is a checker defect:

1. Record the macOS `xcodebuild` output for the shared scheme in the PR (already required by
   `release.md:21-22`) — it is the only gate over the four parse-only files.
2. Re-run `python3 scripts/grok_verify.py --mode pr` after all review reports land, so the
   verification receipt binds the final fingerprint (the current one binds `9e2f0eab…`, the tree is
   `ae7632aa…`).
3. Optional, small, in `gameplay_log_check.py`: AC-001 `>=` instead of `==` (§5.2), and derive the
   parse set's SpriteKit half from the diff alone with the baseline as a floor only (§5.4).

Everything else in `evidence/review-test.md` is closed with evidence above; the wave-A fixes
themselves (P1-9, P1-4, P1-8, P1-6) remain genuinely gated, and this time the gates demonstrably
fail when the properties are broken.
