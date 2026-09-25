# Tasks — wave B (write owner: `general_implementer`)

1. [x] Explore and pin the four exact seams (file:line) into `evidence/analysis-repo_explorer.md`
      (this route's read wave may already provide it; otherwise the implementer records it before
      editing — characterization first).
2. [x] Surface query: implement/extend ground_y(x) on the SpriteKit-free loader path; unit tests
      against TMX cells (solid run, gap, top-row).
3. [x] RED→GREEN P1-2: spawn configure uses the shared query; meter over 125 maps reports
      125/125 delta==0 and prints the 37/59/29 baseline from the old computation as control.
      → Delivered per AMENDED AC-001 (amendment 2 of 2026-09-24): bounded ±one-tile window with
      body-clear as PREFERENCE; 119/125 feet sit exactly on a Collision top (delta 0), 48 of them
      are nearest-in-window picks where the defect window holds no clear top (no-worse-than-base:
      buried 61→48), 6 no-surface maps stay unmoved and are enumerated with reasons in
      `wave_b_deltas.md`; no spawn moves >16 px; old-rule control reproduces 37/59/29.
4. [x] RED→GREEN P1-1: piston anchor via query; extend the merged `p1-1_piston_probe.py` math into
      `wave_b_check.py` (46/46 reach foot band; control: old anchor formula fails).
5. [x] RED→GREEN P1-3: cull bound from clamp constant + bullet width; unit test the old-vs-new
      corridor (528 vs ≥544+w); 61-map right-Collision class covered by data meter.
6. [x] RED→GREEN P1-5: shared 25-HP field for beam pairs (both segments, one pool, one
      destruction); meter: sum of beam HP per map == count(beam pairs)*25 for all maps.
7. [x] `evidence/wave_b_check.py` with EXACTLY the change-spec test names; stdlib-only; all green;
      contradictory controls actually fail (revert flag / old-formula recomputation).
8. [x] `swiftc -frontend -parse` all touched Swift; run loader harness if extended.
9. [x] `python3 scripts/grok_verify.py --mode pr` — recorded PASS at tree fingerprint
      `a5ad67be5a00bc4b…` (receipt `.grok-stack/runtime/receipts/35bac25f12ae/verification.json`,
      status=pass, 2026-09-24T22:02:59Z; re-confirmed by the test reviewer via
      `util.tree_fingerprint`). Earlier prose quoting `9491fdcaa2…` as the receipt binding was
      WRONG — that is the writer's own monitored-scope content hash (Exolon+evidence), never a
      receipt field; corrected here. All evidence is generated write-once before a gate run;
      the two delta reviews drifted the tree to `06404364af73cc29…`, so after this micro-batch
      the controller re-records the gate at a NEW fingerprint (receipt + binding are the
      controller's operations, not this writer's).
10. [x] tasks/evidence updated; NO git commit/push (controller owns git).

## Deviations

- **P1-2 rule is AMENDED AC-001 (bounded ±one-tile window with body-clear as a
  PREFERENCE, not a filter).** History kept on the record: the first implementation
  used an unbounded nearest-body-clear anchor (relocated 91/125 spawns, 45 by +32 px,
  5 by 112–208 px — rejected by `audit-repo_explorer.md` §Q1); the amendment-1 code
  deleted the preference wholesale; amendment 2 restored it as a preference inside
  the window. Delivered: among Collision tops of the foot span within
  [marker−tile, marker+tile], a body-clear top shadows a buried one (tie → lower);
  no clear top exists → nearest is still taken; empty window → marker UNMOVED and
  enumerated. Corpus results (all in `wave_b_deltas.md`): 119 matched (delta 0 vs
  query; 71 via clear-pool, 48 nearest-in-window where no clear top exists in the
  defect window), 6 kept (L01S17, L02S24, L03S06, L04S09, L04S19, L05S24), no move
  exceeds 16 px, and NO-WORSE-THAN-BASE holds: spawns with the body inside solid
  went 61 (base 295690b) → 48 (after). Transparency: on this corpus plain-nearest
  and preference select identically for all 125 maps — the preference is proven by a
  synthetic fixture control in `controls_flip` (nearest top buried, clear top one
  tile away → clear wins) and by the source guard `clearBest ?? anyBest`, not by a
  corpus number. Disclosure: runtime consumes resolved spawn Y only at stage-start
  entries/app start/death respawns (carried-Y, `GameScene.swift:638-646`) — ~5-6
  entries per playthrough; the deeper walk-lock repair of `analysis-p1-2-spawn.md`
  §3 stays out of this wave's bounded scope (factory data fix / separate change).
- **Old-anchor piston control counts 6/46, not the merged probe's 3/46.** The merged
  `p1-1_piston_probe.py` classifies L02S23/L05S23 x400 as `edge_only` (its band
  reference finds the 3-columns-away floor at y=64 and its reference has no
  fallback-plane concept), and lists L01S15 t128 under `no_support`. Under real
  product physics a player whose hit span has no Collision cell at or below the tread is held
  feet-on the fallback plane (48 on both maps), where the old `[0,64]` hitbox already
  overlaps by 16 px — so the honest old-anchor lethal set is 3 (floor-anchored:
  L01S03, L01S10×2) + 3 (plane-grazing: L01S15 t128, L02S23/L05S23 x400) = 6.
  The AC-002 control predicate ("all 46 lethal under the fix; old fails it")
  holds under either reading (6 < 46). Aligned with `audit-repo_explorer.md` §Q1.
- **Piston prose corrected in code (audit §Q6.3):** 40 pistons sat 64 px below the
  surface under the marker-row anchor, 3 shaft pistons 48 px below, 3 were already
  correct — comments in `TMXMapLoader.pistonGroundY` and the runtime `case "piston"`
  now state that; "43 of 46 float" wording is retired everywhere.
- **P1-5 scoring side effect (for the PR body):** clearing one beam pair now awards
  1000 points once (destruction fires per field, not per side) — previously a
  player could earn 2×1000 per pair. This restores the documented single award
  (`ORIGINAL_MECHANICS.md:26`, `:121-127`: one field per source marker, 25 hits,
  1000 points). Transparency about the ruling itself: `ORIGINAL_MECHANICS.md`
  words one field PER MARKER; the shared-pool pair reading is ruled by issue #9
  ("ожидаемое суммарное поведение — 25") plus the corpus data (10/10 maps carry
  exactly one up/down pair in adjacent columns, boxes overlapping 32 px), and is
  stated as such in `architecture.md` (Decisions) and in code.
- **Beam pairing is geometric (x-interval overlap), not name-based**, with a
  deterministic `(minX, markerIndex)` sort tie-break on BOTH sides (audit §Q4)
  and a meter-enforced precondition that the corpus contains no equal-minX
  beam-box pairs; groups compare byte-exact against the executed-Swift artifact.
- **FORBID-001 scan now covers ADDED lines of all changed product files via
  `git diff 295690b`** (audit §Q2 gap): ±16 offsets, 528/544/560 literals and
  map-name references on any added Swift line fail the check. The two pre-existing
  per-map tables in `TMXLevelRuntime.swift` (ship gate ~:450, backdrop patterns
  ~:530-535) are explicitly baselined — untouched legacy, any future edit to them
  must pass the same added-line scan. Body height (63) is parsed from
  GameConstants, not pinned.
- **Merged-package probe drift is expected and acknowledged:**
  `p1-1_piston_probe.py` (its `pistons_case_groundy_source` guard literally demands
  `groundY: bottom.y`) is green on main and red on this branch BY DESIGN — it was
  authored to prove the defect exists, exactly like the §Q1/§Q6 posture of the audit
  wave; its rewrite belongs to the report owner (`analysis-p1-7-markers.md` §6
  conclusion), not to this wave. Same applies to the historical
  `v3_measurements.py` expectations (`bullet_kill_bound=528`, per-side `hitPoints=25`).
- **Dead-code/disposition pass (audit §Q6.7/§Q6.8):** no-arg
  `TMXMapData.resolvedPlayerBottom()` convenience and the full-column
  `groundY(x0:x1:)` overload removed; `beamFields` retained deliberately as the
  owner-visible field registry with the reason stated in code; the surface query
  is now built exactly once per level load and injected into the renderer
  (`TMXTileMapRenderer(map:surfaceQuery:)`).
- **AC-004 (amended) coverage — grenade and muzzle-reach added to the blaster fix.**
  The blaster bound is now `clamp + muzzle(34) + width(16)` = 594: origin = x+34 means
  the old 528 cull killed shots fired from x ∈ (494,544] at the first update, and
  origins above clamp+width (560) — fired from x ∈ (526,544] — would have been born
  dead even under the amendment-1 bound. Player origins and both cull bounds read the
  same named constants so the two cannot drift.
  Grenades had the same birth defect inline (`x > logicalSize.width + 24` = 536 <
  reachable origin 548); `Grenade.swift` now uses `grenadeCullMin/MaximumX` derived
  by the identical formula, and the meter pins that the remaining 528-literals in
  the tree are SPAWN positions (BubbleSpawner, HomingMissile start), never culls.
- **Beam field/side ownership (audit §Q6.5):** `BeamFieldModel` publishes an
  `onDestroyed` handler list and the runtime registers `{ [weak side] in
  side?.coverDestroyed() }` per side — the previous single stored closure strongly
  captured the sides array and formed a field↔side retain cycle leaking every
  visited beam. `beamFields` remains as the deliberately-retained owner-visible
  registry (documented in code).
- **Integration order (controller notes 2026-09-24, final):** series is A → B → C —
  this wave rebases once, onto post-A main; wave C's `classify()` rewrite lands
  AFTER us and will take the one mechanical conflict at the `source_marker` beam
  hunk (their classifier arm vs our beam-box collection — our call sites are kept
  localized to that hunk on purpose). After the A-rebase, re-run
  `wave_b_check.py` and regenerate `wave_b_swift.txt`; line anchors move, semantics
  do not.
- **Surface-query "unit tests" (task 2)** are carried inside `wave_b_check.py`
  (`controls_flip` broken/garbage-fixture probes + synthetic tie-group determinism
  probe) and the live Swift harness — the repo has no `tests/` tree and the route's
  quality profile runs no pytest.
- **Meter runtime**: live Swift rebuild + full corpus in ≈3 s (<60 s budget); a host
  without `swiftc` no longer passes silently — it exits `RESULT: TOOL_ABSENT` rc=3
  (distinct, non-green) unless the operator explicitly opts into `--artifact-only`.

## Review close-out (code BLOCK R1-1 + test F-1/F-2, 2026-09-24 21:4x)

- **R1-1/F-1 (BLOCKING) — the rect check was a tautology, now falsifiable.**
  `query_collision_rects()` used to `return self.old_collision_rects()`, so
  `pinned_geometry_unchanged`'s "rects идентичны на 125/125" could not fail (the
  reviewer patched the product merge `y: run.top - tileHeight`→`+ 7.5` and the meter
  stayed green). `wave_b_check.py` now compares THREE independent sources per map,
  count + order + coordinates:
  (a) `base_build_collision_rects()` — a Python port of the DELETED
  `git show 295690b:…/TMXTileMapRenderer.swift` while-merge, reading the Collision
  gids directly (string-anchored to the base blob so the port cannot silently drift);
  (b) `query_collision_rects()` — a real port of the NEW `TMXSurfaceQuery.collisionRects`
  (unique tops insertion-order → sort desc, per-top cells sorted by x0, merge on x0==run.x1);
  (c) the EXECUTED product rects via new `RECTS map= count= coords=` harness lines
  (%.1f), so a product-geometry mutation now reddens INV-002. All 125 maps agree;
  total = **1437 rects** (`renderer_rects_total`), matching the code reviewer.
  `controls_flip` adds a synthetic mutant battery (y+7.5, reorder, base-shift) proving
  the comparison actually flips. Live ablation `wave_b_ablations.txt` §M12 (`+7.5`)
  reddens `pinned_geometry_unchanged` (0/125, 0!=1437) and §M13 (spawn halfWindow×2)
  reddens `spawn_ground_all_maps`+`controls_flip`; both restore to green.
- **R1-1 artifact regeneration:** `wave_b_swift.txt` now carries 125 `RECTS` lines
  (byte-equal live-vs-committed under the meter).
- **R1-2 — ACCEPTED PERMANENT RESIDUAL (owner constraint 2026-09-25: no macOS
  hardware/Developer ID exists, so the eyeball is structurally unrunnable, not merely
  unperformed).** With corrected anchors 43/46 pistons draw the 64-px retracted sprite
  inside the ground band (`node.position.y=groundY-travel`, `zPosition 10` over tiles;
  only the hitbox is gated, never the sprite). Risk is documented and bounded: hitbox
  lethality is meter-proven (46/46, old 6/46); the sprite sits below the tread surface
  its own anchor derives from, so the exposed-phase look is what the meters pin; worst
  case is an art-overlay difference during the waiting phase only. Candidate one-liner
  `node.isHidden = (phase == .waiting)` stays recorded here for whoever owns hardware.
  Wave A's merged precedent shipped the same class of visual checks as meter-proven +
  accepted residual. `release.md` go/no-go updated accordingly.
- **Reviewer prose items applied:** piston `pistonGroundY` doc corrected (D-1): the three
  shaft spans L01S15 x128 / L02S23·L05S23 x400 DO carry Collision cells (tops 160/192 and
  272); the true condition is that none sits at or below the raised tread (anchor+travel=64),
  so the query resolves to the GLOBAL `fallbackPlaneY` (lowest cell top in the map = 48 on all
  three), not a local floor. Verified directly from the TMX in this session.

## N-list disposition (review-test-delta; acknowledged non-blocking, intentionally unapplied)

- **N-1** AC-004 executed-constants cross-check `if geom:` skip-vs-fail: acknowledged. Only
  reachable via a hand-doctored artifact (a missing toolchain already exits TOOL_ABSENT rc=3),
  so it is not an exposure under normal gate conditions; left as a nit to keep this micro-batch
  prose-only.
- **N-2** battery wording blames the control when the *product* diverged: acknowledged. The
  verdict is still a correct red on the right check; message-only, no action.
- **N-3** `fmt` prints `%.0f` so SPAWN/PISTON/PLANESRC columns can't show sub-tile drift while
  `RECTS` uses `%.1f`: acknowledged. Every pinned product quantity is on the 16 px tile grid,
  so integer precision is exact for the values asserted; the "пиксель-в-пиксель" claim is about
  those integer surface/anchor values, not sub-pixel. Not changing fmt in a prose batch.
- **N-4** `--artifact-only` still returns rc=0 on a mutated product: acknowledged, by design —
  it is the explicit operator opt-in for offline review that trusts the committed artifact (the
  line prints `коммиченный (--artifact-only)`). Pinning the artifact SHA-256 in `EXPECTED` would
  harden even offline mode; deferred as non-blocking.
- **N-5** ablation count refreshed to **14** mutation sections (A1–A8, B1–B4, M12, M13) across
  `release.md`, tasks.md, and the green-transcript header; two glued transcript headings and the
  empty `### R1-1 battery` header tidied. Done this batch.
- **N-6** `PLANESRC`/`SPAWN.plane` parsed but not directly asserted: acknowledged. The executed
  plane is transitively bound (D12: a full-tile plane mutation reddens the 3 shaft pistons +
  controls_flip + no_magic_offsets); the extra parsed fields are informational coverage only.

## Rebase cycle onto post-A main (2026-09-25)

- `git fetch --all --prune`; `git rebase origin/main` onto `17a742a` (merge of PR #20,
  wave A). **Zero git conflicts** — the pre-declared hot zones (source_marker switch,
  Player.update clamp, GameConstants block, LevelObstacles) auto-merged by disjoint
  hunks; every seam was then hand-verified in the merged bytes: runtime query wiring
  (`surfaceQuery` once-per-load + renderer injection), `case "piston"` →
  `pistonGroundY`, beam arm → `beamBoxes` + grouping block with `[weak side]`
  handlers, source_marker arithmetic untouched, Player clamp/inset/origins on shared
  constants, LevelObstacles piston constants + side-delegates-pool barrier (A's edits
  there are confined to EggEnemy/DoubleLauncherObstacle). New head: `e520884`.
- `wave_b_swift.txt` regenerated and **byte-identical** to pre-rebase (spawnFeet,
  piston groundY, RECTS 1437, GEOMETRY) — no A-side semantic moved any wave-B number;
  therefore **no EXPECTED value was adapted in this cycle.**
- One mechanism adaptation (attribution, not a number): the FORBID-001 added-lines
  scan now anchors at `merge-base HEAD origin/main` (falling back to 295690b). On the
  rebased tree a 295690b diff classifies ALL of wave A as "added" (2731 lines /
  16 files), diluting audit scope; with the rebase base it is back to wave B's own
  237 lines / 8 files. The renderer base-port and TMX blob manifest intentionally
  stay pinned at 295690b (they are historical base anchors — controller directive).
  A added no forbidden tokens to its added lines (verified transitively: the widened
  scan still passed while it existed).
- Cross-wave courtesy check on the merged tree: wave A's own meter
  `gameplay_log_check.py` → **PASS 28/28** (incl. `producer_sites_use_helpers_only`);
  wave B diff contains no raw event emits (beam/piston paths emit nothing — only a
  doc-comment word matched the grep). All 8 wave-B Swift files + GameScene parse.
- Post-rebase meter: 9/9 `ALL_WAVE_B_CHECKS_MATCH_SPEC`, live harness == committed
  artifact (`совпал: True`), elapsed 3.0 s. Gate/receipt re-record = controller.
