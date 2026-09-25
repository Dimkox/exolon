# Analysis — four wave-B seams, pinned before editing (recorded by the implementer)

Pinned at route base `295690b` (line numbers are of the base tree; files unchanged
since). If the route's read wave adds its own `analysis-repo_explorer.md` content,
it supersedes this record for its own authorship — the measurements themselves are
reproduced by `wave_b_check.py`, not by this prose.

## P1-2 spawn (fixed)

- `Exolon/GameCore/Levels/TMXLevelRuntime.swift:60-63` (base) — `playerBottom` from
  `loadedMap.object(named:"vitorc")` + `worldBottomLeft`; `:65-68` — `spawnCenter`
  = bottom + half sprite (48×64, `GameConstants.swift:15`). Feet therefore
  `pixelHeight − marker.y`, decorative ±16 off Collision (37/59/29 over 125 maps,
  control reproduced via `v3_measurements.stable_feet`, `spawn_old_rule_hist`).
- Fallback plane `resolvedGroundY = min(rect.maxY)` over renderer rects at `:74-81` —
  kept as semantics, re-homed into `TMXSurfaceQuery.fallbackPlaneY` (min cell top,
  identical values: rects are one tile tall per row).
- Shipped landing rules that then snap/keep the player:
  `Player.swift:291-297` (`landOnFallbackFloorIfNeeded`), `Player.swift:182-201`
  (`refreshGroundSupport`, inset 3, tol 1.5). New spawn feet are chosen *on* a
  surface, so these are no-ops at spawn (asserted per map in the meter).
- **DELIVERED RULE (AC-001 amendment 2 of 2026-09-24; supersedes both earlier
  variants recorded here and in `audit-repo_explorer.md` §Q1 timeline):** the
  first implementation anchored feet to the nearest BODY-CLEAR top over the whole
  column (relocated 91/125 spawns, 45×+32 px, 5×112–208 px — rejected);
  amendment 1 then deleted the body-clear notion inside a plain ±16 window
  (rejected by the architect audit: filter-free nearest leaves buried choices
  unshadowed); amendment 2 — shipped — keeps the ±one-tile window and restores
  body-clear as a PREFERENCE: clear in-window tops shadow buried ones (tie →
  lower), no clear top → nearest in-window still taken (never worse than the
  shipped plane snap), empty window → marker UNMOVED and enumerated.
  Corpus (see `wave_b_deltas.md`): 119 matched (71 via clear pool, 48 nearest
  where no clear top exists in the defect window), 6 kept (L01S17, L02S24,
  L03S06, L04S09, L04S19, L05S24), max move 16 px, body-in-solid count
  61 (base) → 48 (after). On this corpus plain-nearest and preference agree
  map-for-map; the preference is enforced by a synthetic fixture control.
  Disclosure: carried-Y (`GameScene.swift:638-646`) means resolved spawn Y is
  consumed at stage starts/app start/death respawns only (~5-6 entries/play).
  The walk-lock repair from `analysis-p1-2-spawn.md` §3 remains out of scope
  (factory data fix / separate engine change).

## P1-1 pistons (fixed)

- Anchor site `TMXLevelRuntime.swift:289-292` (base): `PistonHazard(leftX: bottom.x,
  groundY: bottom.y)` with `bottom.y = pixelHeight − marker.y` (non-`tiledRect`
  branch `TMXMapLoader.swift:73-81`; 46/46 piston markers carry `w=48,h=64` except
  one `w=h=0` point marker on L01S03).
- Travel geometry `LevelObstacles.swift:329-346` (base): `hiddenY = groundY−64`,
  `exposedY = groundY`, node 48×64, hitbox `x+3, width 42`.
- Measurement: 40/46 pistons have the Collision surface exactly `groundY+64`
  (tread) — hitbox `[g, g+64]` touches the foot line edge-only → never lethal under
  Apple `intersects`; 3 already lethal (L01S03, L01S10×2); 3 columns hold no cell
  under the tread at all (L01S15 x128, L02S23/L05S23 x400 — y=384 markers,
  fallback-plane walkway above a shaft, their surface 48 px above the marker row).
  Old-anchor lethal control: 6/46
  (3 real-floor + 3 grazing the fallback plane; the merged `p1-1_piston_probe.py`
  counted 3 because its band reference has no plane concept — it classifies
  L02S23/L05S23 x400 as `edge_only` against the 3-columns-away floor at y=64 and
  lists L01S15 x128 under `no_support`).

## P1-3 bullet cull (fixed; AC-004 amended adds muzzle + grenades)

- `BlasterBullet.swift:41` (base): `position.x > GameConstants.logicalSize.width + 16`
  = 528 (left `position.x < -16`); bullet 16×2 at `:24,:28-31`.
- Player clamp `Player.swift:127-128` (base): `min(max(x, 24), logicalSize.width + 32)`
  = 544. Corpus right edge of Collision = 560 (maps are 35×16 wide), 61 maps carry
  solid right of x=512 — dead corridor confirmed by data.
- Amendment-2 AC-004 also closes BORN-DEAD shots: blaster origin is x+34
  (`Player.swift` `blasterOrigin`), so from x ∈ (494,544] the old 528 bound culled
  at the first update; the shipped bound is now `clamp + muzzle(34) + width(16)`
  = 594 (left `-(muzzle+width)` = −50), all named-constant derived. Grenades had
  the same defect inline (`x > logicalSize.width + 24` = 536 vs reachable origin
  548) and now share the policy (`grenadeCullMinimumX/MaximumX` = −20..564).
  Remaining 528-literals are spawn POSITIONS (bubble creator, homing missile
  start), pinned by the meter as such.
- Transition trigger `GameScene.swift:610` `x > 510` — pinned, untouched.
- Out-of-scope neighbours deliberately untouched: `HomingMissile` start
  `logicalSize.width + 16` (spawn position, not culling) and bubble spawner x=528.

## P1-5 beam fields (fixed)

- Per-side instantiation `TMXLevelRuntime.swift:356-360` (base): every
  `source_marker` with `sourceBlock` containing `beam_` creates its own
  `ForceFieldBarrier(hitbox:)`; `LevelObstacles.swift:770-796` (base):
  `ForceFieldBarrier` owns `hitPoints = 25` → 20 markers / 10 maps → 2 pools per
  pair → 50 hits per beam.
- Beam boxes `CGRect(x: sx, y: max(0, bottomY−240), width: 48, height: 272)` —
  corpus up/down pairs always sit in adjacent sourceX columns (down = up+1,
  10/10) so the two 48-wide boxes overlap in x by 32 px; x-interval overlap is the
  data-derived pairing (no per-map table, no +1 arithmetic).
- Consumers unchanged: `GameScene.swift:399` (shot), `:569` (player lethal),
  `:1099` (debug overlay) — all per-side `isActive`/`hitbox`, which now delegate to
  the shared field.
