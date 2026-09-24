# Delta re-review — wave A gameplay event log (lane-map closure + writer/rotation controls)

Route agent: `code_reviewer` (delta scope) · change `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c`
Reviewed bytes: working tree at HEAD `fa1b5ad` with the uncommitted change on top
(product diffstat unchanged all session: `699 insertions / 113 deletions` over 10 tracked files,
`Exolon/GameCore/Diagnostics/` = 2 719 lines).
Method: current bytes only — no reliance on the writer's prose, no reliance on my own first-pass
notes. Every claim below is either read off the files with a line number, read off a gate artifact
produced by my own run, or produced by a mutation I applied to a **/tmp shadow copy**.
Real-tree writes by this review: this file only.

## Verdict for the delta scope

**PASS.** All four Critical wire lies (R1-1..R1-4) and both Mediums (R2-1 drop bracket, R2-2 rotate
placement) are closed in the current bytes, each closed by a control that I independently reddened;
the flush-barrier claim is true and I broke it to prove the guard bites; none of my original findings
was invalidated. Two non-blocking items and one housekeeping fact are listed in §5-§7.

---

## 1. Structural change verified (this is what actually closed the class)

The lane map moved into compiled product code, and the gate now compiles that file:

* 41 named producer functions in `Exolon/GameCore/Diagnostics/GameplayEventSink.swift:473-736`
  (`extension GameplayEventSink`) own **43 wire kinds** — one function per name, except
  `emitCrouchEdge` (`player.crouch_begin`/`_end`) and `emitPauseChanged` (`state.pause_enter`/`_exit`).
  So "43 lane maps" is exact: 43 maps in 41 functions, `tick.heartbeat` being the 44th
  producer-reachable kind and composed inside `beginTick` rather than by a helper. Counts read off
  the checker's own parser: `_producer_helpers()` → 43 kinds / 41 distinct helpers,
  `wire_reachable_names()` → 44, unowned → `[]` (`GameplayEventLog.swift`/`gameplay_log_check.py:1587-1612`).
* `GameplayEventSink.swift` is in the Linux harness compile list
  (`evidence/harness/run.sh:35-45`) — so the helpers are the **same code the product calls**, which is
  precisely what my first pass said was missing.
* Zero raw lane arithmetic left in the 5 producer files (verified independently: the only
  `GameplayEvent.*` reference in `GameScene`/`Player`/`TMXLevelRuntime`/`LevelObstacles`/
  `FixedTickDriver` is `GameplayEvent.microseconds(fromSteps:)` at `GameScene.swift:1222`, a unit
  conversion feeding a semantic argument, not a lane write).
* `lane_round_trip_is_exact` drives **49 records across 45 names** from those helpers and compares
  every field against `lane-roundtrip.tsv`, whose expectations are hand-written literals in
  `evidence/harness/main.swift:827-1010` — not recomputed from the encoder. I re-derived the literals
  myself and they are genuinely independent oracles: `x=2043` for position 510.75 px (`510.75×4`),
  `delay_us=1166667` for 70 steps (`round(70e6/60)`), `invulnerability_us=400000` for 24 steps,
  `points_after=999999 clamped=true` for `995000+9000`, `next_level=""` for the no-successor case,
  `resource=L05S25` for zone 124, `accumulator_us=233333 pending_steps=14`. A swapped lane, a shifted
  bit, a misread i32 pair or a wrong derivation each fail on their own field.

## 2. My four originals — closed, with current-byte evidence

| finding | current code | wire evidence (my run) |
| --- | --- | --- |
| **R1-1** `damage.player_hit` packed lane passed in `a` | helper `GameplayEventSink.swift:586-594` passes `x, y, lane, lives`; formatter `GameplayEventLog.swift:1024-1030` reads `x=a`, `y=b`, pack from `c` | `{"name":"damage.player_hit","cause":"missile","x":2043,"y":800,"flow_state_before":"playing","flow_state_after":"playerDead","lives":2}` |
| **R1-2** formatter decoded `blocked` from the entity lane | formatter `GameplayEventLog.swift:1017-1023` now decodes `record.c` (comment names the reason); helper `:580-583` packs into `c` per `x-encode` | `{"name":"damage.player_blocked","cause":"force_field","invulnerability_us":321000,"test_invulnerability":true}` — the cause and the cheat flag are now observable |
| **R1-3** 17-bit `checkpoint` pack / lives read one bit high | `GameplayPack.checkpoint` `:347-351` = ammo 0-6, grenades `&0b11111 << 7` (5 bits, 7-11), lives `<< 12` (12-15) = 16 bits exactly; formatter `:1106-1111` reads the same three offsets; `schemas[38]` **and** the schema annotation now both say `entity=pack(ammo:0..6,grenades:7..11,lives:12..15)` | `{"name":"state.checkpoint_saved","resource":"L05S25","ammo":99,"grenades":10,"points":456789,"lives":3}` |
| **R1-4** extra zone lane shifted `state.restart`'s i32 | `emitRunRestarted(discardedPoints:)` `:701-705` emits `emit(.stateRestart, split.0, split.1)`; `from_zone` comes from the record zone lane as `x-encode` declares; call site `GameScene.swift:1127` passes only the points | `{"name":"state.restart","from_zone":124,"points":123456}` |

Three-way map agreement (schema `x-encode` ↔ `GameplayEventKind.schemas` ↔ helper ↔ formatter) holds
for the 14 names I audited mechanically: 5, 17, 20, 22, 23, 25, 29, 32, 33, 34, 35, 38, 42, 48 —
**0 mismatches**, including `state.zone_load`, whose stale `a = cause code` annotation from my
first pass was corrected to `entity=cause`. The whole 48-name catalog carries a block-level
`x-encode`, and the schema contains **no** `"None"` or `null` remnants of the contract-sync accident
the writer logged in `mistakes.md` (grep: 0 occurrences).

## 3. Mutation controls I ran (shadow copies under `/tmp`, real tree untouched)

Shadow root `/tmp/exsh` mirrors the repo depth `run.sh` and the checker expect; its baseline run
passed **28/28**, so every failure below is attributable to my mutation, not to the harness.
Afterwards `diff -rq /tmp/exsh/Exolon <real>/Exolon` reported no difference (all mutants reverted).

| mutant | what I broke (reproduction of my original finding) | result |
| --- | --- | --- |
| **A** = R1-1 | `emitPlayerHit` re-aliased so the packed lane goes into `a` | `FAIL lane_round_trip_is_exact: damage.player_hit.cause: wire 'unknown32' != packed input 'missile'; .x: wire '1607' != '2043'; .y: wire '2043' != '800'; .flow_state_before: wire 'respawning' != 'playing'; .flow_state_after: wire 'playing' != 'playerDead'` — and **two further checks reddened on their own**: `envelope_schema_valid` (`'unknown32' not in the frozen enum …`) and `forbid_wallclock_fields` (`cause='unknown32' is not a whitelisted label`) |
| **B** = R1-3 | `GameplayPack.checkpoint` lives shifted `<< 12` → `<< 13` | `FAIL … state.checkpoint_saved.lives: wire '6' != packed input '3'` |
| **E** = R1-4 | `emit(.stateRestart, 7, split.0, split.1)` (extra leading lane) | `FAIL … state.restart.points: wire '458753' != packed input '123456'` (`(7<<16)|1`, exactly the arithmetic my first pass predicted) |
| **C** = the ban | reintroduced `events.emit(.playerMotion, entity: 0, 1, 2, 3, 4)` into `GameScene.emitMotion` | `FAIL producer_sites_use_helpers_only: Exolon/GameCore/GameScene.swift: events.emit( - a raw lane-tuple emit call (use the named producer helper)` |
| **D1** | renamed a helper so no product file calls it | `FAIL producer_sites_use_helpers_only: producer helpers no product file calls (dead lane maps): ['emitStageAwardComponentRenamed']` |
| **D2** | made one helper emit the wrong kind | `FAIL …: kinds with no producer helper: ['bonus.stage_boundary_suppressed']` |
| **F** = the barrier | `flush()` back to a single `drainNow()` instead of `drainEverything()` | the harness itself aborts red: `FAIL the final flush drained the ring: pending=13682`, `FAIL async stream carries every motion: 2048`, `FAIL async stream carries 0 heartbeats (600-tick period)` ⇒ `run.sh` exits non-zero ⇒ gate cannot pass |

Mutants A+B+E were applied together and each was reported separately (the check collects problems per
record), which is why a single rebuild produced three attributed failures. Overall mutated run:
`RESULT: FAIL (25/28 checks passed)` for A+B+E. **Requirement (1) and (2) satisfied: ≥2 original
mutations reproduced, plus the ban demonstrated on a reintroduced raw `events.emit(` in GameScene.**

## 4. The two Mediums — closed, and now mechanically checkable

**R2-1 (drop accounting).** `GameplayEventLog.swift:693-699` emits the record with
`lastRetainedSeq: nextSeq - 1, firstRetainedSeq: nextSeq + 1`, i.e. `log.events_dropped` sits *between*
two records that exist; `:654` claims the loss window only when a batch actually follows
(`let drops = batch > 0 ? droppedSinceDrain : 0`), so the upper neighbour is guaranteed to be written.
The contract now says so: block `x-encode` = "writer-built, emitted in front of the batch it brackets:
last_seq/first_seq name records that exist on both sides of the loss window", plus per-field
`x-note`s. `_drop_bracket_problems` (`gameplay_log_check.py:1124`) asserts the pair is strictly
ordered the other way round, that both seqs are present, and that the drop line's own seq is exactly
between them. Artifact read from my run:
`seq=301 count=4496 first_seq=302 last_seq=300` on a stream whose 815 seqs are contiguous 0..814
(300 and 302 present ✓). Completeness is now arithmetic, not a marker count: `drops_are_counted`
asserts `log.end.events − body == declared` (`:1012`) and `stream_invariants` asserts
"log.end declares N events, the stream carries M records plus L declared drops" (`:1117`), and the
mid-stream scenario reports **5308 declared vs 812 written** ✓ — my requested control (loss witnessed
by real existing seqs) is in place.

**R2-2 (rotation).** `rotateFile` (`GameplayEventLog.swift:762-789`) writes `log.rotate` **before**
`rotateToNextFile()`, using `writer.nextFilePath()` (protocol `:37`, impls `:89` file / `:195` memory)
so `to_path` names the successor without having opened it, then re-arms `fileIsOpen` and writes the
new header. Direct artifact proof from my run:

```
rotation-…-123.jsonl  first: log.begin  seq 4182      last: log.rotate seq 4215 (to …-124.jsonl)
rotation-…-124.jsonl  first: log.begin  seq 4216      last: log.rotate seq 4249 (to …-125.jsonl)
rotation-…-125.jsonl  first: log.begin  seq 4250      last: log.end    seq 4257 (events 4006)
```

Each retired file now ends with its own rotate line, so a consumer holding one file can distinguish
retirement from truncation — exactly what the annotation promises. `rotation_linkage` asserts it.

**Flush barrier (parent item 5).** `flush()` → `drainEverything()` (`:550-561`) loops while
`pending > 0 || droppedSinceDrain > 0`, in both the `.synchronous` and the on-queue/off-queue
asynchronous branches (`:532/:539/:543`), and `shutdown()` (`:566`) calls it before writing `log.end`.
The async scenario uses the production convenience initializer (real file writer + queue + 0.02 s
timer) with `drainBatchEvents = 128` against 15 600 emitted records, so a one-batch barrier can only
fail — and it does (mutant F) ✓.

## 5. New items in their defect list — my assessment

* **S-1 (sink snapshot) — fixed, not deferred.** `GameScene.swift:41` is now
  `private let tickDriver = FixedTickDriver()` (eager, no snapshot of `events`), rebound through
  `events.didSet` → `tickDriver.useSink(events)` (`:35`), with `FixedTickDriver.useSink`
  (`FixedTickDriver.swift:54-56`) documented against the exact failure mode I described
  ("`tick` sticking at 0 in a non-empty file"). ✓
* **Heartbeat drain-time label — fixed at the source.** `appendHeartbeatLocked` stores the flow code
  in the record's own subject lane (`GameplayEventLog.swift:627`) and the formatter reads `subject`
  (`:1141-1143`); both lane maps were updated to `entity=flow_code`. A heartbeat drained after a flow
  change can no longer name the newer state. ✓
* **Constant-by-construction flags — half of them fixed.**
  `player.teleport.jump_latch_held` is now captured *before* the mutation
  (`GameScene.swift:317` `let upHeldThroughTeleport = rawInput.jump`, used at `:320-321`), so the field
  distinguishes "UP physically held" from "not held" — real information, and AC-004's predicate keys on
  it. `input.contextual_consumed.jump_suppressed` remains constant-true by construction: both call
  sites (`:311`, `:323`) pass `rawInput.jump`, and the enclosing branch requires
  `jumpJustPressed` (`:301`), which implies `rawInput.jump`. The helper now takes a `Bool`
  (`GameplayEventSink.swift:489`), so nothing forbids a false value — it is just unreachable today.
  Acceptable as a nit; I recommend the comment at `:312-316` state it, the way
  `emitPausePressConsumed` documents its own always-true `pending` (`:481-485`).

## 6. New findings from this delta pass (neither blocks the delta scope)

* **N-1 (Minor, latent livelock).** `drainEverything()` (`GameplayEventLog.swift:558-561`) has no exit
  path when `isShutDown` is set: `drainNow()` returns at `:647` without claiming `pending` or
  `droppedSinceDrain`, so `hasPendingWork()` (`:550`) stays true forever. The invariant
  `droppedSinceDrain > 0 ⇒ pending > 0` holds (a lap requires a full ring, and every drain with
  `batch > 0` claims the window at `:654`), so the only way to hang is a `flush()` with a non-empty
  ring **after** `shutdown()`. Today that is unreachable — the sole `flush()` call in product code is
  `shutdown()` itself (`:578`), before the flag — but `flush()` is a public protocol method
  (`GameplayEventSink:385`), so any future caller (or a post-termination frame) wedges the drain
  queue. One-line hardening: `while hasPendingWork(), !isShutDown { drainNow() }`, or bound the loop
  by `ring.count / drainBatchEvents + 1` passes and count the rest as drops.
* **N-2 (Nit, boundary of the new controls).** `producer_sites_use_helpers_only` matches literal
  needles, so `let sink = events; sink.emit(.kind, …)`, a renamed sink property, or a raw
  `UInt16(truncatingIfNeeded:)`/`<<` pack in a producer file would slip past the ban; and the
  round-trip proves each **helper** once, not the **choice of arguments** at each product call site.
  I hand-audited that residual surface across the risky sites and found no mismatch: grenade
  blocked/thrown origins and before/after (`GameScene.swift:452-462`), blaster ammo
  (`:438-441`), pickup before/after (`:1234`), `awardPoints` capturing `before` before the mutation
  (`:817-820`), `flowAfter: .playerDead` matching the very next line (`:1289-1291` and `:723`),
  `emitDeathSettled`'s two tick arguments (`:1309-1312`), `emitZoneLoaded`/`emitZoneTransition`
  (`:1252-1265`), `emitCheckpointSaved` field mapping (`:1268-1270`). Worth one macOS-side
  product-call-site test if this log ever becomes a merge gate; the ban's needles are also worth
  widening to `.emit(.` plus the raw `UInt16(truncatingIfNeeded:` spelling.

## 7. Housekeeping fact the receipts depend on

`git rev-parse HEAD` moved **during this delta session**: `fa1b5ad` "docs(evidence): commit orphaned
P1-11 release/security review reports" landed on the branch (2 files, +540 lines; no product file
touched — the working-tree product diffstat is byte-for-byte the same 699/113 I measured at session
start, and `Exolon/…` mtimes are all ≤ 22:29). Because `tree_fingerprint` hashes
`git_head()` first (`.grok-stack/adaptive_grok/util.py:183-199`), the bound verification receipt no
longer matches: recorded `9e2f0eab…` vs current `8064dc76…`. **This is expected drift from the
commit, not a content change and not caused by this review**: my runs never wrote into the tree
(`gameplay_log_check.py` only writes `evidence/harness/last-run.txt` under the explicit `--record`
flag, `:1883`, which I never passed; my shadow copies and every artifact live in `/tmp`), and I
confirmed the fingerprint still matched mid-session before the commit appeared. Action for the
orchestrator: re-run `python3 scripts/grok_verify.py --mode pr` once **all** agents have settled
(`review-test-delta.md` was still being written while I worked), then record this review's receipt
against the new fingerprint — otherwise the same race stales it again.

## 8. Gate result on current bytes (my run)

`RESULT: PASS (28/28 checks passed)` — including the five new controls
(`lane_round_trip_is_exact` 49 records/45 names, `producer_sites_use_helpers_only` 5 files clean +
43 maps all called, `async_writer_healthy` 15 600 motions 0 drops + whole-ring barrier,
`touched_swift_files_parse_clean` 13 files, `frame_step_budget` max 2 steps/frame with the reverted
control breaching), plus the strengthened older ones (`hot_path_is_allocation_free` now covers 4
frames including `beginTick`; `counters_never_reset` catches an injected rewind; `stream_invariants`
fails on truncated, tail-torn **and** gapped copies across 39 streams/179 671 records). All four
wave-A predicates still pass with their reverted controls still flipping (P1-9: 0 steps fixed vs 17
reverted; P1-8: 1 award + 748 witnesses vs 749 awards; P1-4: 1 latch-held teleport, 0 leaks;
P1-6: 1 payout + 40 later shots with `launcher_active_after=true`). `EXOLON_EVENT_LOG=off` still
creates no file, and the README now states the kill switch honestly as **file**-inert, not path-inert
(`README.md:40-41`) — my S-2 closed.

## 9. Disposition of my first-pass findings

| id | item | status |
| --- | --- | --- |
| R1-1..R1-4 | four wire lies | **fixed**, mutation-proven (A/B/E) |
| R2-1 | fabricated drop window | **fixed** — brackets real seqs, contract text updated, completeness arithmetic asserted |
| R2-2 | rotate in the new file | **fixed** — retired file ends in its own rotate (`nextFilePath()`) |
| R2-3 | lane-map authority drift | **fixed** — `x-encode` moved to the machine-readable block key and now agrees with `schemas[]`, helper and formatter (14 names checked, 0 mismatches) |
| §3 | producers uncompiled/replica-only | **fixed** — helpers in a compiled file + `lane_round_trip_is_exact`; residual boundary = N-2 |
| S-1 | lazy driver snapshot | **fixed** (`GameScene.swift:35, 41`) |
| S-2 | README overclaim | **fixed** (`README.md:40-41`) |
| S-3 | teleport latch flag uninformative | **fixed** for `player.teleport`; still constant for `input.contextual_consumed` (§5) |
| S-4 | free-form `log.end.reason`, dead `flowLabel(forCode:)` | **fixed** (`shutdown(reason: GameplayLogEndReason)` at `:566`; alias removed) |
| S-5 | misplaced doc, "14 call sites", duplicated 70/60 literal, `default:` level | **fixed** — `screenExitX`/`deathSettleDelay` named in `GameConstants`, doc says "10 call sites" (`GameScene.swift:814-815`); `minimumLevel` still uses `default: return 1` (nit, unchanged) |
| S-6 | `stats.written` semantics | **fixed** — `stats: (events:, pending:, dropped:)` returns `appendedTotal` (`:295-299`) |
| S-7 | DateFormatter thread comment | **fixed** (`:347`) |
| new | — | N-1 (latent `drainEverything` spin post-shutdown), N-2 (ban/round-trip boundary), §7 (receipt rebind) |

None of my original findings was invalidated by the delta work; all were either fixed or downgraded
with evidence. **Delta scope: PASS.** Recommended follow-ups before the change is offered for merge:
N-1's one-line guard, and a rebind of the verification receipt after every writer has settled.
