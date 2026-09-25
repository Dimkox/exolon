# Analysis — docs_researcher (citation integrity, wave B, pass B)

Role: read-only auditor. Only repository write from this agent is this file.
Tree: `/home/pall/projects/.exolon-wave-b/exolon`, branch `codex/wave-b-mapdata-physics-20260924`,
route base `295690b` (= `origin/main`). All times UTC (owner lives GMT+3).

Snapshot of the audited docs at the moment of checking (the writer is in flight; the tree moved
under this audit — see §5):

| audited file | bytes | mtime (UTC) |
| --- | ---: | --- |
| `brief.md` | 3848 | 2026-09-24 19:44:10 |
| `change-spec.yaml` | 5449 | 2026-09-24 **20:31:17** |
| `architecture.md` | 2050 | 19:44:10 |
| `tasks.md` | 4173 | 20:29:31 |
| `test-plan.md` | 1513 | 19:44:10 |
| `evidence/wave_b_check.py` | 57766 | 20:25:50 |
| `evidence/wave_b_deltas.md` | 12350 | 20:27:49 |
| `evidence/wave_b_swift.txt` | 17733 | 20:13:27 |
| `evidence/analysis-repo_explorer.md` | 3849 | 20:28:55 |

Primary sources used: `gh issue view 5 6 7 9 --repo Dimkox/exolon` (fetched verbatim, all OPEN);
`engineering/reports/exolon-full-audit-20260920-v3.md:26-30`; the committed meters
`engineering/changes/20260919-...-7db1f3/evidence/v3_measurements.py` and
`.../20260921-...-2e7698/evidence/{analysis-p1-2-spawn.md,p1-1_piston_probe.py}` (both tracked in
git, so "merged" is accurate — PR #3/#4 are ancestors of `295690b`); `ORIGINAL_MECHANICS.md`; the
product Swift at `295690b`.

## 1. Issue-body baselines (issues #5 / #6 / #7 / #9)

| # | Claim (wave-B doc) | Source actually consulted | Verdict |
| --- | --- | --- | --- |
| 1.1 | "of 125 maps, 37 exact, 59 spawn +16 px above the Collision surface, 29 −16 px below" (`brief.md:14-15`) | issue #6: "На 125 картах: 37 без изменения, 59 с подъёмом 16 px, 29 с падением 16 px"; audit `v3.md:27`: "без изменения **37 карт**, подъём **+16 px → 59**, падение **−16 px → 29** (Σ=125)"; committed meter `v3_measurements.py` live run: `spawn_clean=37, spawn_lift=59, spawn_drop=29, spawn_zero_delta_total=125`; wave-B's own `wave_b_deltas.md` control column recomputed independently = `{0:37, +16:59, −16:29}` | **VERIFIED** (counts and Σ=125) |
| 1.2 | the ±16 is measured "above/below **the Collision surface**" (`brief.md:14-15`; echoed `requirements.md:1`, `release.md:1`) | `v3_measurements.stable_feet` returns rest-vs-**marker-feet** delta; `analysis-p1-2-spawn.md:§2` "rest−marker histogram {0: 37, +16: 59, −16: 29}"; same file §1: "The **real** error is worse than ±16 where the floor near the marker is thick" | **DRIFT** — reference frame mislabelled (marker, not surface) |
| 1.3 | "37 **exact**" (`brief.md:14`); AC-001 old text "the audited 37 exact" | audit calls it "без изменения" (unchanged); `analysis-p1-2-spawn.md:§2`: "**37** is a delta-classification, not a correctness count; **truly-correct (delta 0, body clear, walks) = 34**"; a different, real `exact` number exists: `spawn_legacy_exact=35` | **DRIFT** — collides with the audited `exact 35`; wave-B's own delta table proves 34 (only 34 maps have new==marker) |
| 1.4 | "46 pistons on 27 maps" (`brief.md:21`, AC-002, test-plan:8) | issue #5: "46 поршней на 27 картах"; audit `v3.md:26`: "46 объектов `piston` на 27 картах"; `v3_measurements.py`: `pistons_objects=46, pistons_maps=27`; `piston_probe.py EXPECTED`: same; harness artifact: 46 `PISTON` lines over 27 maps | **VERIFIED** (four independent sources) |
| 1.5 | "world-bottom **floats above** the player's feet and the piston cannot hit" (`brief.md:21-22`) | issue #5: "имеют world-bottom **ниже** уровня ног игрока"; audit `v3.md:26`: "**43** стоят **ниже** ног", histogram `96→1, 0→2, −32→12, −48→15, −64→16`; `piston_probe.py`: `product_model_localfloor = {lethal_area 3, edge_only 42, **below 0**, no_support 1}` | **UNSUPPORTED** — direction is inverted against all three sources; none reports anything floating above the feet |
| 1.6 | test-plan:8 "world-bottom ≤ player foot line (lethal band reached)" | product damage box is `[bottom, bottom+64]` vs player `[feet, feet+63]`; lethality needs `bottom < feet+63 AND bottom+64 > feet` (`wave_b_check.py` `new_lethal` implements the overlap, correctly) | **DRIFT** (prose only) — the written predicate states the *sunk* condition and contradicts 1.5's wording; the meter's predicate is right |
| 1.7 | "bullets culled at x>528 while the player clamp is x=544 (`Player.swift:128`)" (`brief.md:17`) | issue #7: "Игрок может выйти до x=544, а пуля удаляется при x>528"; audit `v3.md:28`: "`BlasterBullet.swift:42` kill при `x > 528`; `Player.swift:128` отпускает игрока до `544`"; base code: `BlasterBullet.swift:42` = `position.x > GameConstants.logicalSize.width + 16` (=528), `Player.swift:128` = `min(max(position.x, visualHalfWidth), logicalSize.width + 32)` (=544) | **VERIFIED** incl. both line numbers |
| 1.8 | "61 maps carry Collision right of x=512" (`brief.md:18`) | issue #7: "на 61 карте есть Collision правее x=512"; audit: "**61/125** карт имеют солидные клетки Collision при **x≥512**"; `v3_measurements.py:311` = `any(sx >= 512)` → 61 | **VERIFIED** for 61 (issue/audit disagree among themselves on ≥ vs >) |
| 1.9 | `wave_b_check.py` claims the same 61 under key `maps_solid_right_of_512` but computes `max(sx+TW) > 512` (cell right edge, i.e. `sx > 496`) — a different predicate than the audit's | recomputed both predicates on the corpus with the canonical parser: A(start≥512)=61, B(rightEdge>512)=61, `A\B = []`, `B\A = []`; contradictory control `[(504,·,·)]` → A=False/B=True, so the discriminator does fire in principle, it cannot on a 16-px grid (cell at 496 ends exactly at 512, not `>512`) | **VERIFIED by coincidence-free equivalence** — labels differ, extensions are identical for this corpus; harmless but should be stated |
| 1.10 | "each side instantiates its own 25-hit-point field → 50 per beam; expected behavior per issue #9 is **25 total**" (`brief.md:19-20`) | issue #9: "каждая сторона создаёт поле с 25 hit points, хотя ожидаемое суммарное поведение — 25"; audit `v3.md:30`: "**10** карт с обеими ветками (`beam_up` 10, `beam_down` 10, пересечение 10); `hitPoints = 25` на поле (`LevelObstacles.swift:766`) ⇒ 2×25"; base code: `TMXLevelRuntime.swift:356-360` creates one `ForceFieldBarrier` per `beam_` marker, `LevelObstacles.swift:766` `private var hitPoints = 25`; harness artifact: 10 `BEAM` lines, `boxes=2 fields=1` | **VERIFIED** (and the quoted Russian in `brief.md:52-53` is verbatim from issue #9) |
| 1.11 | P1-1 is wave-B scope (title, Problem, In-scope, AC-002, tasks 4) | `gh issue view 5 --json labels`: issue **#5 is labelled `wave-A`**; #6/#7/#9 are `wave-B` | **DRIFT (governance)** — the tracker assigns P1-1 to wave A; `brief.md:58` assumes wave A only carries the event log |

## 2. Faithfulness to the merged measurement files (`20260921-...-2e7698`)

| # | Claim | Primary source | Verdict |
| --- | --- | --- | --- |
| 2.1 | `brief.md:15-16` "measurement in the merged P1-11 package evidence: `…/evidence/analysis-p1-2-spawn.md`" | file exists, tracked (`git ls-files --error-unmatch` OK), and §2 does publish `{0:37, +16:59, −16:29}` from three measures (static replica, executed product Swift, `v3_measurements.py`) | **VERIFIED** |
| 2.2 | AC-001 "reproduces the audited split" as control | reproduced exactly in `wave_b_deltas.md` (my independent re-tally of the 125-row table: `{0:37, 16:59, −16:29}`) | **VERIFIED** |
| 2.3 | The merged file's load-bearing corrections are absent from the wave-B prose: 37≠correct (34 truly-clean; L01S09/L04S16 stand on the invisible plane, L03S10 spawns inside a solid), "walk-locked at spawn 61 maps, hard-locked 28", stage-start blockers L04S01 (zone 075) / L05S01 (zone 100), and "deprecate the JSON one-column method for gating" | `analysis-p1-2-spawn.md:§2, §3, §7` | **DRIFT (omission)** — the docs quote only the histogram; note the meter *does* honour the substance: exactly the 3 maps the merged file called fake-clean are the only delta-0 maps the fix moves (`L01S09→80`, `L03S10→96`, `L04S16→80`) |
| 2.4 | AC-001 amendment: "the previous unbounded rule relocated **91/125** spawns (**45 by 32 px, 5 by 112-208 px**)" | committed `wave_b_deltas.md` new-vs-marker tally = `{0:34, 16:38, 32:45, −16:3, 112:1, 176:1, 192:1, 208:2}` → moved 91 ✓, 45 at 32 px ✓, 5 in 112-208 ✓; and those 5 maps (`L01S11 +192`, `L01S21 +176`, `L02S24 +208`, `L04S01 +112`, `L05S24 +208`) are *exactly* the 5 far-anchor maps `analysis-p1-2-spawn.md:§4` predicted | **VERIFIED** — strongest faithfulness signal found; the merged prediction held map-for-map |
| 2.5 | `brief.md:23` "`evidence/p1-1_piston_probe.py` already measures this on main" | ran the probe with `--root /home/pall/projects/exolon` → `RESULT: ALL_P1_1_MEASUREMENTS_MATCH_REPORT`, detail rows 46; with `--root` on the wave-B tree → `RESULT: MISMATCH`, sole failing key `pistons_case_groundy_source` (source guard, not geometry) | **VERIFIED** for "on main"; the probe is red on this branch **by design** and `tasks.md:52-56` owns that |
| 2.6 | AC-002 control "old object-row anchor FAILS the same predicate"; `EXPECTED["piston_lethal_old"]` = 3 (20:25) → 6 (20:29) | merged probe `product_model_localfloor.lethal_area = 3` (old anchor vs local floor) — the number wave-B first pinned; `analysis-repo_explorer.md:31-37` re-derives 40 edge-only + 3 lethal + 3 no-cell = 46, arithmetically consistent with the probe (probe `edge_only=42` = 40 + the 2 shaft pistons its ±40 px band rescued) | **VERIFIED (value 3 is faithful)** |
| 2.7 | `tasks.md:31-38` "the three void-shaft pistons (L01S15 x128, L02S23/L05S23 x400) **were unclassified there** [in the merged probe]" | probe `--json` detail: `L01S15 x128 → floor_used=None` (the probe's only `no_support`); `L02S23 x400`/`L05S23 x400 → floor_own=None, floor_band=64, floor_used=64` → classified `edge_only`, **not** unclassified | **DRIFT** — stated cause explains 1 of 3; the real 3→6 gap is the probe's ±40 px band reference (correctly stated at `analysis-repo_explorer.md:36-37`), so `tasks.md` and the analysis file disagree with each other about why a pinned audit number moved |
| 2.8 | `brief.md:39` "Piston `groundY` from the Collision cell under the piston base" | meter `SurfaceMirror.walkable_piston_surface()` returns `self.plane` (= `min(cell top)`, column-blind) when the span holds no cell; `EXPECTED["piston_from_plane_fallback"]=3` and `wave_b_deltas.md` names them (`L01S15 x128`, `L02S23 x400`, `L05S23 x400`) | **DRIFT** — 3/46 anchor to the global plane, not to a cell under the base; `tasks.md:39-45` documents it, `brief.md` does not |

## 3. `ORIGINAL_MECHANICS.md` attribution check

| # | Claim | Primary source | Verdict |
| --- | --- | --- | --- |
| 3.1 | Any wave-B claim attributed to `ORIGINAL_MECHANICS.md` | `grep -rn ORIGINAL_MECHANICS` over the whole change package (docs + `evidence/*.py|md|txt|swift`) → **0 hits** | **N/A — no misattribution exists**; the doc is simply never cited |
| 3.2 | Substance of the only mechanic-relevant wave-B claim ("one shared 25-HP pool per beam pair", ruling 2) | `ORIGINAL_MECHANICS.md:26` "The vertical force field counts blaster hits and disappears on the 25th hit; award is 1000 points"; `:121-127` "## Vertical force field … Extends vertically from its source marker until the next no-walk cell … Exactly 25 blaster hits destroy it (13 trigger pulls with double-shot…)"; `:162` "Zone 035: 25-hit force field" — the doc speaks of **one** field per source marker and never mentions `beam_up`/`beam_down` or pairing | **UNSUPPORTED-BY-SILENCE (low)** — the "25 total per pair" reading is carried only by issue #9 + audit `v3.md:30`; the mechanics doc neither confirms nor forbids it. Data supports the pair reading: the two markers sit in adjacent sourceX columns (L02S11 up@x288/sourceX18, down@x304/sourceX19; L02S17 mirrored), so their 48-px boxes overlap 32 px in 10/10 maps — one visual barrier, two halves. Cite it explicitly instead of leaving the primary source unengaged |
| 3.3 | Merging two fields cannot regress the score the mechanics doc pins at 1000/field | base code has no award on force-field destruction (`git grep ForceField.*score\|1000` → none; `GameScene.swift:401` only calls `hitByBlaster()`) | **VERIFIED (no risk)** — and it exposes that `ORIGINAL_MECHANICS.md:26/:125` award is unimplemented at base; out of wave-B scope |
| 3.4 | `architecture.md:16-17` "the loader is already SpriteKit-free" | `TMXMapLoader.swift` at base imports only `CoreGraphics`, `Foundation` | **VERIFIED** |

## 4. Audit report rows P1-1 / P1-2 / P1-3 / P1-5 — cited vs actual

(`engineering/reports/exolon-full-audit-20260920-v3.md`, rows at lines 26, 27, 28, 30; `Exolon/GameCore`
is byte-identical between the audit HEAD `52795d1` and the route base `295690b` — `git diff --stat` empty,
so every row cite below was checked against the same code the auditor saw.)

| # | Row | Cited by wave-B | Actual row text / verified state | Verdict |
| --- | --- | --- | --- | --- |
| 4.1 | P1-1 `v3.md:26` | `brief.md:11` (generic), `architecture.md:8` | "Якорь берётся из **собственного низа маркера**, а не от **ходовой поверхности**" — wave-B renders it as "taken from the object tile row, not the real Collision surface below" (`brief.md:21-22`): acceptable paraphrase of the anchor, but combined with 1.5 it asserts a direction the row states oppositely ("43 стоят **ниже** ног"); row's lethality split is **1 area / 2 edge / 43 below** under *its own* model, vs wave-B's 3 (probe model) and 6 (meter) — three different models, only the last two named in wave-B | **DRIFT** (direction + unflagged model-dependence of the lethal count) |
| 4.2 | P1-2 `v3.md:27` | `brief.md:14`, AC-001 | numbers match exactly; the row also carries "По методу закоммиченного JSON … `exact 35`: обе меры даёт один артефакт" — wave-B keeps only one measure and labels it "exact" (see 1.3) | **VERIFIED numbers / DRIFT wording** |
| 4.3 | P1-3 `v3.md:28` | `brief.md:17-18` | `BlasterBullet.swift:42`, `Player.swift:128`, 512 width, `61/125 … при x≥512` — all reproduced live and in code | **VERIFIED** |
| 4.4 | P1-3 row's own cite "`GameConstants.swift:6` логическая ширина 512" | not inherited by wave-B | the declaration is at `GameConstants.swift:5` (`:6` is `fixedTimeStep`) | **UNSUPPORTED (in the source itself)** — one off-by-one in the audit; harmless to wave-B, but it is the doc wave-B names as authority |
| 4.5 | P1-3 "screen-transition trigger (x>510)" (`brief.md:36`, AC-004, `architecture.md` n/a) | cited to issues #5/6/7/9 collectively (`brief.md:11-12`) | **no issue and not audit P1-3 mentions 510**; it is `GameScene.swift:610` `guard player.position.x > 510` (base) and audit rows P1-8/RT-05 mention `x > 510` for *other* findings. Still present at 20:31 in the working tree (unchanged) | **VERIFIED against code, DRIFT on attribution** — the docs' blanket "numbers from … issues #5/#6/#7/#9" over-claims for 510 |
| 4.6 | P1-5 `v3.md:30` | `brief.md:19-20`, AC-003 | `10` maps both branches, `hitPoints = 25` at `LevelObstacles.swift:766`, "⇒ 2×25", where = `TMXLevelRuntime.swift:356-360` — every one reproduced (code lines confirmed at base; meter expects `beam_markers=20 / beam_maps=10 / fields=10 / total 250 / old 500`, artifact shows 10 `BEAM boxes=2 fields=1`) | **VERIFIED** |
| 4.7 | `architecture.md:26` "same space as wave A's **§7.6 rule 6**" | — | no such section exists anywhere in the tree (`grep -rn "7\.6"` hits only unrelated PostgreSQL/percentage strings); wave A has no change package in this worktree and `origin/codex/wave-a-gameplay-log-tick-fixes-20260924` == `295690b` (no commits) | **UNSUPPORTED** — dangling cross-reference to a document that does not exist yet |
| 4.8 | `analysis-repo_explorer.md` file:line pins | self-cited as base-tree pins | `Player.swift:291-297` ✓, `Player.swift:182-201` (+inset 3 @187, tol 1.5 @192) ✓, `GameConstants.swift:15` `48×64` ✓, `TMXLevelRuntime.swift:65-68` ✓, `:287`-vs-claimed **`:289-292`** ✗ (289 = `rootNode.addChild`, 291 = `case "capsule"`), `:356-360` ✓, `LevelObstacles.swift:329-346` ✓, `GameScene.swift:610` ✓, `Player.swift:127-128` ✓; `BlasterBullet.swift` cull claimed **:41**, actual **42**; bullet node size claimed **:24**, actual **23**; `ForceFieldBarrier` claimed `:770-796` while the cited `hitPoints = 25` is at **766**, outside the range; fallback plane claimed `:74-81`, actual `:72-78` | **DRIFT (4 off-by-one/two line pins)** — every *value* is right, four *anchors* are not |
| 4.9 | `analysis-repo_explorer.md:27-28` "46/46 piston markers carry `w=48,h=64` except one `w=h=0` point marker on L01S03" | corpus: 45 with (48,64), 1 with no width/height attributes, and it is `L01S03.tmx x=432 y=288` | **VERIFIED** (self-contradictory "46/46 … except one" phrasing; the fact and the map are right — and it is exactly the 1 piston where the probe's two anchor models agree, matching `anchor_models_differ_objects=45`) |

## 5. Invariants and current-state checks

| # | Claim | Evidence | Verdict |
| --- | --- | --- | --- |
| 5.1 | INV-001 `int(zoneNumber) == (stage-1)*25 + (scene-1)` "for all 125 TMX files" | independent re-run over the corpus: 117 files carry `zoneNumber`, 8 do not (`L01S01`…`L01S08`), **0** formula violations among the 117; `wave_b_check.py` pins `zone_number_present=117` | **VERIFIED (formula) / DRIFT (scope wording)** — cannot hold "for all 125"; the meter correctly treats the file name as canon |
| 5.2 | INV-002 "player clamp (544) … **byte-stable** across the change" | value holds (`playerMaximumCenterX = logicalSize.width + 32` = 544, `GameConstants.swift:31`), but `Player.swift:128` was rewritten to the named-constant form at `:129`, and `wave_b_check.py:667-669` **requires** that rewrite (`check(re.search(r"position\.x = min\(max\(position\.x, GameConstants\.playerMinimumCenterX\)…")`) | **DRIFT** — "byte-stable" is false as written for the clamp expression while the meter demands it changed; the numeric geometry (510 @ `GameScene.swift:610`, 512×384 @ `GameConstants.swift:5`, 544) is stable. Suggest "value-stable" |
| 5.3 | FORBID-001 "no edited TMX content" | `git status --porcelain -- '*.tmx'` → empty; 7 modified files are all Swift | **VERIFIED** |
| 5.4 | AC-004/`EXPECTED` `maps_solid_right_of_512=61`, `max_solid_right_edge=560`, `bullet_cull_bound_new=560`, `bullet_width=16`, `cull >= rightmost` | corpus: right-most cell edge = **560** (maps are 35×16); `blasterCullMaximumX = playerMaximumCenterX + blasterBulletSize.width` = 544+16 = 560 (`GameConstants.swift:42`); bullet 16×2 at `BlasterBullet.swift:23/:30`; artifact `GEOMETRY … cullMaxX=560.0 … bulletW=16.0` | **VERIFIED** — and the bound is derived, not literal, as ruling 3 demands |
| 5.5 | AC-003 "sum of field hit points equals 25 × number of pairs" | 10 pairs (artifact `BEAM` lines `fields=1`, `boxes=2`) → 250; old 20 pools × 25 = 500; artifact `BEAMPOOL sharedHitPoints=25 … destroyHitIndex=25 … remaining=0` | **VERIFIED** |
| 5.6 | Spec ↔ evidence desync introduced by the 20:31 AC-001 amendment | AC-001 (20:31:17) now forbids any spawn moving >16 px vs marker, but the meter frozen at 20:25:50 still pins `spawn_new_vs_marker_hist = {0:34, 16:38, 32:45, −16:3, 112:1, 176:1, 192:1, 208:2}` and the committed `wave_b_deltas.md` (20:27) still tabulates the **rejected** rule (45 maps at +32, 5 at +112…+208) | **OPEN BLOCKER (not a citation defect)** — as snapshotted, AC-001's own cited test would fail against AC-001's own committed evidence; the amendment text is faithful to that evidence (2.4), the *code* has not caught up |

## 6. Controls used in this pass

* Predicate-equivalence probe on the canonical parser (`/tmp/cite_ctl_probe.py`) with a contradictory
  control cell (`sx=504`) that **must** split A/B — it did (`A=False, B=True`), so the 61=61 agreement
  in 1.9 is a proven equivalence, not a broken discriminator.
* Re-ran the merged `p1-1_piston_probe.py` twice (main tree = green, wave-B tree = red on one
  source-guard key) so "already measures this on main" was tested on both sides of the claim (§2.5).
* Re-tallied `wave_b_deltas.md` (125 spawn rows) rather than trusting the meter's summary; that is how
  2.3/2.4/5.6 were separated.
* Every `file:line` in §4 was resolved with `git show 295690b:…` (not the working tree) because the
  writer has modified 7 of those Swift files in flight.
* `wave_b_check.py` was **not executed**: it unconditionally writes `wave_b_deltas.md` and
  `wave_b_harness/last-run.txt`, which would have mutated the package and raced the writer. Its
  committed outputs were read instead, and the artifact mtimes are recorded above.

## 7. Verdict tally (35 checks)

* **VERIFIED — 19**: 1.1, 1.4, 1.7, 1.8, 1.9, 1.10, 2.1, 2.2, 2.4, 2.5, 2.6, 3.3, 3.4, 4.3, 4.6, 4.9, 5.3, 5.4, 5.5
* **DRIFT — 9**: 1.2, 1.3, 1.6, 1.11 (P1-1 is labelled wave-A), 2.3, 2.7, 2.8, 4.8, 5.2
* **Mixed — numbers right, wording/frame wrong — 4**: 4.1, 4.2, 4.5, 5.1
* **UNSUPPORTED — 3**: 1.5 (piston direction inverted against all three sources), 4.4 (audit's own `GameConstants.swift:6`), 4.7 (dangling "wave A §7.6")
* **Other — 3**: 3.1 (no `ORIGINAL_MECHANICS` attribution exists anywhere in the package), 3.2 (unsupported-by-silence, low), 5.6 (**1 blocker**)

No cited **count** turned out wrong: 37/59/29/125, 46/27, 528/544/512/560/61, 25/50, 250/500/10 pairs,
117 zoneNumbers all reproduce from primary sources. The defects are in *direction* (1.5), *reference
frames and labels* (1.2, 1.3, 1.6, 2.8), *attribution* (4.5, 4.7, 3.2), *line anchors* (4.8) and one
*cause explanation* that is right for 1 of 3 cases (2.7).
