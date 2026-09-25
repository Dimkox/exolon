# Citation-integrity audit — wave C docs vs primaries (`docs_researcher`)

Change: `20260924-close-wave-c-content-and-factory-audit-findings-f2d90a`
Tree `/home/pall/projects/.exolon-wave-c/exolon` · branch `codex/wave-c-content-factory-20260924` ·
HEAD `295690b` (= route base) · snapshot 2026-09-24 ~20:35 UTC, **writer in flight** (mtimes moved under
me: `change-spec.yaml` 20:26, `tasks.md`/`requirements.md` 20:28, `marker-coverage.md`/`green-meter-run.txt`
20:29, `level-content-v1.json` 20:23). Verdicts below were taken against those revisions.
Mode: strictly read-only. No repository file was written except this report.

**Method.** Every number was re-measured by me from `Exolon/Resources/*.tmx` with a *from-scratch* stdlib
implementation (independent of `wave_c_check.py`), plus `gh issue view 11 16 --repo Dimkox/exolon`, the
merged `analysis-p1-7-markers.md`, the `perfile/level-graph.md` it rests on, `ORIGINAL_MECHANICS.md`,
`LEVEL_COMPILER_AUDIT.md`, the v3 audit, and the current + route-base Swift. My own reimplementation of
`wave-c-canonical-1` reproduced **all 125 manifest digests byte-exactly (0 mismatches)**, so the
canonicalization is agreed, not assumed.

Verdict key: **VERIFIED** = primary re-measurement agrees · **DRIFT** = the number is right but the
restatement is imprecise/mis-scoped, or a citation no longer points where claimed · **UNSUPPORTED** = no
in-tree primary carries the claim.

---

## 1. Issues #11 and #16 — are the wave-C restatements faithful?

Primaries (fetched live):

- `#11` **OPEN**, labels `blocked-on-owner` + `wave-C`, body verbatim: «Из **127** source_marker только
  **76** покрыты matcher; `blk_waggon`, `blk_gunMachine_BOTTOM` и `blk_mushroom` игнорируются на
  **32** картах. Добавить фабричные типы или безопасную модель визуальных объектов. Источник: full audit P1-7.»
- `#16` **OPEN**, same labels, body verbatim: «Канонический хеш показывает **101** уникальную карту из
  **125**; **23 пары L02/L05 и L03S09/L04S11** идентичны. Подтвердить намеренность или восстановить
  уникальные данные. Источник: full audit P1-12.»

| Claim in wave-C docs | Source / primary | Verdict |
| --- | --- | --- |
| 125 maps · 127 `source_marker` objects · 11 distinct `sourceBlock` · 76 covered · 51 lost · 32 maps | my re-measurement: 125 / 127 / 11 / 76 / 51 / 32 | **VERIFIED** |
| 3 ignored families `blk_waggon` 24 (14 maps), `blk_gunMachine_BOTTOM` 18 (15), `blk_mushroom` 9 (6) | mine: 24/14, 18/15, 9/6 | **VERIFIED** |
| Controls: drop `beam_` ⇒ 71 lost; drop all 7 ⇒ 127 | mine: 71, 127 | **VERIFIED** |
| Pre-change "8 of 11 distinct values claimed" (`baseline-meter-red.txt`, report §Marker coverage) | mine: 8 claimed / 3 unclaimed of 11 | **VERIFIED** |
| Post-change 127/127 resolved, `unmatched: {}`, 11/11 claimed, no value double-matched | parsed the product classifier (`TMXMapLoader.swift:409-418`) and applied it to the corpus: 11/11, 0 double-matches, `kind_for` identical to the doc's §Product execution block | **VERIFIED** |
| 32-row per-map table of the 51 formerly-dropped markers (map · zone · kinds ×n · total) | diffed row-by-row against my measurement: 32/32 maps, exact kind counts, exact 0-based zone for each row, Σ=51, 0 errors | **VERIFIED** |
| `marker-disposition-v1.json` 11 rows (counts, maps, maps_list, zones) | all 11 rows match my census; `maps_list` for the 3 safe families is exactly my map set; mushroom zones `[25,43,53,69,90,118]` ✓ | **VERIFIED** |
| "101 unique of 125", 24 declared pairs = 23 `L02Sxx≡L05Sxx` (xx=03…25) + `L03S09≡L04S11`, 48 files | my canonicalization, **4 independent projection variants**, all give unique=101, groups=24, maps=48, and the same 23+1 pair set; xx range measured 3…25 | **VERIFIED** |
| "127 = 50 live + 26 no-op/write-only + 51 dropped" (`analysis-repo_explorer.md` §2) | 50 = 20 beam+13 beacon_base+13 control_beacon+4 changing_room; 26 = 19 blinker+2 topdown+5 stage_end; Σ=127 | **VERIFIED** |
| The 51 sit on already-solid cells; markers are 1-cell point anchors; 32 maps already drawn | mine: 51/51 on a solid `Collision` cell (all gid=1); 0/127 carry `width`/`height`; `x==sourceX*16 ∧ y==sourceY*16` 127/127; all 32 have an `imagelayer` | **VERIFIED** |
| Footprints `3x17 / 6x8 / 5x6 / 4x3 / 6x6 / 0x0` + safe `5x3, 4x3, 4x3` | read from the current Swift (`CGRect` 48×272, 96×128, 80×96, 64×48, 96×96, `break`, `break`) and `safeModelFootprintCells` (`TMXMapLoader.swift:427-431`) | **VERIFIED** |
| brief.md:11 «of **127 distinct `source_marker` values**» · change-spec AC-001 «127/127 **distinct source_marker values**» | 127 is the **instance** count; the corpus has **11** distinct values. `README.md` and `requirements.md` AC-001 say it correctly ("127 `source_marker` objects") | **DRIFT** (F1) |
| change-spec FORBID-001 «the **24 duplicate maps**» · same phrase in `marker-disposition-v1.json` `forbidden[0]` | it is 24 duplicate **pairs** = 48 maps (the report and manifest say 48 correctly); issue #16's *title* «24 зоны…» is itself loose | **DRIFT** (F2) |
| brief.md quotes #16's finding text «Подтвердить намеренность или восстановить уникальные данные.» | verbatim ✓ | **VERIFIED** |
| Docs present P1-7/P1-12 as **closed** ("CLOSED BY RULING", `tasks.md` "closed by ruling", report «instead of an open audit finding», `state.json` → `approved` "P1-12 closed by documented ruling") | both issues are still **OPEN** and carry `blocked-on-owner` = «Нужно продуктовое решение владельца»; no wave-C doc says so or records an owner reply | **DRIFT** (F3) |
| Propagation of the merged §1 parenthetical «127 `.tmx` exist tree-wide; the other 17 … fixtures» (`analysis-repo_explorer.md:51`) | measured: 142 `.tmx` tree-wide = 125 Resources + 17 fixtures. 125/125/17 are right; the total "127" is the **marker** count leaking into a file count. Inherited verbatim from merged `analysis-p1-7-markers.md:14` | **DRIFT** (F4) |

---

## 2. Merged measurement + `perfile/level-graph.md` — same canonicalization? Pair count 23+1? "4 pairs byte-identical incl. background"?

| Claim | Primary | Verdict |
| --- | --- | --- |
| Manifest canonicalization = "the audited level-graph slice: tiles of every layer + every object, background excluded" (`wave_c_check.py:135`, report §Canonicalization) | `level-graph.md` §Дубликаты: slice «тайлы + объекты» ⇒ **101 / 24 groups / 48 maps** — my independent reimplementation reproduces 101/24/48 **and all 125 manifest digests byte-exactly** | **VERIFIED** |
| Report: «**Identical to the method** the merged level-graph lane used» | the lane's scripts lived in `/tmp/lane-graph/` — **outside the repo** (`level-graph.md` header), so method identity is not checkable in-tree; only output equality is (and it holds, incl. 96 tiles-only and 121 with background). `analysis-repo_explorer.md` §3 states this correctly ("had to be reconstructed and *proved* equal") | **DRIFT** (F5 — overstatement of "identical method") |
| Slices «96 (tiles) / 101 (tiles+objects) / 121 (+backdrop bytes +tileset resolution)», «byte-level = 125 unique of 125» | mine: 96 / 101 / 121 / 125 | **VERIFIED** |
| Pair count **23 + 1** | mine: exactly 23 `L02Sxx≡L05Sxx` (xx 03…25) + `L03S09≡L04S11`; no extra, no missing, across 4 projections | **VERIFIED** |
| «**4 pairs** identical including the backdrop» = `L02S04/L05S04`, `L02S16/L05S16`, `L02S22/L05S22`, `L02S23/L05S23` (`zone_028≡103`, `zone_040≡115`, `zone_046≡121`, `zone_047≡122`) | mine: exactly those 4 pairs are backdrop-byte-identical; PNG census 153 files / 149 unique / the same 4 duplicate pairs; `level-graph.md` names the same 4 and the same 4 PNG pairs | **VERIFIED** |
| Correctly reflected vs the lane's basis? `level-graph.md` conditions the 4 on «байты фона **и резолв тайлсетов**», while the manifest flag compares backdrop PNG bytes only | mine: adding tileset declarations **and** their resolved image digests changes nothing — still 121/4/8, same pairs. So the narrower flag is equivalent; the "differ **only** in which `zone_NNN_original.png`" claim for the other 20 pairs is also exactly reproduced (101 → 121 = +20 splits) | **VERIFIED** |
| `self_check.body_sha256 = 6be262cb…` (report, `tasks.md`, green transcript) | recomputed `sha256(json.dumps(body, sort_keys=True))` over the manifest minus `self_check` → `6be262cba2a1081370c0c22f9333f0596829b192afc11e74b8fc38fd58d7fcc8` | **VERIFIED** |
| `generated_from_commit: 295690b…`, `resource_directory`, `unique_count: 101`, `map_count: 125`, `duplicate_group_count: 24`, `maps_covered_by_duplicates: 48` | manifest fields + recomputation | **VERIFIED** |
| Merged `analysis-p1-7-markers.md` numbers still hold at this route base (127/76/51/32/24/18/9/71 + `:351`, `:356…394`, `:407`, `:409`) | re-measured ✓; `git show 295690b:…TMXLevelRuntime.swift` puts `case "source_marker":` at 351, the 7 tests at 356/361/366/369/371/380/394, chain closing at 407, `default:` at 409 ✓ (audit citation `351-407` exact) | **VERIFIED** |
| `marker-disposition-v1.json` `basis` cites `TMXLevelRuntime.swift:356-360 / 361-365 / 366-368 / 370 / 371-379 / 380-393 / 394-406` | true at route base; **false in the working tree this change edits** — `case "source_marker":` now at `:359`, `:370` is `forceFields.append`, `:394-406` sits inside `.beaconBase`. The JSON carries no "at route base" qualifier (unlike `tasks.md`/`analysis-repo_explorer.md`, which do) | **DRIFT** (F6) |
| `analysis-repo_explorer.md:51` "TMXMapLoader.swift (353 lines)" | 352 at route base (`awk END{NR}`, file ends with newline) | **DRIFT** (F7, trivial) |
| Other anchors cited by wave-C evidence: `TMXMapLoader.swift:305-343`, `GameScene.swift:575` + `sourceHazards` 0 appends, `stageExitMarkers` read nowhere, `TMXTileMapRenderer.swift:57-61,84-85`, `ORIGINAL_MECHANICS.md:36-41`, `v3_measurements.py:43-48/89/331-337`, `linux_static_audit.py:21/47-55/75-81` | each opened: decodeLayerData 305-343 (unchanged by the edit) ✓; `:575` is the `sourceHazards` kill branch in base **and** current ✓; `sourceHazards` declared `:28`, never appended ✓; `stageExitMarkers` declared + appended, no reader ✓; renderer sizing/basename lines ✓; OM 36-41 = "Stationary gun machine" ✓; the three measurer anchors ✓ | **VERIFIED** |

---

## 3. TMX trap — the 0-based `zoneNumber` formula as stated

| Claim (report §Zone identity; manifest `zone_index_formula`; INV-001) | Primary | Verdict |
| --- | --- | --- |
| `int(zoneNumber) == (stage-1)*25 + (scene-1)`, 0-based, `L05S25 → 124` | mine: holds for **117/117** maps carrying the key, 0 deviations; derived index spans 8…124 | **VERIFIED** |
| Property present on 117 of 125 | mine: 117 | **VERIFIED** |
| The 8 keyless maps are exactly `L01S01…L01S08` (zones 000-007) and carry ad-hoc provenance keys instead | mine: exactly those 8; their derived indices 0…7; each carries one of `originalSource`/`referenceSource`/`referenceObjects`/`step9Corrected`/`step9Progress` | **VERIFIED** |
| Naive «L01S09 must be zone 009» ⇒ **117 false mismatches** ("the same trap as comparing against the file name") | mine: 117/117 false under the naive reading; the probe asserts the flip, so it cannot degrade into a tautology | **VERIFIED** |
| «`zoneNumber` continues the **original ASM numbering 000…124**» | `LEVEL_COMPILER_AUDIT.md` numbers all 125 screens `000…124` and its index equals `(stage-1)*25+(scene-1)` for **125/125** files; `L01S01→000`, `L05S25→124` | **VERIFIED** |
| Manifest stores the derived `zone_index` for all 125 files, keyless included | mine: 125/125 `zone_index` == derived value; the 8 keyless entries record `zone_number_property: null` | **VERIFIED** |
| INV-001 scoping («derived for all 125, raw property on 117, eight maps honestly record null») | matches measurement exactly | **VERIFIED** |
| Report's formula block is introduced by "For every map that **carries the property** (117 of 125)" but its inline example is `L01S01 -> 000` — `L01S01` is one of the 8 that carry nothing | the example is true for the *derived* index, misleading inside that sentence | **DRIFT** (F8, wording) |

---

## 4. "Intentional reskin" — ruling or source-backed?

What the primaries actually say (verbatim):

- `ORIGINAL_MECHANICS.md:166` (inside **«## Walkthrough checkpoints that must work exactly»**):
  «Zones **100–124 repeat the structural pattern of 25–49 with cosmetic changes after 101**; Zone 124
  completes the full game and loops to the beginning.» OM's own header ranks that source #4:
  «StrategyWiki walkthrough **only as a cross-check**».
- `engineering/reports/exolon-full-audit-20260920-v3.md:37` (P1-12 row, last column):
  «**стадия 5 = перекраска стадии 2**»; `:130`: «P1-12 дубли контента (**влияет на обещание
  «125 original zones**)»; `:93` lists the UI label «ALL 125 ORIGINAL ZONES» among B1…B9.
- `perfile/level-graph.md:36`: «Стадия 5 (зоны 102…124) — это **перекрашенная** стадия 2 (зоны 27…49)».
- `LEVEL_COMPILER_AUDIT.md` — no prose about stage 5 at all, but its **per-screen records settle it**:
  `solid=` + action list are **identical for both members of 23 of the 24 declared pairs** (measured),
  while `L05S01`/`L05S02` differ from `L02S01`/`L02S02` — i.e. the repetition is in the imported 1987
  table, and it starts at zone 102, precisely OM's "cosmetic changes after 101".
- No primary anywhere uses the word *intentional / намеренно* for the duplicates; issue #16 explicitly
  leaves it open («Подтвердить намеренность **или** восстановить уникальные данные»).

| Claim | Verdict |
| --- | --- |
| "The duplication is in the imported source data, not produced by the factory (the loader/parser chain in `Exolon/GameCore/Levels/`)" | **VERIFIED** — and now backed by a primary the change never cited: the ASM table itself repeats 23/24 pairs. No generator or `.asm` exists in-tree (`find *.asm` → none), so the factory could not have authored it. |
| "Stage 5 is the original game's recolored stage 2" (for the 23-pair axis) | **VERIFIED** against `ORIGINAL_MECHANICS.md:166` + v3 §1:37 + `level-graph.md:36` + the ASM table. **But no wave-C doc names any of them** — the report asserts it bare (citation gap, F9). |
| "…so the 24 pairs are intentional content" (i.e. intentionality as a *fact*) | **UNSUPPORTED as a sourced fact / correctly a RULING** — no primary states intent; the route task did order "rule on intentionality explicitly". Labeled as a ruling in `brief.md` §Design rulings 1, `tasks.md` ("closed **by ruling**"), the report (§"Ruling on P1-12"), and the manifest (`ruling.decision`). Stated as fact, without that label, in **README.md** ("are the original game's recolored stage 2"), **test-plan.md** ("visually identical **as designed**"), **change-spec FORBID-001** ("the reskin **is** original-design content") and the report's intro ("a **design fact** of the original game") — F10. |
| The premise covers the 24th pair (`L03S09 ≡ L04S11`, zones 58/85) | **UNSUPPORTED, and contradicted in-tree.** The report itself calls it "the single pair off that axis", and OM:166 / v3 / level-graph speak only of stage 5↔stage 2 — but `LEVEL_COMPILER_AUDIT.md` records **different originals** for it (`:66` `058 L03S09 solid=140 actions=` vs `:93` `085 L04S11 solid=128 actions=`), while the two shipped maps are content-identical (same canonical digest `1a91d3e7…`, tiles + 1 object). So the ruling's blanket reason "no unique data was lost" (`level-content-v1.json` `ruling.reason`) is not carried by any primary for that pair. Caveat, and it cuts both ways: the `solid=` column matches **no** TMX-derived metric (0/125 screens, for any plausible definition), so it cannot *prove* a loss either — it is an unresolved discrepancy the docs do not disclose. |
| README: "`L02Sxx≡L05Sxx` pairs **plus `L03S09≡L04S11`** are the original game's recolored **stage 2**" | **DRIFT** — the 24th pair is stage 3 → stage 4 (zones 58/85), not stage 2 → stage 5, so folding it into that predicate is wrong as written (F11). |
| Closing docs address the finding the audit actually raised | **GAP** — v3 framed P1-12 as a threat to the «ALL 125 ORIGINAL ZONES» promise; no wave-C doc mentions the UI label or says whether the ruling leaves that promise accurate (F12). |

---

## Findings to fix (writer/controller), ranked

1. **F3 — closure/status honesty.** `README.md`, `brief.md`, `tasks.md`, the report and `state.json` all
   say P1-7/P1-12 are closed or no longer open, while issues **#11 and #16 are OPEN and labeled
   `blocked-on-owner`**. Add one line to each closing doc: ruling recorded in-repo; upstream issues stay
   open pending the owner's decision (and a PR comment linking them).
2. **F10/F11 + the 24th pair.** Keep the ruling, but (a) drop the fact-form "are the original game's
   recolored stage 2 / as designed / is original-design content" from README, test-plan and FORBID-001,
   or attach the citations; (b) state explicitly that the stage-5 rationale covers **23** pairs and that
   `L03S09≡L04S11` is pinned by the same mechanism on the weaker ground "already identical in the shipped
   data", and (c) disclose the `LEVEL_COMPILER_AUDIT.md` tension (`solid=140` vs `128`, `actions` empty on
   both) instead of asserting "no unique data was lost" for all 24.
3. **F9 — missing citations.** Name the primaries behind the reskin premise: `ORIGINAL_MECHANICS.md:166`,
   `exolon-full-audit-20260920-v3.md:37`, `perfile/level-graph.md:36`, and the ASM table's identical
   per-screen records for 23/24 pairs. This is the only load-bearing claim in wave-C carried without a pointer.
4. **F6 — stale `file:line`.** In `marker-disposition-v1.json`, qualify every `TMXLevelRuntime.swift:NNN`
   basis as "at route base `295690b`" (or re-point to the current `:359-437` switch). They were regenerated
   at 20:21, i.e. after the change's own edit to that file.
5. **F4 — propagated arithmetic error.** "127 `.tmx` exist tree-wide; the other 17 … fixtures"
   (`analysis-repo_explorer.md:51`, copied from merged `analysis-p1-7-markers.md:14`) → measured **142**
   (125 + 17). Fix in the wave-C doc and note the merged source keeps the same defect.
6. **F1/F2 — unit slips in the typed spec.** AC-001 «127/127 **distinct source_marker values**» → "127
   `source_marker` objects (11 distinct `sourceBlock` values)"; FORBID-001 «24 duplicate **maps**» → "24
   duplicate **pairs** (48 maps)". Same in `brief.md:11` and `marker-disposition-v1.json:154`.
7. **F5/F7/F8 + display nit** (low). Report: "Identical to the method …" → "reconstructed and proved equal
   by output (the lane's script is not in the tree)" — `analysis-repo_explorer.md` §3 already words it
   correctly; `353 lines` → 352; move the `L01S01 -> 000` example out of the "carries the property"
   sentence. In `marker-coverage.md` §Product execution, rename the `footprint:` key
   (e.g. `safe_model_footprint_cells`): it prints `safeModelFootprintCells` for **every** family, so it shows
   `blk_beam_down: 4x3` directly under a table row saying `3x17` — correct but readable as a contradiction.
   `marker-disposition-v1.json` `totals.safe_model_kinds: 3` counts *families*; `tasks.md` FORBID-002
   "the two safe-model kinds" counts *kinds* (`inertScenery`, `unconfirmedAction`) — both true, label the unit.

**Not findings.** Every quantitative claim I was asked to re-check reproduces from the corpus; the two
independent measurements (mine and the meter's) agree on all 125 digests, the 101/24/48/4 counts, the
23+1 pair set, and the marker census. `resources` are unmodified (my digest recompute ran against the
working tree and matched a manifest generated at `295690b`), so FORBID-001's data claim holds as measured.

---

## Auditor summary (8 lines)

1. Issues #11/#16 (fetched live): all restated numbers — 127/76/51/32, 24·18·9 with 14/15/6 maps, 101/125,
   23+1 pairs — are faithful; both issues are still **OPEN** and `blocked-on-owner`, which no doc says (F3).
2. Independent stdlib re-measurement reproduces the whole marker census, all controls (71 / 127 / 8-of-11),
   the 32-row per-map table, the disposition JSON and every footprint against the actual Swift — 0 numeric errors.
3. My own reimplementation of `wave-c-canonical-1` reproduces **all 125 manifest digests byte-exactly**:
   101 unique, 24 groups, 48 files, exactly the 23 `L02Sxx≡L05Sxx` (xx 03…25) + `L03S09≡L04S11`; `body_sha256` recomputes.
4. "4 pairs byte-identical incl. background" is correctly reflected: same 4 pairs and same 4 PNG duplicate
   pairs as `level-graph.md`; adding tileset bytes/resolution changes nothing (121/4/8 reproduced), and the
   other 20 pairs differ **only** in the referenced `zone_NNN_original.png`.
5. TMX trap verified, including against the ASM record: 0-based formula 117/117, keyless = exactly
   `L01S01…L01S08`, naive reading = exactly 117 false mismatches, and `LEVEL_COMPILER_AUDIT.md` numbers
   all 125 screens with the same 0-based index.
6. "Intentional reskin" is **our ruling** (no primary says intentional; #16 asks to confirm) — properly
   labeled in brief/tasks/report/manifest, but asserted as fact in README, test-plan and FORBID-001, and
   **never cited** although `ORIGINAL_MECHANICS.md:166` + v3:37 + the ASM table support the 23-pair premise.
7. The ruling's premise does not reach `L03S09≡L04S11`: the ASM table records those two as **different**
   originals (solid 140 vs 128) while the two shipped maps are content-identical, so "no unique data was
   lost" is
   UNSUPPORTED for that pair — and the `solid=` column matches no TMX metric (0/125), so it is a disclosed
   tension, not a proven defect.
8. Wording/citation drift to fix: "127 distinct values" (AC-001/brief), "24 duplicate maps" (FORBID-001),
   route-base `TMXLevelRuntime.swift:NNN` refs now stale post-edit, "127 .tmx tree-wide" (142),
   "identical method" (only outputs are provable), and the `footprint:` key ambiguity.
