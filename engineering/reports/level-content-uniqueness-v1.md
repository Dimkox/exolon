# Level content spec v1 — uniqueness model, canonicalization and the P1-12 ruling

Change: `20260924-close-wave-c-content-and-factory-audit-findings-f2d90a`
Contract: [`../contracts/level-content-v1.json`](../contracts/level-content-v1.json)
Machine check: [`wave_c_check.py`](../changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/wave_c_check.py)
(`--write-manifest`, `--write-dispositions`, nine probes; stdlib only, ~2.5 s)

> **Status.** This document records a *ruling* and its evidence. Audit findings P1-7 (issue #11) and
> P1-12 (issue #16) are resolved **by ruling, pending PR merge**: both issues remain OPEN upstream and
> #16 carries `blocked-on-owner`, because the finding text asks to "confirm intentionality **or** restore
> unique data" and that choice belongs to the owner. No file in this tree closes them.

## What this document fixes

`Exolon/Resources` ships **125** level files (`L01S01…L05S25`). Under the audited content slice they
describe **101 distinct levels**. Change `f2d90a` rules that gap to be intentional original design rather
than a factory defect, and pins it as a testable contract. The ruling is a decision, not a sourced fact:
no primary anywhere states that the duplication was intentional (see "Where the premise reaches, and
where it stops").

| Quantity | Value | Where it is enforced |
| --- | ---: | --- |
| Level files | 125 | `level_pair_manifest_pinned` |
| Distinct levels (tiles + objects) | **101** | same probe + `unique_count` in the manifest |
| Declared identical pairs | **24** (48 files) | `identical_pairs` must be hash-equal |
| Pairs identical including the backdrop | **4** | `background_identical` flag |
| Undeclared collisions tolerated | **0** | any new collision fails the test |
| `source_marker` objects resolved | **127 of 127** | `marker_coverage_all_maps` |
| …of which reach gameplay | **50** | disposition column, `ignored_types_disposition` |
| …recorded as labeled safe models | **51** (previously silently dropped) | `safe_models_are_labeled` |
| …documented no-op / write-only | **21 + 5** | disposition column (`no-op`, `write-only`) |
| Silently dropped markers | **0** (was 51 on 32 maps) | `marker_coverage_all_maps` |

"Resolved" is never "implemented". 77 of the 127 markers produce no observable change in the running game
(51 safe models + 21 no-ops + 5 write-only), and this change deliberately invents no behaviour for any of
them. Under the amended AC-001 the disposition column is normative evidence, and the meter enforces
`disposition == safe-model ⟺ product isSafeModel ⟺ label present` as a two-way equivalence, so a safe
model cannot be relabelled "typed" to dodge FORBID-002.

## Zone identity is 0-based — do not compare `zoneNumber` to file names

The rule is

```
int(zoneNumber) == (stage - 1) * 25 + (scene - 1)      # e.g. L02S03 -> 027, L05S25 -> 124
```

and it is evaluated on the **117 of 125** maps that carry the `zoneNumber` property. The other 8
(`L01S01…L01S08`, zones 000-007) have **no** `zoneNumber` key at all — they carry ad-hoc provenance keys
instead — so for those 8 only the *derived* index exists, and the manifest records
`zone_number_property: null` rather than inventing a value.

`zoneNumber` continues the original ASM numbering `000…124`: `LEVEL_COMPILER_AUDIT.md` numbers all 125
screens with exactly that 0-based index (`000 L01S01` … `124 L05S25`). A naive reading such as "L01S09
must be zone 009" therefore produces **117 false mismatches**, and comparing the number against the file
name fails the same way. `zone_index_formula` is enforced *and* required to demonstrate that: the probe
asserts the naive readings blow up, so it cannot degrade into a tautology. The manifest stores the
derived `zone_index` for all 125 files, keyless ones included, and INV-001 binds the canonicalization
version to every hash.

## Canonicalization (version `wave-c-canonical-1`)

The merged level-graph lane computed its numbers with a script kept in `/tmp/lane-graph/`, **outside the
repository**, so its method cannot be compared source-to-source in-tree. What this change did was
reconstruct a method and **prove it equal by output**: the reconstruction reproduces the lane's
96 / 101 / 121 slice counts, its 24 duplicate groups over 48 maps, the same 23+1 pair set, and the same
4 fully-identical pairs — and the independent citation audit reproduced all 125 manifest digests
byte-exactly from the same description.

* **included** — every `<layer>` tile array (decoded with the product loader's own semantics:
  `base64` → little-endian `uint32`, `csv` → split on `,` `\n` `\r` `\t` space, non-empty
  `compression` is a hard error, per `TMXMapLoader.swift:305-343` at route base `295690b`), the layer
  name/dims, and every `<object>` (`name`, `type`, `x`, `y`, `width`, `height`, sorted `property`
  name/value pairs);
* **excluded** — map properties (`nextLevel`, `zoneNumber`, `zoneSource`, provenance keys),
  `imagelayer` references and backdrop bytes, tileset declarations and their resolution;
* serialized with `json.dumps(..., sort_keys=True)` and hashed `sha256`.

Why the exclusions matter: byte-level file hashes give **125 unique of 125** — useless, because
`nextLevel` and `zoneNumber` differ even where the level is the same. Adding backdrop bytes and tileset
resolution to the slice gives **121**; the gameplay-relevant slice is the 101 above. The manifest records
the backdrop separately per pair so both readings stay reconstructible.

Sensitivity was proved, not assumed: adding one object to `L05S03`, or changing one tile value, each
flips its digest, while an untouched re-parse of the same file does not (`level_pair_manifest_pinned`
controls `extra_object_flips_digest`, `changed_tile_flips_digest`, `untouched_copy_is_stable`).

## The 24 declared pairs

23 of them are the stage-2 → stage-5 axis (zones 27-49 reused as 102-124). `L03S09 ≡ L04S11`
(zones 58 and 85) is a **stage-3 → stage-4** pair and is *not* part of that axis — see the next section.

| a | b | zone a | zone b | backdrop a | backdrop b | backdrop |
| --- | --- | ---: | ---: | --- | --- | --- |
| `L02S03` | `L05S03` | 027 | 102 | `zone_027_original.png` | `zone_102_original.png` | different |
| `L02S04` | `L05S04` | 028 | 103 | `zone_028_original.png` | `zone_103_original.png` | identical bytes |
| `L02S05` | `L05S05` | 029 | 104 | `zone_029_original.png` | `zone_104_original.png` | different |
| `L02S06` | `L05S06` | 030 | 105 | `zone_030_original.png` | `zone_105_original.png` | different |
| `L02S07` | `L05S07` | 031 | 106 | `zone_031_original.png` | `zone_106_original.png` | different |
| `L02S08` | `L05S08` | 032 | 107 | `zone_032_original.png` | `zone_107_original.png` | different |
| `L02S09` | `L05S09` | 033 | 108 | `zone_033_original.png` | `zone_108_original.png` | different |
| `L02S10` | `L05S10` | 034 | 109 | `zone_034_original.png` | `zone_109_original.png` | different |
| `L02S11` | `L05S11` | 035 | 110 | `zone_035_original.png` | `zone_110_original.png` | different |
| `L02S12` | `L05S12` | 036 | 111 | `zone_036_original.png` | `zone_111_original.png` | different |
| `L02S13` | `L05S13` | 037 | 112 | `zone_037_original.png` | `zone_112_original.png` | different |
| `L02S14` | `L05S14` | 038 | 113 | `zone_038_original.png` | `zone_113_original.png` | different |
| `L02S15` | `L05S15` | 039 | 114 | `zone_039_original.png` | `zone_114_original.png` | different |
| `L02S16` | `L05S16` | 040 | 115 | `zone_040_original.png` | `zone_115_original.png` | identical bytes |
| `L02S17` | `L05S17` | 041 | 116 | `zone_041_original.png` | `zone_116_original.png` | different |
| `L02S18` | `L05S18` | 042 | 117 | `zone_042_original.png` | `zone_117_original.png` | different |
| `L02S19` | `L05S19` | 043 | 118 | `zone_043_original.png` | `zone_118_original.png` | different |
| `L02S20` | `L05S20` | 044 | 119 | `zone_044_original.png` | `zone_119_original.png` | different |
| `L02S21` | `L05S21` | 045 | 120 | `zone_045_original.png` | `zone_120_original.png` | different |
| `L02S22` | `L05S22` | 046 | 121 | `zone_046_original.png` | `zone_121_original.png` | identical bytes |
| `L02S23` | `L05S23` | 047 | 122 | `zone_047_original.png` | `zone_122_original.png` | identical bytes |
| `L02S24` | `L05S24` | 048 | 123 | `zone_048_original.png` | `zone_123_original.png` | different |
| `L02S25` | `L05S25` | 049 | 124 | `zone_049_original.png` | `zone_124_original.png` | different |
| `L03S09` | `L04S11` | 058 | 085 | `zone_058_original.png` | `zone_085_original.png` | different |

**The 4 fully indistinguishable pairs** — `L02S04/L05S04`, `L02S16/L05S16`, `L02S22/L05S22`,
`L02S23/L05S23` — have *byte-identical* backdrops too (`zone_028 ≡ zone_103`, `zone_040 ≡ zone_115`,
`zone_046 ≡ zone_121`, `zone_047 ≡ zone_122`), so 8 files describe 4 levels and a player cannot tell them
apart at all. The PNG census reports exactly 4 duplicate pairs, which independently confirms the same
fact. The remaining 20 pairs differ *only* in which `zone_NNN_original.png` they reference — the recolour
is in the backdrop file, while platforms, enemies and coordinates are the same level.

## Where the premise reaches, and where it stops

The stage-2 → stage-5 repetition is source-backed by four primaries, none of which the change's first
draft cited:

1. `ORIGINAL_MECHANICS.md:166` (under "Walkthrough checkpoints that must work exactly"): *"Zones 100–124
   repeat the structural pattern of 25–49 with cosmetic changes after 101"* — OM itself ranks this source
   as a cross-check only, and "after 101" is precisely where the measured pairs start (zone 102).
2. `engineering/reports/exolon-full-audit-20260920-v3.md:37` — the P1-12 row states
   *"стадия 5 = перекраска стадии 2"*.
3. `.../20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/level-graph.md:36` —
   *"Стадия 5 (зоны 102…124) — это перекрашенная стадия 2 (зоны 27…49)"*.
4. `LEVEL_COMPILER_AUDIT.md` — the imported 1987 table settles it mechanically: its per-screen record
   (`solid=` plus the full action list) is **identical for both members of 23 of the 24 pairs**, while
   `L05S01`/`L05S02` differ from `L02S01`/`L02S02`. The repetition is in the data the factory consumed,
   and it starts at zone 102. No generator and no `.asm` exist in this tree, so the factory cannot have
   authored it.

**The premise does not reach `L03S09 ≡ L04S11`, and that pair contradicts it.** All four primaries speak
only of stage 5 versus stage 2. For zones 58 and 85 the imported table records *different* originals —
`058 L03S09 solid=140 actions=` against `085 L04S11 solid=128 actions=` — while the two shipped maps are
content-identical under the canonical slice (same digest, both with 64 nonzero Collision cells). So the
claim "no unique data was lost" is **UNSUPPORTED for this pair** and is deliberately not made.

The honest counterweight, disclosed rather than glossed: the `solid=` column matches **no** TMX-derived
metric in this corpus (0 of 125 screens equal; 6 within ±5 cells), so it cannot *prove* a loss either —
both action lists are empty. It is an unresolved discrepancy, not evidence of a defect. This pair is
therefore pinned on the weaker ground *"already identical in the shipped data"*, recorded as
`pair_notes["L03S09/L04S11"]` in the manifest and as `ruling_ground` on its pair row, and it is the one
worth regenerating first if the owner rejects the ruling — which would need the external
`data_zone_data.asm` to say what zone 58 or 85 originally held.

`level_pair_manifest_pinned` refuses to pass if that disclosure is absent, so the manifest cannot be
regenerated into implying that the stage-2 premise covers all 24 pairs.

## Ruling on P1-12: ruled intentional, pinned rather than repaired

* **Decision (this change's, not a source's):** the 24 pairs are treated as intentional original content
  and are **pinned**, not repaired.
* **No tile or object content may be authored to dissolve them** (FORBID-001). Doing so would ship
  invented content as if it were restored original data — the exact failure mode the finding warns about.
* The identity is pinned by `level_pair_manifest_pinned`, which fails if a declared pair ever diverges
  *or* if a new undeclared collision appears: "someone regenerated one half of a pair" and "someone
  pasted a new duplicate" are both loud failures.
* If the owner later decides these 48 files must become unique, the manifest answers "which 48 files and
  which 24 backdrops" as one query over `identical_pairs`. That is a new, separately authorized change.
* Maps with no backdrop at all are `L01S01…L01S04` and `L01S07` (5 of 125); none is in a duplicate pair,
  so `background_count: 0` there is data, not a gap in the manifest.

### Reconciling this with the "ALL 125 ORIGINAL ZONES" promise

The full audit raised P1-12 specifically as a threat to that UI claim
(`exolon-full-audit-20260920-v3.md:93` lists the label, `:130` names the tension). The claim is about
**zone count**, and the uniqueness model is about **content identity**; they are not in conflict, and
saying so is part of closing the finding rather than a side effect of it. The shipped game presents a
linear chain of 125 zones: 125 files, 124 `nextLevel` edges, one start (`L01S01`), one terminal
(`L05S25`), no cycles or orphans, and all 125 visited in order. Every one of the 125 zones is playable,
so "125 zones" is accurate as a count and this change does not alter it — the graph was verified
independently by the level-graph lane and is untouched here.

What "101 unique" qualifies is how much *distinct design* those 125 zones contain: 24 of them replay
content the player has already seen, 4 of those indistinguishably. The promise is therefore accurate on
count and **optimistic on content**, and that gap is a product-marketing judgement for the owner, not a
factory defect — which is exactly why it is recorded as a ruling with the issue left open. If the owner
wants the label to mean 125 distinct levels, that is the regeneration path above; if they want it to mean
125 playable zones, it already does.

## Marker coverage (P1-7), the other half of the same content question

The factory resolves **11 of 11** distinct `sourceBlock` values across **127 of 127** `source_marker`
objects (was 8 of 11 / 76 of 127). The three formerly-dropped families are `blk_waggon` (24 markers on
14 maps), `blk_gunMachine_BOTTOM` (18 on 15) and `blk_mushroom` (9 on 6) — 51 markers on 32 maps. Each is
now a typed, labeled safe-model record. The other 26 previously-"covered" markers keep their existing
disposition: 21 are documented no-ops and 5 write-only, which is why 127/127 must not be read as
"127/127 implemented". An unmatched marker goes to `TMXLevelRuntime.unmatchedSourceMarkers`, which the
meter treats as failure, and the runtime `switch` is exhaustive with no `default:`, so a new family
without an arm is a compile error. Full per-marker and per-map table:
[`marker-coverage.md`](../changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/marker-coverage.md).

## Regenerating

```bash
cd engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence
python3 wave_c_check.py --write-manifest       # rewrite the digest contract from the corpus
python3 wave_c_check.py --write-dispositions   # rewrite the marker coverage tables
python3 wave_c_check.py                         # run all nine probes (rc 0 == green)
```

`--write-manifest` derives the duplicate pairs from the corpus and *refuses* to write if they no longer
match the 24 pairs this document rules on, so the contract cannot be silently rewritten to describe a
different finding. The written manifest carries `self_check.body_sha256` over its own body, which is what
binds the canonicalization version document-wide: editing any entry, including a ruling string, without
regenerating fails `manifest_selfcheck`. Regeneration is byte-stable — running it twice on an unchanged
corpus produces the same file.
