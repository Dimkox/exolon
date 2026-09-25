# Task 1 — Characterization: where the level factory is, and what it actually does today

Change: `20260924-close-wave-c-content-and-factory-audit-findings-f2d90a`
Route base `295690b` · branch `codex/wave-c-content-factory-20260924` · tree
`/home/pall/projects/.exolon-wave-c/exolon` · host Linux · **written before any product edit.**

Method: read the tree, then re-measure `Exolon/Resources/*.tmx` with `xml.etree` and compare every
number against the merged authority (`20260921-…-2e7698/evidence/analysis-p1-7-markers.md` and the
`20260919-…-7db1f3/evidence/perfile/level-graph.md` it cites) instead of recomputing fresh.

## 1. Factory location — "the level factory" is a three-stage chain, and the matcher is in stage 3

| Stage | File:line | Role | Evidence this is the factory and not a consumer |
| --- | --- | --- | --- |
| 1 · data generation | `LEVEL_COMPILER_AUDIT.md` (133 lines) | The 1987 zone/block table that **produced** all 125 screens (`Action counts: 2=101, 3=37, …`). Per-screen lists are `x:y:type`. | Reclassified by the v3 pass as **ASM input, not shipped data**; no `.asm` and no generator exist in-tree (`find *.asm` → none). Usable for **exclusion**, never for **specification**. |
| 2 | `Exolon/GameCore/Levels/TMXMapLoader.swift` (352 lines at route base `295690b`) | XML parser → `TMXMapData` (layers, object groups, `properties`). **No marker semantics here.** | Only file the Linux harness compiles (§4). |
| 3 | `Exolon/GameCore/Levels/TMXLevelRuntime.swift:351-414` | **The matcher** — `case "source_marker":` turns `sourceBlock` into runtime objects. This is the "factory matcher" both issues refer to. | Cited by the audit as `TMXLevelRuntime.swift:351-407`; that range is exact in this tree. |
| 3b | `Exolon/GameCore/Levels/TMXTileMapRenderer.swift:57-61,84-85` | Tile sprite sizing + basename texture resolution. | Not on the marker path. |

### Matcher anatomy (verbatim line map, this HEAD)

```
:351  case "source_marker":
:352    let source = object.properties["sourceBlock"] ?? ""
:356    if        source.contains("beam_")           -> forceFields.append + rootNode.addChild
:361    else if source.contains("topdown_electro")   -> break                     (no-op)
:366    else if source.contains("blinker")           -> break                     (no-op)
:369    else if source.contains("stage_end")         -> stageExitMarkers.append   (write-only)
:371    else if source.contains("changing_room")     -> changingRooms + exclusions
:380    else if source.contains("beacon_base")       -> missileGuidanceBaseCollisionRects
:394    else if source.contains("control_beacon")    -> missileGuidance + coverNode
:407    }                        <-- chain CLOSES WITH NO `else`: unmatched sourceBlock is dropped here
:409  default:   (of `switch object.name`, not of the sourceBlock chain)
:413      break  <-- "Unknown objects are intentionally ignored"
```

**Root cause of P1-7 is `:407`, not `:409`.** The silent drop is the *absence of an `else`* on the
`if/else if` chain: a `sourceBlock` that matches none of the seven substrings falls out of the chain and
the case ends. No array is touched, no log, no counter, no test can see it. `:409-413` is a *different*
silent path (unknown **object names**) and is not what the 51 markers hit — the 51 all arrive as
`object.name == "source_marker"`, a name that *is* handled.

Consequence for AC-001: "the silent-ignore code path no longer exists (an unmatched marker fails the
meter)" requires (a) an `else` that records the miss on an observable property, and (b) a meter that
turns a non-empty record into failure. A meter alone cannot prove (a) because a dropped marker is invisible
to the runtime, which is precisely why the four hand-copied mirrors (§5) all agree with each other and
disagree with reality.

## 2. P1-7 baseline re-measured at this base — every merged number reproduces exactly

Corpus: `Exolon/Resources/*.tmx` = **125** files. (A whole-tree `find -name '*.tmx'` gives **142** = 125
shipped + 17 deliberately malformed loader fixtures under `20260919-…/evidence/harness/fixtures/`; the
merged `analysis-p1-7-markers.md:14` mis-states that total as "127 `.tmx` exist tree-wide", which is the
*marker* count leaking into a file count — corrected here, the merged file still carries it. Excluding the
fixtures, as the merged pass did, gives the same 125.) Object layers: `Objects` in 119 maps,
`Object Layer 1` in 6 legacy maps.

`HANDLED` = the seven substrings parsed out of `TMXLevelRuntime.swift` itself (not hand-copied):

| Quantity | Merged authority | Measured here | |
| --- | ---: | ---: | --- |
| `source_marker` objects | 127 | **127** | ✅ |
| distinct `sourceBlock` values | 11 | **11** | ✅ |
| covered by the 7 substrings | 76 | **76** | ✅ |
| lost | 51 | **51** | ✅ |
| maps carrying ≥1 loss | 32 | **32** | ✅ |
| `blk_waggon` | 24 / 14 maps | **24 / 14** | ✅ |
| `blk_gunMachine_BOTTOM` | 18 / 15 maps | **18 / 15** | ✅ |
| `blk_mushroom` | 9 / 6 maps | **9 / 6** | ✅ |

Full census (n · value · disposition): 24 `blk_waggon` **LOST** · 19 `blk_blinker` handled-no-op ·
18 `blk_gunMachine_BOTTOM` **LOST** · 13 `blk_beacon_base` · 13 `blk_control_beacon` · 10 `blk_beam_up` ·
10 `blk_beam_down` · 9 `blk_mushroom` **LOST** · 5 `blk_stage_end` (write-only) · 4 `blk_changing_room` ·
2 `blk_topdown_electro` handled-no-op. **127 = 50 live + 26 no-op/write-only + 51 dropped.**

Losing-map sets match the merged list verbatim, incl. the multi-family maps `L01S24`, `L03S04`, `L04S04`
and the reskin twins `L02S19/L05S19` (mushroom) and `L02S22/L05S22`, `L02S21/L05S21` (gunMachine).

### Semantics available for the three families (in-tree evidence only)

Restating the merged §2 findings, which this pass re-confirms by grep and by the shared 1-cell geometry:
all 51 markers sit on an already-**solid** Collision cell, every one of the 32 maps already carries the
full-frame `imagelayer` that draws them, and all 127 markers have **no `width`/`height`** (they are
`x = sourceX*16, y = sourceY*16` point anchors). So the loss is *entity* loss, never a visual or
collision hole.

- `blk_mushroom` (9/6 maps): **0 actions** at own cell or in a 6×4 window; footprint uniform **(4,3) cells**,
  the same shape class as `blk_beacon_base` (whose `:381-383` comment independently calibrates the
  estimator at 4×3 for 13/13). No asset matches `mushroom` in `Exolon/Resources`.
- `blk_waggon` (24/14 maps): **0 actions**; footprint 5×3 for 21/24, with merged runs reading (10,3) and
  (15,3) where waggons touch (`L01S23` markers at x=8 and x=14). No asset matches `waggon|wagon`.
- `blk_gunMachine_BOTTOM` (18/15 maps): the **only** losing family with a positive action record — type 11
  at own cell 18/18, offset `(-1,+2)` from a `blk_gunMachine_TOP` turret 1:1 per map. But type 11 has 56
  instances in the original and only 18 exported, and the other 38 appear in 18 maps with **no** BOTTOM
  marker at all, where they show as vertical pairs. So type 11 ≠ "lower gun barrel" on in-repo evidence;
  `ORIGINAL_MECHANICS.md:36-41` documents the gun-machine mechanic as ONE entity whose bullet origin
  (`turret.left + 2`, `turret.bottom + 56`) is the already-shipped `turret`, and `:170` lists gun machines
  as required; what is absent in-tree is only the numeric type-11 → entity binding for the *separate
  lower* cell. No `gunMachine*` asset.

**Ruling carried into the design:** none of the three can be given invented behaviour. All three resolve to
the *typed, labeled* safe model (recorded inert-scenery entity), which is the brief's tier-2
("documented safe model") and satisfies FORBID-002's "identifiable in the meter output". Tier-1 (real
factory type with gameplay) would require inventing behaviour, which is exactly what §2 forbids.

## 3. P1-12 baseline — canonicalization reproduced from the merged method, 101/125

`level-graph.md` defines the slice as **tile layers + objects, background excluded from identity**; it lists
96 (tiles only) / 96 (Collision) / **101 (tiles+objects)** / 121 (tiles+objects+background bytes+tilerset
resolution). Its script lived in `/tmp/lane-graph/` — **outside the repo**, so the method had to be
reconstructed and *proved* equal, not assumed. Reconstruction here: `xml.etree`, layer data decoded with the
product loader's own semantics (`TMXMapLoader.swift:305-343`: `base64`→little-endian `uint32`,
`csv`→split on `{, \n \r \t space}`, non-empty `compression` is a throw), objects as
`[name, type, x, y, width, height, sorted properties]`, `json.dumps(..., sort_keys=True)`, `sha256`.

Result: **101 unique of 125, 24 duplicate groups** — and the 24 groups are **exactly** the declared pairs
(`L02Sxx≡L05Sxx` for xx=03…25 **plus** `L03S09≡L04S11`), with no undeclared group and no missing pair.
Robustness check: the count is **101 for all 12** variants of (layer-name included, layer-dims included,
object-projection) tried, so the number is not an artifact of my projection choices; only the pair
*membership* could differ, and it does not.

Background equality recorded separately, as the brief requires: exactly **4 pairs are byte-identical
including the backdrop** — `L02S04/L05S04` (`zone_028_original.png` ≡ `zone_103_original.png`),
`L02S16/L05S16` (`zone_040` ≡ `zone_115`), `L02S22/L05S22` (`zone_046` ≡ `zone_121`),
`L02S23/L05S23` (`zone_047` ≡ `zone_122`). The other 20 pairs differ only in the referenced
`zone_NNN_original.png` file name. Both facts match `level-graph.md` §Дубликаты/§PNG byte-for-byte, and
the 4 PNG duplicate pairs are the same 4 pairs — mutual confirmation.

Zone identity: `int(zoneNumber) == (stage-1)*25 + (scene-1)`, **0-based**, holds for all 117 files that
carry the key, 0 deviations; the 8 files without it are `L01S01…L01S08` (zones 000-007), which carry
ad-hoc provenance keys instead. A naive `L01S09 → 009` comparison yields 117 false mismatches — recorded
here because the manifest test must use the formula, not the file name (§`zone_index_formula`).

## 4. Executable Linux contour available for product-code assertions

`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/run.sh` compiles the
**product** `TMXMapLoader.swift` on Linux against a CoreGraphics type-rename shim and loads all 125 maps.
Two hard constraints it imposes on where new code may live:

- `run.sh` step 2 (`rc=65`): the build copy may differ from the repository file by **exactly one line**
  (`import FoundationXML` inserted after line 1). Anything appended to `TMXMapLoader.swift` is picked up
  with no `run.sh` change; anything in a **new** file breaks the contour.
- step 6: building without the shim must fail — keep it that way.

So the marker classifier belongs in `TMXMapLoader.swift` (Foundation-only, already on the harness path),
and its counts become measurable from real Swift instead of a Python replica.

## 5. Four hand-copied mirrors of the same seven literals — the staleness hazard

| Copy | Location | Consequence |
| --- | --- | --- |
| 1 | `TMXLevelRuntime.swift:356-394` | the product (authority) |
| 2 | `20260919-…-7db1f3/evidence/v3_measurements.py:89` `HANDLED = (…)` | never reads `TMXLevelRuntime.swift` ⇒ a Swift-only fix keeps it printing `lost=51` and **green** |
| 3 | `…/linux_static_audit.py:47-55` `HANDLED_SOURCE_SUBSTRINGS` (+ `:75-81` LIVE, `:91+` NOOP) | same; **and it rewrites committed evidence in place** (`OUT_DIR = Path(__file__).resolve().parent`, line 21) — do not run it casually |
| 4 | `…/v3_measurements.py:43-48` `EXPECTED` | the numbers the v3 report promises |

This is why `wave_c_check.py` **parses the Swift source** for the literal table instead of copying it:
probe `marker_baseline_reproduced` proves the *pre-change* 7/127 split from a parsed table, and
`marker_coverage_all_maps` proves the *post-change* table covers 11/11. `v3_measurements.py`'s own staleness
is a pre-existing defect of that change package; it is recorded, not silently patched here (its docstring
binds it to the v3 report's prose, and `analysis-p1-7-markers.md` §6 already prescribes that amendment as
that change's work).

## 6. Runtime-consumer facts that bound the change

- `sourceHazards` (`:28`) is declared and consumed by a **kill-player** branch
  (`GameScene.swift:575`) but has **0 appends** tree-wide. Routing scenery into it would make 33 harmless
  blocks instantly lethal — explicitly avoided.
- `stageExitMarkers` is appended at `:370` and read **nowhere** (write-only) — pre-existing, out of scope.
- `TMXMapLoader.swift` is the only `.swift` on the Linux contour; `GameScene.swift` needs SpriteKit and is
  macOS/xcodebuild-only, so no new consumer logic there can be proven on Linux.
- `v3_measurements.py:331-337` fails any `SKTexture(imageNamed:)` literal whose PNG is absent on disk
  (`texture_names_missing_on_disk: 0`). **No new texture name may be introduced**, so the safe model must
  be a recorded observable entity, not new artwork.
- pbxproj 4-edit rule (wave A): a **new** `.swift` file needs PBXBuildFile (~`:31`), PBXFileReference
  (~`:333`), group (~`:698`), Sources phase (~`:1374`). Avoided by appending to an existing file; see
  Deviations on task 5.

## 7. Gate state observed before edits

`python3 scripts/grok_verify.py --mode pr --no-record` at `295690b` + the change package only:
`RESULT: FAIL | profiles=base | changed=11`, with
`ERROR …/change-spec.yaml: test evidence path does not exist: …/evidence/wave_c_check.py` (×9) and
`contract path does not exist: engineering/contracts/level-content-v1.json`.
All other checks pass (`git-diff-check 4/4`, ruff, bandit, secret-scan, factory-unit, source-stability).
Confirms the controller's note: the two named artifacts must exist early; the spec is **not** edited to
satisfy the recorder.

## 8. Decisions taken from this characterization (binding for tasks 3-7)

1. Fix `:407` by giving the chain an `else` arm that records the miss; keep the seven existing substring
   tests **in their current order** (no value currently double-matches, but order-freedom is a property of
   today's data, not of the classifier — the meter must not depend on it).
2. Resolve all three losing families to a **typed, named, labeled inert-scenery model** with the measured
   footprints (mushroom/beacon class 4×3 → 64×48 px; waggon 5×3 → 80×48 px; gunMachine_BOTTOM 4 wide ×
   measured height, but its *behaviour* stays `unconfirmed`), plus an `unmatched` bucket that fails the meter.
3. Do not add gameplay behaviour, textures, nodes, or Swift files: the change is entity-recording plus
   manifest plus meter. Runtime registration for new *rendering* types is therefore not required (task 5 →
   Deviations, with the reason).
4. Pin P1-12 by digest manifest + divergence test, never by inventing tiles (FORBID-001).

Verdict: characterization complete, baseline reproduced 1:1, no product file modified yet.

---

## Appendix — currency of the citations in this file (added after implementation)

This report was written **before** the edit, so its `file:line` map describes the route base
`295690b`, which is exactly what it is evidence about. After the edit the same anchors moved. Both sets
are recorded here so no reader has to guess which tree a number belongs to:

| Anchor | Route base `295690b` (this report, §1) | After change f295690b+wave-C (working tree) |
| --- | --- | --- |
| `case "source_marker":` | `TMXLevelRuntime.swift:351` | `:359` |
| the seven substring tests | `:356, 361, 366, 369, 371, 380, 394` (`if/else if` chain) | replaced by `case .forceField/.highVoltage/.blinker/.stageEnd/.changingRoom/.beaconBase/.controlBeacon` at `:367-417` |
| chain closing with no `else` | `:407` | arms `:418-426` `.inertScenery`, `:427-434` `.unconfirmedAction`, `:435-439` `case nil:` → `unmatchedSourceMarkers.append` |
| `default:` of the object-**name** switch | `:409` | `:441` (unchanged in behaviour, out of scope here) |
| matcher authority | the chain in `TMXLevelRuntime.swift` | `TMXMapLoader.swift:364-435` (`TMXSourceMarkerKind`, `classify` `:407-420`, `safeModelFootprintCells` `:427-432`) + `TMXSafeModelMarker` `:438-444` |
| `TMXMapLoader.swift` length | 352 lines | 444 lines |

`marker-disposition-v1.json` carries the same dual anchoring per row (`citations.runtime_arm` checked
against the current tree, `citations.route_base` naming `295690b`), and `ignored_types_disposition`
**re-reads every cited line span** on each run, so a future edit that moves an arm reddens the meter
instead of leaving a stale citation in a table.

Two method notes from the same review pass:

- §3's canonicalization claim should be read as "reconstructed and proved equal **by output**": the
  merged lane's script lived in `/tmp/lane-graph/`, outside the repository, so method identity is not
  checkable in-tree. What is checkable — and checked — is that the reconstruction reproduces 101 unique,
  the same 24 groups, 96 tiles-only, 121 with backdrop+tilesets, and all 125 manifest digests.
- AC-005's pre-change side is no longer a golden this tool wrote and then compared to itself. The meter
  reads `git show 295690b:TMXLevelRuntime.swift`, fingerprints the chain arms from that immutable blob,
  and compares against the working tree's switch arms; the committed golden only records the same
  base-derived values plus the data digest (`baseline-prechange-digest.json`, digest
  `545e281f470c0900…`, unchanged across the edit).

## Corrections after review (appended; the text above is left as written pre-edit)

- **C1 — §2's `blk_gunMachine_BOTTOM` bullet understated what is in-tree.** Saying the mechanic's
  documentation "cannot be identified from anything in this repository" was **false**:
  `ORIGINAL_MECHANICS.md:36-41` documents the gun machine fully in-repo (bullet origin
  `turret.left + 2` / `turret.bottom + 56`, bullets travel left and are blaster-immune, the turret is
  grenade-destroyable for 150 points) and `:170` explicitly lists gun machines among the markers that
  must have a runtime implementation. The scope of what is missing is narrower: the **numeric
  type-11 → entity binding** that would say what the *separate lower* cell is, given 56 type-11 actions
  exist while only 18 accompany a BOTTOM marker and the other 38 sit in maps without one. The
  disposition (recorded safe model, never armed) is unchanged and still the right call; the shipped
  label, this report §2 and `marker-disposition-v1.json` now say it that way. Raised by the
  controller's micro-batch N1; `analysis-docs_researcher.md` had already marked the mechanic VERIFIED.
- **C2 — §8's footprint note encoded a wrong anchor.** It described the safe-model box as
  "beaconBase-equivalent", but the implemented `max(0, bottomY - height)` puts the box top two source
  rows **below** the marker (32 pt low on all 32 affected maps), whereas `.beaconBase`'s own conversion
  `pixelHeight - (sourceY + 3)*16` with `height: 48` puts the top at the marker's row. The helper now
  anchors at `topY = pixelHeight - syTop` and `wave_c_check.py` pins the arithmetic
  (`safe_model_anchor_problems` + `anchor_parity_broken`, controls
  `anchor_parity_honest_accepted` / `anchor_regressed_to_bottomY_detected` /
  `anchor_single_row_shift_detected` / `anchor_beacon_side_shift_detected`), so comment and code can no
  longer drift apart. Raised by the micro-batch N2 (round-1 code-review F1).
