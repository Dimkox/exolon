# Rebase verification — wave B onto merged wave A

Change: `20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2`
Tree: `/home/pall/projects/.exolon-wave-b/exolon` @ head `6c7dfe5` (parent = `17a742a` = `origin/main`, the merge of
PR #20 / wave A `2c2ba15`). Pre-rebase head reviewed in `review-code-delta.md` was `84d00c2` on base `295690b`.
Role: `code_reviewer`, READ-ONLY. This file is the only write in the repository.

## FINAL VERDICT: **PASS** — specifically for the rebase/merge. Wave B's semantics survived the auto-merge intact,
both meters are green on the merged bytes, and no wave-A behavior was diluted by wave-B hunks. The receipts may
re-bind on this word.

Two expectations in my brief did **not** reproduce as stated and are reported honestly rather than passed over:
the re-alias mutant still does **not** redden INV-002 (§2, D-2 carried), and the spawn tie-break is still
unprotected — now measured, not inferred (§2, M7). Neither is merge-blocking; both are listed with a bounded
blast radius. One new gate-coverage hole that only exists *because* of the wave union is reported as Rb-1 (§5).

## 0. Method and read-only proof

All mutation experiments and all meter runs executed in throwaway clones under `/tmp/rb/*`. No product or
evidence file in the reviewed tree was touched: `git status --porcelain` was empty for the whole measurement phase,
and the only entries after it are this report and the test reviewer's (both untracked paperwork, no product bytes).

The decisive attribution argument is git itself: the clone `/tmp/rb/exolon` checks out **the same commit**
`6c7dfe5` (`merge-base HEAD origin/main = 17a742a`, matching the real tree) and reports
`git status --porcelain` **empty**, exactly as the real tree does. Two clean working trees over one commit are
byte-identical for every tracked file by construction; I additionally `cmp`-checked the 11 files both meters read
(8 product files + `wave_b_check.py` + `wave_b_harness/main.swift` + `gameplay_log_check.py`) and all matched. So
every number below is a measurement **of this tree**. `swiftc` 6.4 at `/opt/swift/usr/bin/swiftc`, so both
executable legs really compiled and ran.

For completeness, `adaptive_grok.util.tree_fingerprint` (the value receipts bind to) is
`sha256(HEAD ‖ each changed/untracked path + its sha256)` — it is *not* a whole-tree walk. Before I wrote this
report both trees therefore hashed identically
(`af9b2d47f39de0d8384de73c45bc0d254542b9928c98b40c122259f722b320a6` = HEAD `6c7dfe5` + empty dirty set), and after
this report and the test reviewer's landed the real tree hashes to
`38775e73034705778d3650640c659b8545fb375eb4556bb745fe3ac982f923cd` (dirty set = the two `review-*-rebase.md`
files; it moves again on any further write). See §6.

## 1. Wave-B semantics survived the merge — proved at patch level, not spot-checked

**Whole-delta proof.** I extracted wave B's product patch twice — as it stood pre-rebase
(`git diff 295690b 84d00c2 -- Exolon/`, 727 lines) and post-rebase (`git diff 17a742a HEAD -- Exolon/`, 727 lines) —
normalised only the hunk headers and index lines, and compared. **All 8 files are patch-identical**
(`GameConstants`, `Player`, `TMXMapLoader`, `TMXLevelRuntime`, `LevelObstacles`, `TMXTileMapRenderer`,
`BlasterBullet`, `Grenade`): every `+`/`−` line *and* every context line matches, only offsets moved. Stat is
identical (420 insertions / 87 deletions). An auto-merge that had re-flowed, duplicated, dropped or reordered any
wave-B hunk would break this test; it did not.

**Executed proof.** `wave_b_swift.txt` (the compiled-product artifact: spawn feet, piston groundY, `RECTS` 1437,
GEOMETRY) is **byte-identical** between `84d00c2` and `HEAD`, confirming the writer's claim at `tasks.md:208`
independently. Four of the eight product blobs (`TMXMapLoader`, `BlasterBullet`, `Grenade`, `TMXTileMapRenderer`)
are literally the same git objects as pre-rebase; the four that changed did so only because wave A's own lines
arrived.

Per item in the brief, all verified in the merged bytes:

| wave-B semantic | merged location | status |
|---|---|---|
| spawn bounded ±16 + preference rule | `TMXMapLoader.swift:196-217` (`boundedSurfaceY`, `clearBest ?? anyBest`), call site `:112-122` with `halfWindow: CGFloat(tileHeight)`; `TMXLevelRuntime.swift:73-81` | intact; meter `AC-001 matched 119/125 (clear 71 / dirty-nearest 48), kept 6, buried base 61 → after 48`, hard bound `abs(delta) <= 16` enforced at `wave_b_check.py:986` |
| `pistonGroundY` + corrected global-plane comment | `TMXMapLoader.swift:220-238` | intact; the comment is my D-1 correction, and it is factually right: the three shaft spans DO carry cells (tops 160/192 at x=128, 272 at x=400) and none is ≤ `markerBottomY + pistonTravel` = 64, so the query falls to the global `fallbackPlaneY` (lowest cell top = 48) — matches my own recomputation last pass; meter reports `plane-fallback 3` of 46 |
| beam shared pool + `[weak side]` + tie-break | `TMXMapLoader.swift:265-296` (`BeamFieldModel`, one `remainingHitPoints -= 1`), `:299-322` (`TMXBeamGrouping`, `(minX, index)` order), `TMXLevelRuntime.swift:476-491` (`[weak side] in side?.coverDestroyed()`) | intact **and machine-guarded**: meter anchors the weak capture textually (`wave_b_check.py:859-862`, four anchors incl. "no `field.onDestroy =`", "no single-strong-closure", "one decrement site", `a.offset < b.offset` tie-break at `:832`); my strong-capture mutant M6 reddened it (§2) |
| derived cull constants | `GameConstants.swift:41-63` (`blasterCull*`/`grenadeCull*` as expressions over `playerMaximumCenterX`, muzzle/throw, size); consumers `Player.swift:299-313`, `BlasterBullet.swift:45-53`, `Grenade.swift:81-85` | intact; meter regex-pins the *formulas* (`:913-919`), not the numbers → `-50..594` / `-20..564`, and wave A did not move `playerMaximumCenterX` (A's `GameConstants` hunk is `postDeathProtectionDuration` comment + `screenExitX` + `deathSettleDelay`, all disjoint) |

## 2. My mutation set, re-run on the merged tree

| id | mutant (all in `/tmp/rb/*`) | expected | measured | verdict |
|---|---|---|---|---|
| M2 | product `y: run.top - tileHeight` → `+ 7.5` at **both** run-append sites (`TMXMapLoader.swift` `collisionRects`) | INV-002 reddens | rc=**1**; `pinned_geometry_unchanged` FAIL "rects … на 0/125 (всего 0)"; `controls_flip` FAIL | ✅ reproduces my pre-rebase experiment A line-for-line |
| M1 | meter re-alias: comparison-site `new_rects = base_rects` (collapse of the base-vs-new leg) | brief expected INV-002 to redden | rc=**0**; still prints "rects base-порт==new-порт==исполненный на **125/125** (всего 1437)", `pinned_geometry_unchanged` PASS, `controls_flip` PASS | ❌ **does not redden** — D-2 carried, see below |
| M1b | method-level alias of `SurfaceMirror.query_collision_rects` | same | not constructible: the mirror holds no `mp`/gids and the old side is the module function `base_build_collision_rects(mp)`, so the only meaningful alias *is* M1. (My first attempt aliased to a non-existent `old_collision_rects` and died on `AttributeError` — a crash-red, not a semantic red; discarded, not counted.) | n/a |
| M4 | M1 **and** M2 together (bound the blast radius of the alias hole) | still red | rc=**1**, `pinned_geometry_unchanged` FAIL 0/125 | ✅ the shipped-geometry guarantee survives an alias collapse |
| M3 | reintroduce a raw lane emit **on a wave-B line** in a PRODUCER_FILE: `events?.emit(.beamDestroyed, GameplayEvent.lane(0), 0, 0)` inside B's new beam loop (`TMXLevelRuntime.swift:483`) | wave-A `producer_sites_use_helpers_only` fires | **FAIL** rc=1, naming both needles: `TMXLevelRuntime.swift: events?.emit( - a raw lane-tuple emit call` and `GameplayEvent.lane( - hand packing at the call site` | ✅ A's ban still bites inside B's hunk |
| M6 | `[weak side]` → `[side]` in B's beam loop | beam check reddens | rc=**1**, `beam_shared_hp_all_maps` FAIL | ✅ weak capture is enforced, not just present |
| M7 | both product spawn tie-breaks inverted (`top < anyBest!` / `top < clearBest!` → `>`) | — | rc=**0**, 9/9 green | ❌ R1-3 still open, now **measured** on merged bytes |
| M5 | meter `wave_base()` forced back to the pre-rebase base `295690b` (control for the attribution fix) | — | rc=**0**, but the scan swells to **2731 code lines in 16 files** (wave A absorbed into wave B's scope) vs the true **237 / 8** | ⚠ reproduces the writer's own figure at `tasks.md:213`; the fix is correct but nothing *detects* a wrong base (`n_files >= 7 and n_code >= 150` is a lower bound only) |
| C1/C2 | committed syntax garbage (`func … ((( {`) appended to `BlasterBullet.swift` (C1) vs `LevelObstacles.swift` (C2), tree left clean so A's parse set is what a real review would see | — | C1: A's `touched_swift_files_parse_clean` **PASS** *and* wave-B meter **PASS** (rc=0). C2 (control): **FAIL** with the exact compiler error | 🔴 new finding Rb-1 (§5); the control flips, so the gate works — it just does not cover B's files |

**Interference check (explicitly requested).** Static: I scanned all 395 of wave B's added lines (comments
included) against all seven of A's forbidden needles — `events.emit(`, `events?.emit(`, `GameplayPack.`,
`GameplayEvent.lane(`, `GameplayEvent.split(`, `GameplayEvent.q(`, `Int16(truncatingIfNeeded` → **zero matches**.
A's own check confirms it dynamically on the merged tree ("5 producer files carry zero lane arithmetic; all 43 lane
maps … called from product code"). So the writer's "only a doc-comment word matched" is, for **A's** bans, an
understatement: nothing matched, not even in a comment. The claim *is* accurate for **B's own** FORBID-001 literals:
the only lines containing `±16 / 528 / 544 / 560` are 5 comment lines (`GameConstants.swift` "re-pins the old 528",
`TMXLevelRuntime.swift` "0/+16/−16 px", `TMXMapLoader.swift` "/// … 0/+16/−16 px", `BlasterBullet.swift`
"x>528 while the player can stand to x=544", `Grenade.swift` "(544 + 4 = 548)"), all removed by `strip_comments`
before the scan — verified line by line. Cross-wave reverse direction also clean: no wave-A line trips wave-B's
FORBID-001 (M5 shows the scan goes green even when A's 2494 extra lines are wrongly counted as B's).

## 3. Both meters, run by me on this tree

* `wave_b_check.py` → **rc=0, 9/9 `PASS`**, `RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC`, `артефакт Swift: живой
  (совпал: True)`, `elapsed=2.9s` (budget 60 s). PASS-line set is **identical** to the committed
  `wave_b_check_green.txt` (which is itself labelled post-rebase on `17a742a`/`e520884` and already declares the old
  receipt `a5ad67be5a…` invalid).
* `gameplay_log_check.py` (wave A) → **rc=0, `RESULT: PASS (28/28 checks passed)`**, harness rebuilt from this
  tree's sources. Its Linux harness compiles and runs `GameConstants.swift`, `InputState.swift`, `GameState.swift`
  and **`Player.swift`** — i.e. wave B's clamp/inset/muzzle/throw edits were *executed* inside wave A's scenario set
  (1298 motion records, 0 drops). This is the strongest available cross-wave evidence: 28 A-side checks green over
  B-touched product code.
* Both meters write only under their own clone in my runs; the reviewed tree stayed clean.

## 4. Wave A not diluted by wave B

* **Launcher payout (P1-6 / AC-005).** A's rewrite of `DoubleLauncherObstacle` (`bonusState`, `entityID`,
  `isActive { bonusState.canFire }`, `collectBonusIfTouched` → `payBonus`) lives at `LevelObstacles.swift:682-740`;
  B's only hunks in that file are `PistonHazard` (`:326`) and `ForceFieldBarrier` (`:776`). `p1_6_stream_predicate`
  and `forbid_double_stage_bonus` PASS on the merged tree ("1 payout naming object 41, 40 later shots with
  `launcher_active_after=true`, 20 after a zone load; the pre-fix control fails predicate D").
* **Entity ordinals** — the join key of `bonus.double_launcher` ↔ `entity.launcher_fire` — are still allocated
  unconditionally once per object: B inserted `var beamBoxes` *before* the loop and moved field construction *after*
  it, leaving `let entityID = nextEntityID; nextEntityID &+= 1` untouched (`git show 17a742a:…` vs merged, diffed
  side by side). A's witness semantics preserved.
* **Jump latch (P1-4 / AC-004).** A's `contextHoldsJumpLatch` block and B's named-constant clamp now sit in the same
  `Player.update` (merged `:124-153`), disjoint statements, no reordering; `p1_4_stream_predicate` PASS ("1 teleport
  with the latch held, 1 legitimate jump after a release edge, 0 leaks"). A's `emitJump`/`emitLand`/
  `emitCrouchEdge` producers are all still present and still called (A's dead-lane-map clause passed).
* **P1-8 / P1-9** PASS unchanged (`1 award + 748 suppressions` vs `749 awards` reverted; `0 steps after
  transition`, reverted 14-step leak). A's source-level bans still hold over B's files: no
  `resetAccumulatorOnZoneTransition: false` and no self-owned accumulator in any of the three pinned products.
* A's event contract declares **no** beam/force-field kind at all (`grep -i 'force_?field|beam'` over A's
  spec/evidence → 0 hits), so B's beam-pool rewrite cannot falsify any A witness. The one shared consumer,
  `GameScene.swift:503-506` (`awardPoints(1_000, reason: .forceField)` on `destroyed == true`), now fires once per
  **beam** instead of once per **side** — which is wave B's declared intent (and restores the documented 1000-point
  single award), not a dilution of A.

## 5. Findings

| id | sev | conf | file:line | summary |
|---|---|---|---|---|
| Rb-1 | Suggestion | high | `engineering/changes/…32f59c/evidence/gameplay_log_check.py:1532-1541` (set) + `wave_b_check.py` (harness scope) | Merge-created coverage hole: wave A's parse set is sized to **wave A's** 13 files (`SPRITEKIT_BOUND` + hardcoded baseline, because on a clean tree `git diff --name-only HEAD` is empty), and wave B's harness compiles only `GameConstants` + `TMXMapLoader`. Three files wave B rewrote — `TMXTileMapRenderer.swift`, `BlasterBullet.swift`, `Grenade.swift` — are therefore syntax/type-checked by **neither** meter. Measured: committed syntax garbage in `BlasterBullet.swift` leaves both meters green (C1), while the same injection in `LevelObstacles.swift` reddens A's gate (C2). A's "control: injected garbage rejected" cannot see this because it injects into an already-listed file. Cheapest fix: append wave B's SpriteKit-bound files to A's `baseline` list (or add one `swiftc -parse` leg to `wave_b_check.py`). Not merge-blocking: the Xcode/macOS release build is the real compiler, and every numeric claim about those files was verified textually and by the executed legs. |
| D-2 (carried, **unmet expectation**) | Suggestion | high | `wave_b_check.py:1250-1262` | My brief asked "re-alias `query_collision_rects` → INV-002 must redden". On the merged tree it still does **not** (M1: rc=0, and the footer keeps asserting three-way agreement `125/125` although only two legs remain). Nothing in the tree, the amend, or the N-list claims this was hardened, so this is not a regression — it is my open item reproduced on new bytes. Blast radius bounded by M4: with the alias in place, a product geometry defect still reddens (rc=1, 0/125) via the executed leg + the 1437 pin. |
| R1-3 (carried, now measured) | Suggestion | high | `TMXMapLoader.swift:209`, `:214`; `wave_b_check.py:749` | The spawn lower-Y tie-break is exercised by 0/125 maps and has no synthetic fixture: inverting **both** tie comparisons in the product leaves wave B 9/9 green (M7). §4b's mutant battery covers only the rect leg; §1c's fixture covers preference-vs-nearest, not ties. Behaviourally inert on the shipped corpus (uniform 16 px tiles, no equidistant pair), so non-blocking. |
| R1-4 remainder | Nice to have | high | `change-spec.yaml:5` | AC-001 still reads "within one **half-tile** (+/-16 px)" while the code passes `halfWindow = CGFloat(tileHeight)` = one full tile. The *number* is right and machine-enforced (`abs(delta) <= 16`); only the word "half-tile" mislabels it. One-word spec edit: "one tile". |
| Rb-2 | Nice to have | medium | `wave_b_check.py:1127-1146` | `no_magic_offsets` cannot detect a wrong base: forcing `wave_base()` back to `295690b` still returns rc=0 with 2731 "added" lines in 16 files (M5). The rebase fix itself is correct and its output matches the writer's documented figure; adding an upper bound (`n_files == 8`, or `n_code` within a band) would make a future mis-attribution visible instead of silently diluting FORBID-001's scope. |

Carried and unchanged in status: **R1-2** (piston retracted sprite, deferred to a human macOS play-check),
**R1-5** (`beamFields` is a deliberately documented unread registry; the four weak-capture anchors now guard it
better than before), **R1-6** (closed), **D-1** (closed — the corrected comment is present and I re-derived its
numbers), **D-3** (closed via N-5; the post-rebase green transcript header now states the battery count and that the
ablation log is pre-rebase with a byte-identical artifact).

## 6. Receipts

`code_review.json` / `test_review.json` / `verification.json` under `.grok-stack/runtime/receipts/35bac25f12ae/`
carry `tree_fingerprint = 239356b054…` (recorded 22:31:57Z, i.e. the pre-rebase `84d00c2` content). The current tree
is `af9b2d47f39de0d8…`, so **all three are stale and must be re-recorded** with
`python3 scripts/grok_verify.py --mode pr` *after* every reviewer in this wave has settled — this file will itself
move the fingerprint. (This also settles the `9491fdcaa2…` oddity from `review-code-delta.md §6`: the committed
`wave_b_check_green.txt` header names `a5ad67be5a…` as the superseded pre-rebase fingerprint; neither identifier is
the current one.) Note `route.json`/`.grok-stack/runtime/active-route.json` still record
`base_commit = 295690b…`; that is now the wave-A-parent-of-parent, not the rebase base — worth refreshing in the
route/state paperwork so the PR body does not quote a stale base, but it is runtime metadata, not merge authority
(the App-owned policy-epoch check on `6c7dfe5` is).

### Closing note
The merge is clean in the strictest sense I could measure: wave B's patch is byte-for-byte the patch I already
approved in all eight files, the compiled-product artifact did not move by a single byte, both meters are green on
these exact bytes in a clone carrying the identical tree fingerprint, and wave A's own 28 checks pass *over* wave B's
edited `Player.swift`/`GameConstants.swift` with the launcher, latch, ledger and accumulator witnesses intact. My one
open expectation (the alias collapse) is reproduced, bounded and re-listed. **Rebase scope: PASS.**
