# P1-7 «Часть контента уровней не читается кодом вовсе» — re-measurement and fix design

- HEAD: `d4c7a58`, branch `codex/release-layer-p1-11-20260921`, host Linux, read-only pass.
- Authority: `engineering/reports/exolon-full-audit-20260920-v3.md` §1 row P1-7 (line 32) and §6 (line 129).
- Matcher under audit: `Exolon/GameCore/Levels/TMXLevelRuntime.swift`, `case "source_marker":` at **line 351**,
  the seven `source.contains(...)` tests at **lines 356, 361, 366, 369, 371, 380, 394**, chain closed at
  **line 407**, `default:` at **line 409**. Citation `TMXLevelRuntime.swift:351-407` in the audit is exact.
- Method: `xml.etree` only. Layer data decoded with the loader's own semantics (`TMXMapLoader.swift:305-343`:
  `base64` → little-endian `uint32`, `csv` → split on `,`/`\n`/`\r`/`\t`/space, `compression` must be empty).
  All 125 Collision layers decoded, 0 length mismatches.

## 1. Re-measurement — the audit's counts hold at this HEAD

**Source dir used: `/home/pall/projects/exolon/Exolon/Resources` — 125 `.tmx`.** (127 `.tmx` exist in the
tree; the other 17 live under `engineering/changes/20260919-.../evidence/harness/fixtures/` and are
deliberately malformed loader fixtures, excluded.) Object layers: `Objects` in 119 maps, `Object Layer 1`
in 6 legacy maps.

| Audit claim (v3 §1 line 32) | Measured | Holds |
| --- | --- | --- |
| 127 `source_marker` of 680 objects | 127 / 680 | ✅ |
| 7 matcher substrings cover 76 | 76 | ✅ |
| 51 lost on 32 maps | 51 on 32 maps | ✅ |
| `blk_waggon` 24 | 24 (14 maps) | ✅ |
| `blk_gunMachine_BOTTOM` 18 | 18 (15 maps) | ✅ |
| `blk_mushroom` 9 | 9 (6 maps) | ✅ |
| control: drop `beam_` ⇒ loss 71 | 71 on 42 maps | ✅ |
| control: drop all 7 ⇒ loss | 127 on 63 maps | (new) |

No `sourceBlock` value matches two substrings, so branch order currently cannot shadow a family.

### Full census — every distinct object `name` (the `type` attribute is empty on 680/680 objects)

`127 source_marker · 125 vitorc · 70 teleport · 53 mine · 48 ammo_pack · 46 piston · 38 grenade_pack ·
37 turret · 31 bubble_creator · 29 rocket · 22 incubator · 19 double_launcher · 12 radar · 7 ship ·
6 gate · 3 light_ceiling · 3 light_floor · 2 ship_fire · 1 capsule · 1 cocoon` = 680.

### Full census — all 11 distinct `sourceBlock` values of `source_marker`, and their true effect

| n | `sourceBlock` | matcher | runtime effect, verified by grep |
| ---: | --- | --- | --- |
| 24 | `blk_waggon` | **none** | silent drop |
| 19 | `blk_blinker` | `blinker` (:366) | `break` — **no-op** |
| 18 | `blk_gunMachine_BOTTOM` | **none** | silent drop |
| 13 | `blk_beacon_base` | `beacon_base` (:380) | live: `missileGuidanceBaseCollisionRects`, read at :108 |
| 13 | `blk_control_beacon` | `control_beacon` (:394) | live: `missileGuidance`, read at :106/169/194 |
| 10 | `blk_beam_down` | `beam_` (:356) | live: `forceFields`, read `GameScene.swift:399,569,1099` |
| 10 | `blk_beam_up` | `beam_` (:356) | live: same |
| 9 | `blk_mushroom` | **none** | silent drop |
| 5 | `blk_stage_end` | `stage_end` (:369) | `stageExitMarkers` appended at :370 and **read nowhere** — write-only |
| 4 | `blk_changing_room` | `changing_room` (:371) | live: `changingRooms`, read `GameScene.swift:234` |
| 2 | `blk_topdown_electro` | `topdown_electro` (:361) | `break` — **no-op** |

**This is the number that must not be mistaken for «three families».** The audit's "51 lost" is only the
*unnamed* residue. Markers that produce **no observable change in the running game** are
`51 + 19 (blinker) + 2 (topdown_electro) + 5 (stage_end) = 77` of 127 — i.e. **61 %**, not 40 %.
Only **50** markers (20 beam + 13 beacon_base + 13 control_beacon + 4 changing_room) reach gameplay, and
the 20 beam markers are themselves the P1-5 defect. 127 = 50 live + 26 no-op/write-only + 51 dropped.

### Defect found in the authority itself

v3 §6 line 129 reads «P1-7 **38** нечитаемых маркеров» while v3 §1 line 32 reads **51**. Measured value is
**51**. §6 carries a stale/incorrect figure. It is not in `v3_measurements.py` (`EXPECTED` has
`markers_lost: 51`), so it is prose drift, not measurement drift. **Flagged, not edited** (read-only pass).

## 2. Per losing family: original semantics, art, current disposition

Provenance note first. `LEVEL_COMPILER_AUDIT.md` was reclassified by the v3 pass as **ASM input, not
shipped data**, and that ruling is honoured below — but it is still the only per-cell record in the tree,
so it is used for **exclusion**, never for **specification**.

- Its per-screen action lists are `x:y:type`. My re-parse (125/125 screens) reproduces the file's own
  header counts byte-exactly: `2=101, 3=37, 4=341, 5=53, 6=70, 7=48, 8=38, 9=48, 10=46, 11=56, 12=5,
  13=13, 14=92, 15=7, 16=5, 17=10`. So the coordinates are trustworthy.
- **It contains no legend for what a type does.** No `.asm` and no generator exist in this repo
  (`find` for `*.asm` → none). The TMX themselves name the external source:
  `zoneSource = rusarh/exolon-esl asm/data_zone_data.asm`; `ORIGINAL_MECHANICS.md:168` names
  `game_init_actions.asm`. Both are outside the tree.
- Two independent corroborations of prior findings: type `3` = 37 = exactly the 37 `turret` objects;
  type `17` = 10 force fields vs **20** `blk_beam_up`/`blk_beam_down` markers — the ASM table itself
  confirms P1-5's double-field defect.

**All three losing families share two measured facts:** every one of the 51 markers sits on a **solid**
Collision cell (`gid = 1`, i.e. `tiles` tileset index 0) — 51/51 — and every one of the 32 maps carrying
them has a full-frame `imagelayer` («Original Static Scenery», present on 120/125 maps; the 5 without it
are `L01S01/02/03/04/07`, none of them a losing map). **So none of them is a visual hole or a collision
hole; all three are already drawn as baked scenery and already block the player.** All 127 markers have
**no `width`/`height`** (0/127) and `x = sourceX*16`, `y = sourceY*16` (127/127) — they are 1-cell point
anchors, which is why every existing branch hard-codes its own footprint.

To size footprints I used a solid-run estimator (maximal solid rectangle from the marker cell) and
**calibrated it against a family the code already documents**: `blk_beacon_base` → **(4, 3) for 13/13**,
matching the comment at `TMXLevelRuntime.swift:381-383` ("four character cells wide and three cells
high"). `blk_control_beacon` → (0,0), consistent with a flying tower over the base. The estimator is
therefore admissible for the losing families.

### `blk_waggon` — 24 markers / 14 maps (`L01S23, L01S24, L02S02, L02S13, L02S24, L03S05, L03S16, L04S01,
L04S04, L04S17, L04S20, L05S02, L05S13, L05S24`)
- Original: **not an action.** 0/24 have an action at their own cell; 0/24 have **any** action of any type
  inside a 6×4 window, and 0 inside the true footprint.
- Footprint: 5×3 solid for 21/24; the other 3 read (10,3) and (15,3) because adjacent waggons touch
  (`L01S23` has markers at x=8 and x=14). Unit block = 5 cells × 3 cells.
- Art: no dedicated asset — `Exolon/Resources` has **no** file matching `waggon|wagon`. Pixels exist only
  inside the baked `zone_NNN_original.png`.
- Disposition today: **silently dropped as an entity, drawn as scenery, already solid.**
- The initial audit's verdict «таблица destroyable не портирована — **недоделка**»
  (`exolon-initial-audit.md:310`, backlog O9 `:348`) is **unsupported** by the only per-cell record in the
  tree: there is no action to port. Making it shootable would be invented behaviour.

### `blk_mushroom` — 9 markers / 6 maps / zones 025, 043, 053, 069, 090, 118
(`L02S01`×2, `L02S19`×1, `L03S04`×2, `L03S20`×1, `L04S16`×2, `L05S19`×1)
- Original: **not an action** — 0/9 at own cell, 0/9 in a 6×4 window.
- Footprint: **(4, 3) for 9/9 — perfectly uniform**, identical shape class to `blk_beacon_base`.
- Art: no asset (`mushroom` matches nothing in `Exolon/Resources`). Drawn only in the baked backdrop.
- Disposition today: **silently dropped as an entity, drawn as scenery, already solid.**
- Two of the nine are on the P1-12 reskin axis: `L02S19` ≡ `L05S19` in collision+objects (different art),
  so 6 maps = 5 distinct structures. Zone 043 is a documented walkthrough checkpoint
  (`ORIGINAL_MECHANICS.md:162`) — the change must be provably behaviour-free.

### `blk_gunMachine_BOTTOM` — 18 markers / 15 maps (`L01S24` zone 023, `L02S08, L02S21, L02S22`×2,
`L03S04, L03S08, L03S12, L03S22, L03S24, L04S04, L04S07, L04S23`×2, `L05S08, L05S21, L05S22`×2)
- Original: this is the **only** losing family with a positive action record — **type 11 at its own cell,
  18/18**. It is also 1:1 per map with `blk_gunMachine_TOP` turrets, at a constant offset
  `(Δx, Δy) = (-1, +2)`; maps with 2 BOTTOMs have exactly 2 TOPs.
- But type 11 has **56** instances in the original and only **18** were exported. The other 38 sit in the
  18 maps that have type-3 actions yet **no** BOTTOM marker, and there they appear as vertical pairs
  (`L01S07 18:17,18:18`; `L01S11 23:15,23:16`; `L01S14 27:17,27:18`; …). So type 11 cannot be identified
  with "the lower barrel of a gun" on in-repo evidence.
- What `ORIGINAL_MECHANICS.md:36-41` documents is the gun machine as one entity (bullet origin at action
  cell X, Y+3; grenade-destroyable; 150 points) — it describes the `turret` that already exists, and says
  nothing about a second lower gun.
- Art: `turret_body.png` / `turret_tube.png` exist and serve the TOP; there is **no** `gunMachine*` asset.
- Footprint: width 4 in 18/18, height 2–4 (the run bleeds into the terrain it stands on).
- Disposition today: **silently dropped as an entity, drawn as scenery, already solid.**
- Verdict: **semantics UNKNOWN — needs the external ASM plus new gameplay code.** Backlog O1
  («18 нижних пушек мертвы», `exolon-initial-audit-backlog.md:26`) overstates what is established: what is
  established is that *a distinct action cell is unimplemented*, not that it is a gun.

## 3. Ranking (this decides scope)

| Tier | Family | n | Why |
| --- | --- | ---: | --- |
| **A — fixable now, no art, no new gameplay code** | `blk_mushroom` | 9 | uniform 4×3, zero actions, art already baked, terrain already solid. The *only* defect is that no code name exists for it. |
| **A** | `blk_waggon` | 24 | same class; one literal away, but carries the merged-run measurement wrinkle (10/15-wide runs) that must be characterised, not guessed. |
| **B — art-free, but each needs a real behaviour decision** | `blk_blinker` 19, `blk_topdown_electro` 2, `blk_stage_end` 5 | 26 | already matched, currently `break`/write-only. Closing them is P1-adjacent work (`RT-05`), not part of P1-7's drop class. |
| **C — needs new gameplay code + external ASM evidence, likely new art** | `blk_gunMachine_BOTTOM` | 18 | only family with a positive action record, and the action type is unidentifiable from the tree. |

## 4. Minimal first vertical slice: `blk_mushroom`, count 0 → 9

Goal: one family readable **end-to-end by executing product code**, and the drop path made structurally
impossible — with zero art, zero new textures, zero behaviour change.

### Why this shape and not a sprite

`DestructibleObstacle.init` (`LevelObstacles.swift:187-197`) **requires** an `imageName`, and
`v3_measurements.py:336-337` fails any texture literal not present as `Exolon/Resources/<name>.png`
(`texture_names_missing_on_disk: 0`, line 75). So any "draw the mushroom properly" slice turns the
committed measurer red (see §6) *and* double-draws over the baked backdrop. The slice must construct an
**observable record, not a visible sprite.**

### Diff shape

**(a) `Exolon/GameCore/Levels/TMXMapLoader.swift`** — append a Foundation-only classifier to the file that
the Linux harness already compiles. This is deliberate: a new `.swift` file costs **4** edits in
`project.pbxproj` (PBXBuildFile ≈:31, PBXFileReference ≈:333, group ≈:698, Sources phase ≈:1374) **and**
breaks the harness invariant "delta = ровно 1 import line" (`run.sh` step 2, `rc=65`). In `TMXMapLoader.swift`
the existing harness picks it up with no `run.sh` change at all.

```swift
/// Every `source_marker.sourceBlock` name the runtime knows about. Adding a TMX
/// marker family without adding a case here is a compile-visible gap: the
/// classifier returns nil and the level runtime records it as unmatched instead
/// of dropping it.
enum TMXSourceMarkerKind: String, CaseIterable {
    case beam, highVoltage, blinker, stageEnd, changingRoom, beaconBase, controlBeacon
    case inertScenery
    // Behaviour is still unknown for this one; see analysis §2.
    case unconfirmed

    static func classify(sourceBlock: String) -> TMXSourceMarkerKind? {
        if sourceBlock.isEmpty { return nil }
        if sourceBlock.contains("beam_") { return .beam }
        ... // the existing six, verbatim order, so P1-5 is untouched
        if sourceBlock.contains("mushroom") { return .inertScenery }
        return nil
    }
}
```
Keeping the seven existing tests in their current order is mandatory — re-ordering `beam_`/`beacon_base`
would silently re-classify data (§1 proves no current value double-matches, so order is free *today*).

**(b) `TMXLevelRuntime.swift:351-407`** — same branches, now driven by the classifier, plus the missing
`else`:

```swift
case "source_marker":
    let source = object.properties["sourceBlock"] ?? ""
    switch TMXSourceMarkerKind.classify(sourceBlock: source) {
    case .beam:            … // verbatim from :356-360
    case .highVoltage:     … // verbatim `break`  :361-365
    case .blinker:         … // verbatim `break`  :366-368
    case .stageEnd:        … // verbatim          :369-370
    case .changingRoom:    … // verbatim          :371-379
    case .beaconBase:      … // verbatim          :380-393
    case .controlBeacon:   … // verbatim          :394-406
    case .inertScenery:
        // blk_mushroom is imported static scenery: already solid in the Collision
        // layer at its own cell and already drawn by the baked Original Static
        // Scenery image layer. The zone table records no action here, so the
        // runtime must not invent behaviour; it only stops dropping the marker.
        inertSceneryMarkers.append(CGRect(x: sx, y: max(0, bottomY - 48), width: 64, height: 48))
    case .unconfirmed?, nil:
        unmatchedSourceMarkers.append(source)   // observable, never silent
    }
```
with `private(set) var inertSceneryMarkers: [CGRect] = []` and
`private(set) var unmatchedSourceMarkers: [String] = []` declared beside the other arrays
(`:28-42`). Footprint 64×48 = the measured uniform 4×3 cells, converted the same way as
`beacon_base` at `:384-391`. Neither array is read by `GameScene` — the slice changes no physics,
no damage, no score, no spawn.

**(c) Linux-measurable assertion.** Extend the existing executable contour
(`.../evidence/harness/main.swift`, which already loads all 125 maps with the **product** loader) to call
`TMXSourceMarkerKind.classify` on every `source_marker` and print per-kind counts plus the residual.
Assertion: `inertScenery == 9`, on exactly `L02S01(2) L02S19(1) L03S04(2) L03S20(1) L04S16(2) L05S19(1)`
= zones 025/043/053/069/090/118, and `unmatched == 42` (= 51 − 9), listed by family. The count goes
**0 → 9** and the residual **51 → 42** in the same run, from real Swift, not a Python replica.

### What must NOT be attempted in the same change

1. `blk_gunMachine_BOTTOM` — its behaviour is unknown in-tree (§2); implementing it now means inventing
   it. Open a separate change that first acquires the `data_zone_data.asm` type-11 routine.
2. `blk_waggon` — same tier, but it carries the 10/15-wide merged runs; land it as its own assertion line
   after the mushroom slice proves the contour.
3. **Any new `SKTexture(imageNamed:)`** or texture literal — turns 4 committed `EXPECTED` entries red
   (§6) and double-draws over shipped art. No new PNG.
4. **Routing these markers into `sourceHazards`** — that array is declared (`TMXLevelRuntime.swift:28`) and
   consumed by a *kill-player* branch (`GameScene.swift:575`) but never appended (P2 `RT-04`). Filling it
   with scenery would make 33 harmless blocks instantly lethal. Verified by grep: 0 appends today.
5. Making the mushroom/waggon shootable, or moving `blinker`/`topdown_electro`/`stage_end` out of no-op —
   those are P1-5/RT-04/ECO work, not P1-7.
6. Editing `LEVEL_COMPILER_AUDIT.md`, `README.md` marketing claims, or `architecture/` (that directory does
   not exist in this tree, although `AGENTS.md` links to it — pre-existing, out of scope here).

## 5. Characterization test: silent drops become impossible

Invariant to hold: **every `sourceBlock` value in the shipped corpus is either claimed by a classifier case
or named in an explicit unhandled list. No third state.**

Implement as a new self-checking measurer in *this* change package
(`evidence/p1_7_measurements.py`, same shape and honesty rules as `v3_measurements.py`), with **three**
probes, each paired with a control that must flip:

1. **Corpus → code.** Parse the 125 maps, collect the distinct `sourceBlock` set (11 today). Parse the
   **real Swift source** `TMXMapLoader.swift` for the classifier's literal table (regex
   `sourceBlock\.contains\("([^"]+)"\)`) — *not* a hand-copied tuple. Fail if
   `corpus_set - claimed_set - declared_unhandled_set != ∅`. Declared-unhandled is a named list in the test
   containing `blk_waggon` and `blk_gunMachine_BOTTOM` with the reason string, so the two open families are
   on the record rather than implied.
   *Control:* append a marker with `sourceBlock="blk_zz_control"` to a temp copy of one map ⇒ the set
   difference becomes non-empty and the test **must** fail listing `blk_zz_control`. If it still passes,
   the probe is decorative — mirror the repo's existing `controls[...]` convention
   (`v3_measurements.py:248`) so an unflippable control forces `rc=1`.
2. **Code → corpus (drift guard).** Assert the parsed literal table equals the classifier's `CaseIterable`
   list, so a case that matches nothing in the corpus is also an error.
   *Control:* delete the `mushroom` literal from a **build copy** ⇒ `inertScenery` must fall 9 → 0 and
   probe 1 must fail. Proves the assertion reads the product file rather than trusting a fixture.
3. **Product execution, not replica.** The harness (`run.sh`) counts come from compiled `TMXMapLoader.swift`;
   the negative control that already exists (build without the CoreGraphics shim must fail, `run.sh`
   step 6) must stay, and the byte-delta check (`sed '2d'` must return the repository file exactly,
   `rc=65`) must still pass after the classifier is added — otherwise the number is not the product's.

Then wire the invariant into the local gate so it runs with `python3 scripts/grok_verify.py --mode pr`,
and record it via `python3 scripts/grok_review.py code_review --status pass --report <path>`.

## 6. Cross-check against the committed `v3_measurements.py`

**Yes, the numbers are hard-encoded — and the answer to "would this fix turn it red" is: not by itself,
and that is itself a defect that must be fixed in the same change.**

Committed file: `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py`.
Status right now at `d4c7a58`: **`RESULT: ALL_V3_MEASUREMENTS_MATCH_REPORT`, rc=0**, all 11 controls OK
(including `markers_probe_flips`). Run read-only; it only prints.

- **Lines 43-48** encode the finding verbatim:
  `43 "markers_total": 127` · `44 "markers_read": 76` · `45 "markers_lost": 51` · `46 "markers_lost_maps": 32` ·
  `47 "markers_lost_kinds": {"blk_waggon": 24, "blk_gunMachine_BOTTOM": 18, "blk_mushroom": 9}` ·
  `48 "markers_control_drop_beam": 71`.
- **Line 89** `HANDLED = ("beam_", "blinker", "changing_room", "stage_end", "beacon_base",
  "control_beacon", "topdown_electro")` — a **hand-copied mirror** of the Swift matcher.
- **Lines 223-248** `marker_split(...)`; verdict at **line 369**
  (`mism = {k: (v, got.get(k)) for k, v in EXPECTED.items() if got.get(k) != v}`), `out["ok"]` at 371,
  `return 0 if out["ok"] else 1` at 389.

Decisive fact: **`v3_measurements.py` never reads `TMXLevelRuntime.swift`.** Its `.swift` reads are at lines
304 (GameConstants), 306-308 (BlasterBullet), 309 (Player), 318 (LevelObstacles), 327 (all-Swift texture
scan), 356 (pbxproj), 359 (L01S04.tmx). So:

- Swift-only fix (add `mushroom` to the matcher) ⇒ TMX data unchanged ⇒ the measurer recomputes
  `lost=51` from its own line-89 tuple ⇒ **stays green and silently goes stale**. The audit's own oracle
  cannot detect the fix it measures. This is the hazard, not a red run.
- Fixing the measurer honestly (parse line 89 out of the product source, or add the substring) ⇒ lines
  44-48 must move to `read 85 / lost 42 / lost_maps 26 / kinds {waggon 24, gunMachine_BOTTOM 18}`,
  and because the docstring at lines 3-8 promises `rc=0 ⇔ цифры совпали с …exolon-full-audit-20260920-v3.md`,
  **the v3 report itself must be amended in the same change** (v3 §1 line 32 and §6 line 129, which is
  already wrong at 38). Renumbering EXPECTED without touching the report breaks the contract the file
  declares about itself.
- The slice as designed in §4 adds **no** texture literal, so lines 331-337 (`texture_sites` 23 @71,
  `texture_literal_names` 17 @72, `texture_computed_sites` 6 @73, `texture_union_names` 21 @74,
  `texture_names_missing_on_disk` 0 @75) stay untouched. Any "make it visible" variant would move 71-74 and
  push 75 to 1 → **rc=1**.
- Two further committed measurers hold the **same matcher copied by hand**:
  `linux_static_audit.py:47-55 HANDLED_SOURCE_SUBSTRINGS`, `:75-81 LIVE_SOURCE_SUBSTRINGS`,
  `:91+ NOOP_SOURCE_SUBSTRINGS`, consumed at `:174-183`, reported at `:462-464` and `:523-528`. That is
  **four** copies of seven Swift string literals in total. **Warning: do not re-run it casually** —
  `OUT_DIR = Path(__file__).resolve().parent` (line 21) and it writes
  `linux-static-audit.md` / `.json` (line ~552) **in place inside the committed evidence directory**, so it
  mutates other change packages' artifacts while always returning 0. Treat regenerating it as an explicit,
  scoped action.
- `fullaudit_measurements.py` does **not** encode the marker numbers (its only near-hit is an unrelated
  verdict string at line 121) — it cannot go red from this change.

Required in the same change, therefore: collapse the four mirrors to one parsed source of truth (§5
probes 1-2), and record the v3 report amendment. Otherwise P1-7 closes while the evidence that justified it
quietly starts describing a matcher that no longer exists.
