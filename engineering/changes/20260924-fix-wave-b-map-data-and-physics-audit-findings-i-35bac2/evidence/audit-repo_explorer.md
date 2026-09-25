# Audit — repo_explorer (route analysis wave): wave B tree state, fix substance, controls

Read-only audit of the working tree. No file modified by the auditor; writer's dev loop not run.
All corpus numbers recomputed independently (python3 -B over TMX, awk/grep over the committed
harness artifact). Saved by the controller as `audit-repo_explorer.md` — the assigned
`analysis-repo_explorer.md` path holds the writer's Task-1 characterization (different role; the
writer has already absorbed this audit's piston corrections).

## Binding snapshot

| Item | Value |
| --- | --- |
| Worktree | /home/pall/projects/.exolon-wave-b/exolon (sibling of main) |
| Branch / HEAD | codex/wave-b-mapdata-physics-20260924 @ 295690b7fc72 (= route base) |
| Product delta | 7 files, +328/−79, all GameCore |
| Untracked | only the change package |
| Audit window | 2026-09-24 20:19–20:27 UTC (host=UTC; owner GMT+3) |
| git diff --check HEAD | clean; all 7 touched files pass swiftc -frontend -parse |

Writer edits observed DURING the audit (cite when judging): wave_b_check.py 20:20:49→20:25:50
(piston pin 3→6 landed mid-audit), BlasterBullet 20:10:35→20:26:18, TMXLevelRuntime
20:09:52→20:26:58 (torn read at 20:26:58, settled by 20:27:16).

## Q1 — Per-defect substance

Files: GameConstants (+27 named geometry), TMXMapLoader (+208: TMXSurfaceQuery,
resolvedPlayerBottom, BeamFieldModel, TMXBeamGrouping), TMXLevelRuntime (+64/−8 wiring),
TMXTileMapRenderer (private buildCollisionRects DELETED, rects from query), LevelObstacles
(piston constants; ForceFieldBarrier loses own HP counter), Player (clamp/foot constants),
BlasterBullet (derived cull).

### P1-3 — FIXED as specced
Cull = blasterCullMaximumX derived: 512+32=544 clamp + 16 bullet width = 560; Player clamps on the
SAME constants; corpus verified: 61/125 maps solid right of 512, max solid right edge exactly 560;
x>510 transition untouched. AC-004 satisfied.

### P1-5 — FIXED structurally
One BeamFieldModel per x-overlapping group; per-side hitPoints deleted; both sides read
field.isActive; onDestroy flips both; single damage entry (first(where:)) prevents double-debit;
pool empties at hit 25, notify exactly once; fresh 25 HP per level instance (runtime rebuilt every
load). PLAYER-VISIBLE SIDE EFFECT for PR notes: award now 1000 per beam (was 2000 per pair).
Pre-existing, out of scope: beam destruction doesn't open the route (Collision layer immutable).

### P1-1 — code FIXED; control fixed mid-audit; prose still stale
Anchor via surfaceQuery.pistonGroundY (highest Collision top ≤ raised tread; fallback plane
elsewhere); 46/46 lethal under meter predicate. Old-anchor lethality is 6, not 3 (3 zero-delta +
3 plane-fallback grazing at −48: L01S15 x=128, L02S23/L05S23 x=400). Pin corrected 20:25:50;
product comments TMXMapLoader.swift:208-211 / TMXLevelRuntime.swift:292-296 "43 of 46 float 64 px
below" still overstated — truth 40 at −64, 3 at −48, 3 unmoved. (Writer's characterization has
since restated this correctly — align the two code comments.)

### P1-2 — mechanically correct, semantics BROADER than the defect → BLOCKING
AC-001's "delta 0 vs shared query" was tautological (spawn computed from that query). The
unbounded nearest-BODY-CLEAR rule relocates spawn on 91/125 maps: histogram
{0:34, −16:3, 16:38, 32:45, 112:1, 176:1, 192:1, 208:2} — 45 maps by +32 px, 5 by 112–208 px
(L01S11 64→256, L01S21 →240, L02S24/L05S24 →272, L04S01 →176): body-clear rejects every surface
with a cell above, so pillar columns keep only the topmost. Player.refreshGroundSupport (±1.5 snap,
no body-clear) WOULD accept the rejected floors — spawn rule stricter than the engine requires.
Unexplained difficulty shift violates the Constraints/SIG-001 duty; wave_b_deltas.md never
generated. Controller resolution: AC-001 amended (bounded ±16 window rule, no-surface maps stay
unmoved and enumerated); writer instructed.

## Q2 — Magic numbers (FORBID-001)
Added-line literals all accounted: 16 as single bullet-width source; 528/544/560 comments only;
25 only as sharedHitPoints; 3 named shared insets; 32 value-preserving clamp move (bare literal
in new home — cosmetic); no new per-map table. GAP: no_magic_offsets scans only
TMXMapLoader/GameConstants; TMXLevelRuntime.swift (which already carries two pre-existing per-map
tables :450, :530-535) unscanned for ADDED lines. Meter also hard-codes body height 63 instead of
parsing it.

## Q3 — One surface query? (FORBID-002)
One Collision interpretation: YES (single cell-top formula, single layer selection, renderer merge
deleted with rect-for-rect 125-map equivalence → INV-002 real). Caveats: spawn vs piston use
different SELECTION rules on the one query; Player.refreshGroundSupport keeps its own support test
(one-way divergence); dead invites: TMXMapData.resolvedPlayerBottom() (:98, zero callers),
TMXSurfaceQuery.groundY(x0:x1:) (:182-184 unused overload), meter-only piston mirror.

## Q4 — Beam determinism risk
TMXBeamGrouping.groups sorts by minX with Swift's UNSTABLE sorted; Python mirror keys (minX,i);
meter compares group lists byte-exact; docstring claims distinct-minX "checked before comparison"
— NO SUCH CHECK EXISTS; artifact already shows both [1+0] and [0+1]. AC-005 flips if any future
map pairs beam halves at equal sourceX. One-line fix: tie-break by index (mirror it) or assert
distinct minX in the meter.

## Q5 — TMX untouched — PROVEN three ways
git status clean for *.tmx/Resources; git diff --quiet 295690b -- '*.tmx' rc 0; independent blob
SHA-1 recompute vs evidence/tmx_base_hashes.json → 125/125 match, 0 missing.

## Q6 — Owed at snapshot (severity-ordered)
1. [self-corrected] piston pin 3→6; re-verify AC-002 on current bytes; two code comments stale.
2. [BLOCKING] P1-2 unbounded relocation + missing wave_b_deltas.md → resolved by AC-001 amendment;
   implement bounded rule.
3. [prose drift] "43 of 46 / 64 px" comments vs 40/3/3.
4. [evidence] analysis-architect/docs_researcher pending (route wave), this audit → audit-*.
5. [evidence] receipts absent, tasks unchecked, state stuck at approved (expected mid-flight;
   close-out duties).
6. [fragility] beam ordering precondition unenforced.
7. [dead code] resolvedPlayerBottom, groundY overload, beamFields consumer-less.
8. [minor perf] surfaceQuery computed property rebuilds cells per access (2–3 full scans/load);
   collisionRects merge O(rows×cells).

## Auditor 8-line summary (verbatim)
1. 7 product files (328+/79−), all GameCore; no new files; no TMX touched; P1-3/P1-5 fixed exactly
   as specced (cull 528→derived 560; one 25-HP pool per group, sides die together).
2. P1-1 anchor derives from surfaceQuery.pistonGroundY, 46/46 lethal — comments' "43 of 46 float
   64 px below" overstated (40 at −64, 3 at −48, 3 unmoved).
3. Meter's piston_lethal_old pin was 3 and is provably 6; writer corrected mid-audit.
4. P1-2 mechanically correct but the nearest-body-clear rule relocates spawn on 91/125 maps
   (45×32 px, 5×112–208 px) — unexplained difficulty shift beyond the ±16 defect.
5. FORBID-001 clean in code; meter's map-name scan misses TMXLevelRuntime.swift.
6. FORBID-002 mostly satisfied; selection-rule divergence, Player's own support test, unstable
   beam sort vs byte-exact artifact comparison with unenforced precondition.
7. Tree snapshot: edits mid-audit; 7 files parse clean; git diff --check clean.
8. Open: wave_b_deltas.md; receipts; tasks; state; dead code (resolvedPlayerBottom, groundY
   overload, beamFields consumer-less).
