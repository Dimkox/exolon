# Analysis P1-2 — spawn is mass-inconsistent with collision: mechanism, re-measurement, fix design

Binding: branch `codex/release-layer-p1-11-20260921`, HEAD `d4c7a58`, host Linux (no Xcode).
Authority line: `engineering/reports/exolon-full-audit-20260920-v3.md:27` (row P1-2).
TMX parsed only via `xml.etree`. No product file touched; the only repository write is this file.

## 0. How the numbers below were produced (and its integrity controls)

Two independent measures:

1. **Static replica** (`/tmp` heredoc, `xml.etree` + base64) mirroring the Swift rules.
2. **Executed real product Swift on Linux** — same technique as
   `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/`:
   - byte-identical copies (`cmp`): `Exolon/GameCore/Player/Player.swift`,
     `GameCore/GameConstants.swift`, `GameCore/InputState.swift`;
   - `Levels/TMXMapLoader.swift`: exactly +1 inserted line `import FoundationXML`
     (verified: removing line 2 restores the repo file byte-for-byte);
   - `Levels/TMXTileMapRenderer.swift:115-149` (`buildCollisionRects`) and
     `Levels/TMXLevelRuntime.swift:58-78` (spawn/ground init) and
     `GameScene.swift:268-276` (per-step order) extracted **verbatim**, wrapped only by
     signatures (one visibility word patched; diffs printed and verified);
   - shim module: Foundation re-export + a **type-only `CGVector` polyfill**
     (Linux Foundation has no `CGVector`; the game never compiled SpriteKit-dependent
     `TMXLevelRuntime`/`GameScene` — only pure-geometry product code ran);
   - one semantics patch in the extracted step line: `player.movementHitbox.intersects(solid)`
     → `cgIntersectsApple(...)` strict overlap (see §2, this is the trap that was caught).
   - Build/run scratch lives in `/tmp/p12h/` (`main.swift` idle+run+jump scenarios,
     1/60 s ticks = `GameConstants.fixedTimeStep`, 600 steps per scenario).

**Control set that must flip** (synthetic fixtures, also run through the real `Player`):
`ctl_clean` (feet on surface → rest=feet, walks), `ctl_sunk` (feet 16 into floor → +16 snap),
`ctl_float` (feet 16 above → visible −16 fall), `ctl_void` (no cells → invisible default plane
at `GameConstants.defaultGroundY=96`), `ctl_embed` (feet below a 3-row mass → snap into mass,
walk-locked, jump-escapes). In the first harness run **all five showed walk-locked** — that
was the bug detector firing: see §2 “semantics trap”. After compensation all five land on
their designed distinct values, and 125/125 executed-Swift results equal the static model
pixel-for-pixel (feet, groundY, rest−marker).

## 1. Mechanism, step by step (file:line on HEAD `d4c7a58`)

What the spawn rule computes:

1. `TMXLevelRuntime.swift:58-63` — find `object(named:"vitorc")`
   (`TMXMapLoader.swift:57-64`), map it via `worldBottomLeft` (`TMXMapLoader.swift:73-81`).
   The 125 vitorc markers are plain points: `w=h=0`, **no `coordinateMode` property in any
   of the 125 maps** → the non-rect branch runs: `bottom = (x, pixelHeight − y)`.
   `pixelHeight = 24·16 = 384` for all maps.
2. `TMXLevelRuntime.swift:65-68` — `spawnCenter = (x + 48/2, y_feet + 64/2)`
   (`GameConstants.swift:15` `playerSpriteSize = 48×64`). So **spawn feet = 384 − marker.y**.
3. `TMXLevelRuntime.swift:70-78` — the “fallback floor” `groundY`:
   `min(rect.maxY)` over **all** collision rects. `buildCollisionRects`
   (`TMXTileMapRenderer.swift:115-149`) merges only horizontal runs, one row tall, so
   `rect.maxY = 384 − 16·row` and `groundY` = **top surface of the lowest solid tile row
   anywhere in the map** — a scalar, column-blind, not “the lowest traversable surface”
   the comment claims (and not the visible floor under the spawn).
4. `GameScene.swift:62 / 646 / 964` → `Player.configure` (`Player.swift:40-43`) →
   `respawn()` (`Player.swift:232-234`) puts the player exactly at `spawnCenter`,
   `isGrounded=true`.
5. First fixed step (`GameScene.swift:268-276`): `Player.update` →
   `landOnFallbackFloorIfNeeded()` (`Player.swift:291-297`, called at :89 and :130):
   **if the player center ≤ groundY+32, snap up to groundY+32** (a global invisible plane);
   then `resolveSolidCollision` per overlapping solid (`Player.swift:137-177`), then
   `refreshGroundSupport` (`Player.swift:182-201`): support = some solid with
   `|maxY − footY| ≤ 1.5` under the feet span (box 46 px inset by 3, `Player.swift:187`);
   if unsupported **and** `footY > groundY + 1.5` → `isGrounded=false` → gravity
   (`Player.swift:32, 118-121`) makes the player fall; while falling, `landOnFallbackFloorIfNeeded`
   guarantees he never goes below the plane.
6. Death inside a zone re-applies the whole thing: `GameScene.swift:332` →
   `finishDeathAndRespawn()` → `respawn()` (`Player.swift:232-234`) → position = marker spawn.

Why the deltas are exact multiples of 16: everything is on the 16 px tile grid —
marker `y` ∈ {320, 288, 176, 128, 64} (all ≡ 0 mod 16; measured `y mod 16 = 0` in 125/125),
and all candidate rest positions (`groundY`, cell tops) are `384 − 16·row`. A rest position is
always *some* cell top or the plane, so `rest − marker` is a multiple of tile height
(`tileheight=16`; not player height — the `+32 = h/2` half-offsets cancel on both sides).
Magnitude 1 px-tile (±16) dominates because 118/125 markers are the compiler template row
`y=320` → feet=64, while each map’s global `groundY` ∈ {48:44, 64:16, 80:60, 96:5}
(verified: my executed-Swift distribution {48:44, 64:16, 80:60, 96:5} matches prior RT-07).

The **real** error is worse than ±16 where the floor near the marker is thick: the plane
lands the player on the *lowest row’s top*, not the floor surface (e.g. L01S11: marker feet 64,
groundY 80, true surface in that column 96 with a pillar at 144…208 directly over the marker
column; ASCII grid dumped from `L01S11.tmx` shows rows 18-19 solid ×35-wide + pillar cells
x∈[16,64) y∈[144,208)).

## 2. Re-measurement on this HEAD; reconciliation of 37/59/29 vs “exact 35”

`evidence/v3_measurements.py` re-run (rc=0, all EXPECTED match, HEAD `d4c7a58`):
`spawn_clean=37, spawn_lift=59, spawn_drop=29 (Σ=125), spawn_legacy_exact=35`.

My independent static replica: **37 / 59 / 29** — same, every delta ∈ {0, +16, −16}.
My executed-product-Swift run: **rest−marker histogram {0: 37, +16: 59, −16: 29}** — 125/125
maps identical to the static replica (feet, groundY, delta per map). The split **holds**.

Reconciliation of the two audit numbers:

* **35 (“exact”)** — `fullaudit-b01-spawn.json` / `spawn_legacy_exact`: probes **one fixed
  tile column** and demands **exact touch** (|Δ|<0.001). Categories: `exact 35 + void 89 +
  16_above 1 (L03S11) = 125`; it has **no drop concept at all** (`16_below=0`, audit §104)
  because it looks only for a floor exactly at feet height.
* **37 (“clean”)** — the shipped-rule sweep: foot box spans 3 tile columns
  (46 px collider − 2×3 px inset, `Player.swift:187`) and 1.5 px tolerance
  (`Player.swift:192`). I set-diffed both methods: the 35-exact set **equals** the 35
  genuinely-supported maps of the current rule; current clean = those 35 **+ 2** maps
  (`L01S09`, `L04S16`) where `feet == groundY` — the snap is a no-op so delta=0, but there is
  **no cell under the feet at all**: the player stands on the invisible plane. Both of them
  are *walk-locked* in the product run (§3). So 37 is a delta-classification, not a
  correctness count; **truly-correct (delta 0, body clear, walks) = 34**.
* **Which method a regression test should use**: the current-rule method (it mirrors shipped
  `Player`/`TMXLevelRuntime` code and is what the product run reproduced 125/125), upgraded
  from static geometry to the **dynamic** assertions of §6. Deprecate the JSON one-column
  method for gating (keep it only as a historical cross-check).

**Semantics trap (the control that proved its worth):** Linux `Foundation.CGRect.intersects`
returns **true for edge-touching rects**; Apple CoreGraphics returns false (verified by a
10-line probe on this host). Left uncompensated, every grounded player “intersects” the floor,
falls into the deep-overlap branch (`Player.swift:174-175`) and every map reports walk-locked
— the first harness run produced exactly that absurd uniform result, and the synthetic
`ctl_clean` control (must walk) caught it. After patching the one loop-guard line to Apple
semantics, `ctl_clean/ctl_sunk/ctl_float/ctl_void` walk free (456/456/456/456 px in 10 s) and
only genuinely embedded maps lock. **Any future Linux harness for this repo must encode this
check as a gate** (§6.3): if the platform says “touching intersects”, the harness must refuse
to report lock numbers. This also falsifies nothing about the audit — vertical results are
unaffected (all branches require strict overlap).

## 3. Observable consequence per group (executed real `Player`, dt=1/60, marker-rule entries)

Marker-rule entries happen at: stage starts (zones 0/25/50/75/100, `GameScene.swift:642-645`),
every in-zone death respawn (`GameScene.swift:332`), app start (`:62`, always L01S01 —
checkpoints from previous processes are deliberately discarded, `GameScene.swift:685-693`).
**Normal walk-in entries to the other 120 zones carry the previous zone’s Y**
(`GameScene.swift:643-645`: `y = max(groundY+32, carriedY)`), masking the marker bug until the
first death in the zone. So the audit numbers are exactly what a player sees on each death and
at each stage start.

* **+16 group (59 maps)** — lift. The snap happens inside the *first* `update()` before the
  first `playerNode.update` (`GameScene.swift:277`), so no motion is seen; the spawn is simply
  16 px higher than the marker ⇒ `vitorc.y` is decorative. 27 of 59 land on the real surface
  (floor is 1 tile thick near spawn) — accidentally fine. **32 of 59 land inside a thicker
  floor mass** (body strictly overlaps 1+ solid at rest) → `resolveSolidCollision` side/deep
  branch zeroes `position.x` every step (`Player.swift:165-176`): **cannot walk**. 30 of the
  32 can jump free (rise 37.8 px > embed), **L01S11 and L01S21 cannot** (pillar directly above
  the marker column blocks the jump path too): hard soft-lock until app restart.
* **−16 group (29 maps)** — drop. First drawn frame at the marker height, then a **visible
  16 px fall over ~18 fixed ticks (≈0.30 s**, gravity −360 px/s²). 26 of 29 land at
  `groundY` **inside the floor mass** (overlap 1-2 rects) and are hard soft-locked — embed
  depth ≥48 px > jump height 37.8 px, walking blocked: at death-respawn into these zones
  Vitorc visibly sinks and then **can never move again** (no progress, no death without an
  enemy; several have none reachable from the spawn cell). Only 3 land clean:
  `L03S06, L03S11, L04S19` (then hit ordinary level geometry after 49-145 px).
* **0 group (37 maps)** — 34 genuinely fine. 3 are not: `L01S09`, `L04S16` (stand on the
  invisible plane, no cell under feet — and with 1 solid overlapping the body: walk-blocked,
  jump-escapes) and `L03S10` (delta 0 *and* in the legacy-35, but body overlaps 2 rects at
  rest: walk-blocked until first jump).

**Worst cases (all hard soft-locks; delta from marker at the rule entry):**
1. **L04S01** (zone 075, −16) and 2. **L05S01** (zone 100, −16) — *stage-start* zones: every
   player reaching stage 4/5 is frozen **on normal entry**, progression impossible.
3. L01S11 (+16), 4. L01S21 (+16) — lift-embedded with pillar overhead, jump can’t escape.
5-10: L01S12 (−16), L01S13 (−16), L02S15 (−16), L03S16 (−16), L03S20 (−16), L03S21 (−16).
Remaining 18 hard-locks: L01S19, L02S12, L02S18, L02S21, L02S25, L03S03, L03S23, L04S04,
L04S06, L04S08, L04S10, L04S15, L04S24, L05S12, L05S15, L05S18, L05S21, L05S25 (all −16).
Totals: **walk-locked at spawn 61 maps, hard-locked 28, truly-clean 34.**

## 4. Candidate minimal fixes (each measured by re-running the harness with the candidate
applied at the `TMXLevelRuntime` geometry level; product files untouched)

**A. Fix the anchor rule in code (recommended).** Shape: in `TMXLevelRuntime.swift` after
`:68`, ~15 lines — keep the shipped position iff it is *supported AND body-clear at feet*;
otherwise re-anchor feet to the nearest collision-rect top, among rects overlapping the foot
span (`cx±20`), whose standing box (46×63 at `cx±23`) overlaps **no** solid; tie → lower;
none found → keep shipped behavior (void maps unchanged). Diff shape: one `var` + one
guard-and-replace block; `spawnCenter` remains the single source for respawn/checkpoint/stage
entry, so all marker-rule paths inherit the fix.

Measured variants:
* capped |Δ|≤32: locks 61→**3** (L01S11, L01S21, L04S01 still hard-locked), embedded 61→3,
  moves-from-truly-clean **0** — not sufficient alone.
* uncapped (recommended): locks 61→**0**, hard 28→**0**, embedded→**0**, moves-from-truly-clean
  **0** (the 34 safe maps provably do not move: the early return is exactly their invariant);
  all three broken groups repaired, including L01S09/L03S10/L04S16. Cost: 5 maps re-anchor
  >32 px up (L01S11 +192→y=256, L01S21 +176, L02S24 +208, L04S01 +112, L05S24 +208) — these
  are maps whose *template marker x* is under a pillar/ledge, so no y-only rule can restore
  the authored spot; they remain correctable only by B.

**B. Fix the marker data.** The compiler that emits `vitorc` is not in this repository
(118/125 markers are one template value (0,320) — a compiler-side default, not authoring
drift). Shape: regenerate/patch the `y` (and for the 5 maps also `x`) attribute of one
`<object name="vitorc">` per TMX in **91 files** (88 delta≠0 + L01S09 + L04S16 + L03S10).
Repairs all three groups perfectly *if* original start cells are sourced; zero risk to the
34. Does not protect against the next compiler run regressing; and the runtime stays
vulnerable to any hand-edited map. Issue belongs to the level-compiler factory repo.

**C. Clamp after placement (in `Player`/`GameScene`).** Shape: change
`landOnFallbackFloorIfNeeded`/`refreshGroundSupport` to use a column-aware local floor.
Measured indirectly by A-cap-16 (same locality idea, wrong anchor point): locks only drop to
48; and the plane is shared with the grenade semantics (`TMXLevelRuntime.swift:70-71` comment)
and per-step hot path — high blast radius (this is really finding B-02/RT-08 territory).
**Not recommended for P1-2**; keep as separate follow-up.

Recommended delivery: **A(uncapped) now** + **B as a factory issue** (compiler must emit
authored `vitorc`), with the 5 far-anchor maps listed for artwork confirmation (§5).

## 5. Provable on Linux vs needs the macOS play test

Linux-proven **in this session, on real product code** (not a replica-only claim): marker
geometry loader path (`h=0`, non-`tiledRect` branch), `spawnCenter`/`groundY` formulas, the
±16 quantization, the 37/59/29 histogram, per-map rest heights, walk-lock/hard-lock
classification (61/28/34), the 35-vs-37 set equality, and both fix variants — all via
`swiftc` execution of byte-verified `Player.swift`+`TMXMapLoader.swift`+`GameConstants.swift`
+ byte-verified extractions (harness in §0). The one Linux-hostile semantic
(`CGRect.intersects` edge-touch) was isolated, proven with a probe, compensated in exactly
one verified line, and must be gated (§6.3).

Needs macOS (`engineering/runbooks/macos-probe.sh`, guided section “## E. Play-наблюдения”,
items `E6` exists; propose new `E6a…E6d` next to it — the tester runs the app; expectations
are from this file):
* **E6a progression blocker:** fresh game → reach stage 4 start (zone 075 = L04S01) and stage 5
  (zone 100 = L05S01). Before fix: Vitorc sinks 16 px on entry and **cannot walk or jump**
  (hard-lock). After fix A: walks immediately. Also check zone 000/025/050 starts unchanged.
* **E6b death-respawn sink:** in L01S12 (zone 011) die once (turret) → respawn: before fix,
  visible 16 px sink then frozen; after fix, respawn on the floor walking.
* **E6c lift invisibility:** L01S17 (zone 017): death-respawn appears 16 px above the marker
  and walks (thin-floor lift) — proves the snap is pre-render, i.e. “+16” is never animated.
* **E6d artwork-vs-anchor:** the 5 far-anchor maps L01S11, L01S21, L02S24, L04S01, L05S24 —
  confirm the re-anchored spot is where the original placed Vitorc (needs original-game
  reference; if not, data fix B must supply the authored x too).
* **E6-semantics control (mandatory one-liner):** in any normal zone (L01S01) confirm walking
  works at all — Apple `intersects`-excluding-touch is assumed by the whole lock analysis;
  if grounded walking froze on macOS, the lock model is invalid and §3 must be re-derived.
* Also untestable on Linux for real: actual frame presentation of the 0.30 s sink (rendering
  timing/compositing), HUD overlay occlusion of low spawns (SH-02 interaction), gamepad path.

## 6. Regression test design (committed, self-checking)

Placement: **new artifact beside (not replacing) `v3_measurements.py`** — v3’s EXPECTED block
is the frozen self-check of audit report v3 and must not drift; the new tool owns
P1-2-regression going forward and lands in this change package next to the sibling
P1-1 pattern (`evidence/piston-anchor-harness/`):

```
engineering/changes/20260921-...-2e7698/evidence/
  spawn-anchor-harness/{run.sh, main.swift, glue.swift, fixtures/*.tmx}   # Swift, product-executing
  spawn_measurements.py                                                   # static mirror, xml.etree, EXPECTED+self-check
  spawn-anchor-swift.txt                                                  # frozen harness output (like piston-anchor-swift.txt)
```

Assertions (`rc=0` only if all hold, mirroring v3 style):
1. Corpus invariants: 125 maps, geometry `35x24@16`, 1 vitorc/map, all `w=h=0`,
   all `y mod 16 == 0`.
2. Rule sweep histogram: `{0: 37, +16: 59, −16: 29}`; Σ=125; no `|Δ|>16`;
   `legacy_exact(35) == supported35` set-equality; clean-minus-legacy == {L01S09, L04S16}.
3. **Dynamic gate** (Swift run): per-map `rest − marker` equals the static histogram value for
   all 125 (model↔product agreement is itself the strongest control);
   locked==61, hard==28, truly-clean==34 (pre-fix baseline; after fix PR: flips to
   locked==0, hard==0, clean-histogram may relax to `{0:34,*}` with `moved_from_truly_clean==0`
   as the guard for the 34).
4. **Controls that must flip (test fails if any doesn’t move):**
   (a) synthetic five `ctl_*` fixtures must each produce their designed distinct outcome;
   (b) platform-semantics probe: if `CGRect(x:0,y:80,w:512,h:16).intersects(CGRect(... y:96))`
   is `true`, harness must **refuse** lock numbers (exit ≠ 0) — encodes the §2 trap;
   (c) mutation control: bump one lift-map marker `y` by −16 in memory → histogram must shift
   59→58/60 and Σ stay 125 (a rule-blind probe cannot tell 37/59/29 from 36/60/29);
   (d) fix-ablation: with the candidate anchor disabled (CAP=0), output must be byte-equal to
   the baseline frozen file; with it enabled, locked must be 0 — the “green after fix” half of
   red/green.
5. After-fix CI shape: `spawn_measurements.py` is the red/green gate (red = rule drift from the
   fixed baseline), the Swift harness re-validates that the python mirror still equals product
   semantics; both are `python3 scripts/grok_verify.py --mode pr`-adjacent evidence under the
   change package, receipts recorded per route.

## 7. Corrections the P1-2 row should carry after this (for the fix PR / v4 report)

* “без изменения 37 карт” ⇒ delta-0 = 37, **of which only 34 are walkable+anchored**;
  L01S09/L04S16 stand on the invisible plane, L03S10 spawns inside a solid.
* Add the consequence v3 under-states: **61 maps walk-locked and 28 hard soft-locked at
  marker-rule entry**, including stage-start blockers **L04S01 (zone 075)** and **L05S01
  (zone 100)** — release-blocking on its own.
* Note that 120 zones mask the bug on walk-in entries via carriedY
  (`GameScene.swift:643-645`) — observable on every in-zone death and stage start.
* Linux harness authors: `CGVector` is absent from Linux Foundation (type-only polyfill
  needed) and Linux `CGRect.intersects` treats edge-touch as intersecting — opposite of Apple;
  gate every lock-related measurement on that probe.
