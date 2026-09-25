# Code review — wave B (P1-1/P1-2/P1-3/P1-5)

Change: `20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2`
Tree: `/home/pall/projects/.exolon-wave-b/exolon` @ base `295690b`, branch `codex/wave-b-mapdata-physics-20260924`
Reviewer role: `code_reviewer` (route `35bac25f12ae`, allowed_agents includes code_reviewer). READ-ONLY: no product
or evidence file was written by this review except this file.
Object: `git diff HEAD` (8 product Swift files, +415/−87) **plus the surrounding implementation**, not the reports.

**Verdict: BLOCK — one Critical finding, and it is an evidence-integrity finding, not a product defect.**
Every stream-level numeric claim in this wave was re-derived independently and all of them hold; the product
change is correct and shippable. What fails is the meter's *published* proof of the renderer rect equivalence:
it is a self-comparison that cannot fail, while its own comment and the PASS line certify it as base-vs-new.
AC-005 of this very change states "a check that cannot fail is itself a failure", so the recorded AC-005
`verification` receipt is not supported by its own evidence for the INV-002 part.

---

## Method (independent, not the implementer's tool)

I re-implemented all four rules from the sources rather than trusting `wave_b_check.py`:

* own TMX parser (`xml.etree`, csv **and** base64/LE-u32 like `TMXMapLoader` line 549-565, map geometry confirmed
  uniform 35×24@16 on 125/125);
* base renderer merge **transcribed from `git show 295690b:Exolon/GameCore/Levels/TMXTileMapRenderer.swift`**;
* new merge, `boundedSurfaceY`, `pistonGroundY`, `fallbackPlaneY`, `TMXBeamGrouping` transcribed from the
  post-change `TMXMapLoader.swift`;
* base spawn settle model re-derived from the committed audit instrument
  `engineering/changes/20260919-.../evidence/v3_measurements.py:155` (`stable_feet`, foot span `[cx−20,cx+20]`,
  tol 1.5) — the same tool that published the 37/59/29 control;
* mutation controls on my own comparison (order-permutation and merge-breaking mutants) to prove it has teeth.

Re-runs on this tree: `python3 evidence/wave_b_check.py` → **rc=0, 9/9 PASS, elapsed 2.7 s**, live Swift harness
rebuilt and byte-equal to the committed artifact. `run.sh` verified genuinely live: it compiles the *current*
`Exolon/GameCore/Levels/TMXMapLoader.swift` + `GameConstants.swift` with a hard delta control of exactly one
import line and a negative build control (no CoreGraphics shim ⇒ must not compile).

---

## 1. TMXSurfaceQuery as the single Collision interpretation — VERIFIED (product), CERTIFICATION IS FALSE (evidence)

**No second cell-top / layer-selection rule survives.** Independent grep over `Exolon/**/*.swift`:

* `lowercased() == "collision"` (solid-cell selection) — exactly one site, `TMXMapLoader.swift:142`.
* cell-top formula `pixelHeight - CGFloat(row * tileHeight)` — exactly one site, `TMXMapLoader.swift:149`.
* remaining `pixelHeight` uses are **not** ground rules: `TMXTileMapRenderer.swift:71` places *visual* tile sprites
  for non-Collision layers (`:47` skips Collision), and `TMXLevelRuntime.swift:379/411/415/422` derive boxes from an
  object's own `sourceX/sourceY` marker properties (beacon base, control beacon, beam), never from Collision cells.
  `TMXLevelRuntime.subtract(rect:removing:)` is boolean algebra on query-produced rects, i.e. a consumer.
* one query instance per load: `let query = loadedMap.surfaceQuery` (`TMXLevelRuntime.swift:69`) feeds renderer rects
  (`:70`), spawn (`:78`), the fallback plane (`:89`) and pistons (`:310`). `TMXMapData.surfaceQuery`
  (`TMXMapLoader.swift:87`) is a computed property, so a second call *would* rebuild the cells — it is called once.
* `footSupportHorizontalInset` is now genuinely shared (`GameConstants.swift:36`, `Player.swift:188`,
  `TMXMapLoader.swift:113-115`), and I confirmed the two spans are numerically identical ([cx−20, cx+20]).

**Renderer merge equivalence: base-vs-new is NOT proven by the committed evidence.**
`wave_b_check.py:330-332`:

```python
def query_collision_rects(self):
    """Слепок нового TMXSurfaceQuery.collisionRects (тот же вход — клетки)."""
    return self.old_collision_rects()  # алгоритм совпадает; отдельный метод для честности сверки
```

`query_collision_rects` **is** `old_collision_rects`, so the 125-map loop at `:1153-1159`
(`if mirror.old_collision_rects() == mirror.query_collision_rects()`) is arithmetically incapable of failing, while
the comment at `:1141` states the opposite: `Это base-vs-new, а не зеркало-vs-себя-зеркало (audit §Q7-7)`, and the
PASS line prints `rects идентичны на 125/125`. Corroboration that this is not a theoretical gap:

* the harness emits **zero** rect geometry (`grep -c rect evidence/wave_b_swift.txt` → 0; no `collisionRects` call in
  `wave_b_harness/main.swift`), so the executed-Swing side never checks it either;
* all 12 logged ablations (`evidence/wave_b_ablations.txt`) still print `rects идентичны на 125/125`.

The only real base anchoring in that check is presence of four literal strings in the base blob (`:1146-1151`), which
proves the base *source* is the base source — not that the new algorithm reproduces it.

**The product claim itself is true.** My base-blob transcription vs my new-source transcription agree on **125/125
maps, 1437 rects, byte-order included** (rows top→bottom, runs left→right), and my comparison does have teeth:
an order-permutation mutant is caught on 113 maps and a merge-breaking mutant on 14. Equivalence holds because
`top = PH − row·TH` is injective and `cell.x0 == run.x1` reproduces consecutive-column merging; the empty-layer and
short-`gids` guards match (`cells == []` ⇒ `[]`, same as base's `return []`).
`fallbackPlaneY` (`TMXMapLoader.swift:166`) is also equivalent to the deleted `min(rect.maxY)` loop: min over cell
tops == min over merged-rect maxY, both falling back to `defaultGroundY` when there is no Collision data.

## 2. boundedSurfaceY preference rule — VERIFIED, all six "kept" maps re-derived

Implementation (`TMXMapLoader.swift:196-219`, caller `:105-124`) matches AC-001 amendment 2 line by line:
closed window `distance <= halfWindow` (`:206`) with `halfWindow = CGFloat(tileHeight)` (`:117`);
body-clear as **preference, not filter** — `return clearBest ?? anyBest` (`:219`), so an all-buried window still
returns the nearest; empty window ⇒ `?? marker.y` (`TMXMapLoader.swift:121`), i.e. unmoved; tie-break to lower Y
(`:209`, `:213`).

My independent recomputation over all 125 maps reproduces the published table **row for row**:

| published (`wave_b_deltas.md`) | my recomputation |
|---|---|
| shift vs marker `{'-16':1,'0':41,'16':83}`, MAX 16 px | identical; max \|shift\| = 16.0 |
| base control 37/59/29 | 37/59/29 (via `stable_feet`) |
| kept 6: L01S17, L02S24, L03S06, L04S09, L04S19, L05S24 | same 6 names, all marker feet 64, all `feet == marker` |
| planes 80/80/48/80/48/80 | same |
| buried base 61 → after 48 | 61 → 48 |
| clear 71 / dirty-nearest 48 / kept 6 | 119 supported-at-feet, 6 kept (same split) |
| rejected unbounded rule 91 moved / 50 beyond tile | not re-derived independently (mirror-only) — accepted from the table, it is a rejected-rule control, not shipped behaviour |

The 6 kept maps are **strict no-ops**, which I consider the decisive safety point: their new feet equal the base
spawn feet exactly (64 = 64), so the shipped rule cannot regress them; `Player.landOnFallbackFloorIfNeeded` still
raises the player to the fallback plane (80 or 48) exactly as on base.

Two honest admissions in the evidence are correct and I confirmed both: the preference never changes a pick on this
corpus (0/125 differ from plain nearest — `wave_b_deltas.md` says so, and `tasks.md:45` records it), covered only by
the synthetic fixture at `wave_b_check.py:923-933`; and the runtime exposure is limited to ~5-6 entries per
playthrough because `GameScene.swift:644-646` carries the previous zone's Y on ordinary transitions.

Real behavioural exposure (my numbers, for the PR body): relative to base's *settled* line, 91/125 unchanged,
26 maps +32 px, 2 maps +16 px, and the 6 kept maps unchanged at spawn (their −16/+16 bucket is purely the
fallback-floor settle that base also performs, so they are true no-ops); nothing moves downward versus base.
84 maps move relative to the marker (41 stay put), and all 119 non-kept maps have feet exactly on a Collision top
(`supported == true`), so none is left floating above the floor.

## 3. Beam — VERIFIED (one pool per group, delegation, no retain cycle, single debit, 1000/beam)

* **One pool per x-overlapping group:** my own grouping recomputation gives 10 beam maps, 2 sides each, **10 fields**,
  pair x-overlap exactly 32 px on every map, each pair `blk_beam_up` + `blk_beam_down` — exactly
  `wave_b_deltas.md`/`AC-003` (250 HP total vs 500 per-side on base). Code: `TMXLevelRuntime.swift:451-466`,
  `TMXBeamGrouping` at `TMXMapLoader.swift:297-318`.
* **Tie-break in grouping is real:** `if a.element.minX != b.element.minX … return a.offset < b.offset`
  (`TMXMapLoader.swift:302-304`) makes the (unstable) Swift sort total; group membership is index-based into
  `beamBoxes`, so it is order-independent. Corpus has distinct minX per pair (Δx = 16 from the 32 px overlap), and the
  meter additionally asserts distinct minX (`wave_b_check.py:761-763`) plus a synthetic equal-minX fixture
  (`:764-766`). Closing rule `box.minX >= currentMaxX` = strict overlap ✓.
* **Sides delegate:** `ForceFieldBarrier` keeps no counter — `let field: BeamFieldModel`
  (`LevelObstacles.swift:771`), `isActive { field.isActive }`, `hitByBlaster() { field.registerHit() }`
  (`:784-786`), and `coverDestroyed()` (`:788-792`) is the visual-only half. Both sides deactivate together, so the
  lethality test at `GameScene.swift:569` and the debug overlay at `:1099` now see the field as a unit ✓.
* **Retain cycle — the audit's flag is fixed.** `field.onDestroyed { [weak side] in side?.coverDestroyed() }`
  (`TMXLevelRuntime.swift:458`); the field owns the handler array (`TMXMapLoader.swift:270,279`), the side owns the
  field strongly, the closure owns the side weakly ⇒ no cycle. `destructionNotified` is set **before** the handler
  loop (`TMXMapLoader.swift:287-289`), so a re-entrant `registerHit()` from a handler cannot re-notify.
* **Single damage entry, no double debit:** the only `hitByBlaster()` call site in the product is
  `GameScene.swift:401`, reached via `forceFields.first(where: { isActive && intersects })` (`:399`) followed by
  `bullet.destroy()` + `continue`, so one bullet debits at most one point per tick even though the two side boxes
  overlap by 32 px; `registerHit()` returns true exactly once per field, so `awardPoints(1_000)` at `:403` fires once
  per beam. Per-doc behaviour (ORIGINAL_MECHANICS.md:26 and :121-127 — 25 hits, 1000 points) is respected; the pair
  reading is honestly ruled from issue #9 + corpus data, and the doc's actual wording is disclosed in the code comment
  (`TMXLevelRuntime.swift:439-450`) and `brief.md`. Double-shot counting (two bullets ⇒ two debits) still works
  because the debit is per bullet, not per trigger pull.
* **Scoring note for the PR body:** the pair award drops 2000 → 1000; already disclosed in `release.md:12` ✓.

## 4. Projectiles — VERIFIED, no inline x-literal left, alive at x=544

* Bounds are pure derivations: `blasterCullMaximumX = playerMaximumCenterX + blasterMuzzleOffsetX +
  blasterBulletSize.width` = **594**, min = −50 (`GameConstants.swift:47-50`); grenade **564**/−20
  (`GameConstants.swift:56-59`). No re-pinned 528.
* The clamp the derivation rests on is the same named constant used by the mover: `Player.swift:129`
  (`playerMinimumCenterX` 24 / `playerMaximumCenterX` 544) — so the two can no longer drift.
* **Muzzle origin alive at x=544:** origin max = 544+34 = **578 < 594** ✓ (base's 528 bound left a 50 px born-dead
  band, 494<x≤544, which I confirmed arithmetically); grenade origin max 548 < 564 ✓ (base 536 killed right throws).
* `Grenade.swift:84-86` and `BlasterBullet.swift:52-53` contain no numeric x literals; the only remaining x literals in
  the product are **start positions**, and the meter pins them as such (`wave_b_check.py` bullet_cull_bounds #5:
  `LevelObstacles.swift:420` `x: 528 + random(0...32)` and `:850` `logicalSize.width + 16`) — I confirmed both are
  spawn coordinates, not culls. `position.y > logicalSize.height + 40` (`Grenade.swift:86`) is the untouched y bound.
* Screen-transition trigger unchanged: single `player.position.x > 510` in `GameScene.swift` (INV-002).

## 5. Pistons — VERIFIED; the two numeric comments are now truthful

`pistonGroundY` (`TMXMapLoader.swift:228-233`) anchors on `groundY(x0: markerX+3, x1: +45, atOrBelow: markerBottomY+64)`
— the *hitbox* span, not the node rect — with the global plane as fallback (`:177`). Call site
`TMXLevelRuntime.swift:308-311`; `PistonHazard` uses `GameConstants.pistonTravel/pistonNodeSize/pistonHitXInset/
pistonHitWidth` (`LevelObstacles.swift:329, 335, 345-346`).

My independent recomputation over the whole corpus: **46 pistons on 27 maps**; shift distribution
**{+64: 40, +48: 3, 0: 3}** with exactly **3 plane-fallback** rows (L01S15@128, L02S23@400, L05S23@400 — no cell at or
below the limit in the tread span) and exactly **3 already-on-surface** rows (L01S03@432, L01S10@192, L01S10@64);
lethal-under-old-anchor = **6/46** (the 3 already-anchored + the 3 plane rows), lethal-under-new-anchor = **46/46**
with `groundY == walkable surface` on every row. That is word-for-word what the two comments now claim
(`TMXLevelRuntime.swift:302-306` and `TMXMapLoader.swift:222-226`), and both are new lines in this diff — i.e. the
previously-stale prose was corrected to data I could re-derive, not to data only the meter asserts.

Wording nit (see R1-4 below): for those 3 plane-fallback rows "that surface" is the *global* fallback plane, not a
Collision cell under the tread; `TMXLevelRuntime.swift:302-306` calls them "shaft pistons" without saying so.
Behavioural note for the PR body (already disclosed): 40 pistons that were edge-only and therefore harmless become
genuinely lethal — this is the point of issue #5, but it is the largest player-visible change in the wave.

## 6. Contract compliance / paperwork — HONEST, but the local gate receipt no longer binds

* **No data edits (blob-proven, my own re-derivation):** `git ls-tree 295690b` blob sha1 == manifest value ==
  `git hash-object` of the working file for **125/125** TMX (`tmx_base_hashes.json`, whose
  `generated_from_commit` really is `295690b…`). The only changed tracked files are the 8 Swift product files;
  nothing else in `git diff --name-only HEAD`.
* **No dependencies:** zero added `import` lines in the diff, no `Package.swift`/`Exolon.xcodeproj` change, no new
  files under `Exolon/`; the only new import is inside the evidence harness copy (`run.sh` awk, delta-controlled).
* **FORBID-001 (no magic offsets):** every new literal is either a *named* constant lifted out of pre-existing inline
  code (42/3/64/16×2/34/16×16/4) or a derivation; `±16` and `528`/`544`/`560` appear only in comments. The
  added-lines scanner plus my own read agree.
* **Backward-compat claims are honest:** `release.md:10-16` matches my recomputation exactly (spawn ±16 on 119,
  6 enumerated unmoved, 48 buried ≤ base 61, grenade 536→564-class, beam award 2000→1000,
  `git status Exolon/Resources` empty). No API/contract/persistence surface is touched, so "no flags" is credible.
* **`rollback.md` coherence: good.** Single `git revert <merge>` is genuinely sufficient (code-only, data untouched,
  no state or migration); the stated post-revert expectations are the numbers I independently reproduced
  (37/59/29, 6/46, 500 HP, 528), and the two carried debts it names are real and verified — 48 body-in-solid spawns
  (needs factory `vitorc` regeneration) and beam route-opening (destroyed field is still solid in the Collision layer;
  unchanged by this diff, `GameScene.swift:415` still blocks on `terrainRects`).
  One caveat: "`controls_flip` and `pinned_geometry` checks must stay GREEN after revert" is over-broad.
  `single_surface_query` asserts the *absence* of `buildCollisionRects` in every product file and the presence of
  `collisionRects = surfaceQuery.collisionRects` — both invert on a revert — and `pinned_geometry_unchanged` reads the
  new named constants (`playerMinimumCenterX`, `pistonNodeSize`, `pistonHitXInset/Width`, `blasterCullMinimumX`) at
  `wave_b_check.py:1131-1137`, which a revert deletes outright (KeyError). Expect both to redden; a documentation error
  in the rollback verification list, not a product problem.
* **Gate receipt is stale (process, R5):** `.grok-stack/runtime/receipts/35bac25f12ae/verification.json`
  (`kind=verification`, `status=pass`, criteria `AC-005`) was recorded 21:25:59 against tree fingerprint
  `caea24c8…`; recomputing with the same helper (`adaptive_grok.util.tree_fingerprint`) now gives **`1b4a8398…`**.
  Cause: `tasks.md` (21:28:57), `release.md` + `rollback.md` (21:30:21) and later reviewer evidence landed after the
  gate. Not caused by running the meter: `write_if_changed` kept `wave_b_deltas.md` byte-identical through my run
  (mtime still 21:21:25) and `__pycache__` is git-ignored, so it does not enter the fingerprint. The gate must be
  re-recorded after all writers/reviewers settle.

---

## Findings

| id | sev | conf | file:line | summary |
|---|---|---|---|---|
| R1-1 | Critical | high | `engineering/changes/20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2/evidence/wave_b_check.py:330-332` | The published base-vs-new proof of renderer rect equivalence is a self-comparison that cannot fail (`query_collision_rects` returns `old_collision_rects`), yet `:1141` certifies it as "base-vs-new, не зеркало-vs-себя-зеркало" and the PASS line prints `rects идентичны на 125/125`; all 12 ablations still print it, and the live harness emits no rect data at all. Violates this change's own AC-005 ("a check that cannot fail is itself a failure"). The *product* claim is true — I proved it from the base blob independently (125/125, 1437 rects) — so the fix is the meter, not the code. |
| R1-2 | Suggestion | medium | `Exolon/GameCore/Objects/LevelObstacles.swift:337-338,354` | Piston sprites are drawn over the ground while retracted. `node.position.y = hiddenY = groundY − 64` with `node.zPosition = 10` on a node whose map sibling is `z = 0` (`TMXLevelRuntime.swift:100`), and only the *hitbox* is gated (`:344`), never the sprite. Quantified from my own recomputation: at base the retracted sprite was fully off-screen on 16/46 and clipped to 16-32 px on 27 more, while with the corrected anchors **43/46 now draw all 64 px inside the ground band** (3 draw 48 px). Needs a runtime visual check (I cannot launch the SpriteKit target here); `node.isHidden = (phase == .waiting)` or dropping the piston below the tile layers is the one-line candidate. |
| R1-3 | Suggestion | high | `Exolon/GameCore/Levels/TMXMapLoader.swift:209,213` | The documented lower-Y tie-break is exercised by 0/125 corpus maps and has no synthetic fixture — `controls_flip` covers only the body-clear preference (`wave_b_check.py:923-933`). Flipping `top < anyBest!` would keep the whole meter green. Add a two-equidistant-tops fixture, or state that the tie-break is a determinism guard only. |
| R1-4 | Suggestion | high | `engineering/changes/…/change-spec.yaml` AC-001 vs `Exolon/GameCore/Levels/TMXMapLoader.swift:117` | Unit drift: the spec says "within one **half-tile** (±16 px)", the code passes `halfWindow: CGFloat(tileHeight)` = one **full** tile. Equal on this corpus only because 125/125 maps are 16 px tiles; a 32 px-tile map would silently permit ±32 under an AC that promises ±16. Also imprecise prose: the 3 plane-fallback rows described as "48 px below that surface" (`TMXMapLoader.swift:222-226`, `TMXLevelRuntime.swift:302-306`) anchor on the *global* fallback plane, not a cell under the tread. |
| R1-5 | Nice to have | high | `Exolon/GameCore/Levels/TMXLevelRuntime.swift:39,465` | `beamFields` has no reader anywhere in the product (only the declaration and the append); per-side `let field` already owns the model, so the comment's "owner-visible registry" justification is ownership it does not need. Likewise `destructionHandlers` (`TMXMapLoader.swift:270,279`) are never cleared after firing — harmless (level-scoped), but it keeps every side alive via the weak-lookup until the level dies. |
| R1-6 | Suggestion | high | `engineering/changes/…/rollback.md` "Verification after rollback" + local receipt | Two paperwork defects: (a) "controls_flip and pinned_geometry checks must stay GREEN after revert" is wrong — `single_surface_query` asserts `buildCollisionRects` is absent and `pinned_geometry_unchanged` parses constants that only exist post-change (`wave_b_check.py:1131-1137`), so both redden on a reverted tree by design; (b) the recorded `verification` receipt (fingerprint `caea24c8…`, 21:25:59) no longer binds (current `1b4a8398…`) — re-run `scripts/grok_verify.py --mode pr` after all writers settle. |

### What I would accept as closing R1-1
Implement the new merge in the mirror independently of the base transcription (or, better, have
`wave_b_harness/main.swift` print `collisionRects` per map and compare that executed output against the base-blob
transcription), and add a mutant control so the check demonstrably reddens. Then re-run the meter, re-record the gate,
and re-issue this receipt. No product change is required for any finding above except, at human discretion, R1-2.

### Verified-correct highlights (no action)
Single-parse architecture is real, not cosmetic (one layer selector, one cell-top formula, one query instance feeding
four consumers); the pool model is SpriteKit-free and executed live; `[weak side]` closes the flagged cycle; the
spawn rule is bounded and no-worse by re-derived numbers; cull bounds, piston anchors and beam grouping are all
derived from named constants and Collision data with no per-map table and no edited TMX byte.
