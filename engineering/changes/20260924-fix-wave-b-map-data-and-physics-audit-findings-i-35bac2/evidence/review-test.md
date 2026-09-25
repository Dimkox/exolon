# Test review — wave B (`20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2`)

Reviewer: route `test_reviewer`, tree `/home/pall/projects/.exolon-wave-b/exolon`, base `295690b`.
Read-only review; the only file written by this review is this one. Meter runs and ablations were
executed in `/tmp` copies (control copy `/tmp/wbCtl`, mutated `/tmp/wbA..F`).

## VERDICT: **FAIL** — one blocking item (F-1), five non-blocking

Blocking: `pinned_geometry_unchanged` (INV-002) contains a sub-check that **cannot fail**, and a
behaviorally live mutation of the geometry it claims to pin passes the whole meter 9/9 green. That
is the exact failure mode the change-spec's own AC-005 forbids ("a check that cannot fail is itself
a failure"). Everything else in the test story reproduced under independent re-derivation, including
the numbers most likely to have been fudged (the 61→48 no-worse-than-base control).

Fix size is small: make `query_collision_rects()` an independent implementation (or bind the product
rects in the harness) and keep the rest. Re-record the gate afterwards (see F-6).

## 1. Spec → path::symbol mapping (all 9 evidence paths resolve; meter 9/9)

`python3 evidence/wave_b_check.py` → `RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC`, rc=0, elapsed 2.9 s
(budget 60 s), `артефакт Swift: живой (совпал: True)`.

| ID | path::symbol | line |
| --- | --- | --- |
| AC-001 | `evidence/wave_b_check.py::spawn_ground_all_maps` | 656 |
| AC-002 | `evidence/wave_b_check.py::piston_anchor_all_pistons` | 720 |
| AC-003 | `evidence/wave_b_check.py::beam_shared_hp_all_maps` | 744 |
| AC-004 | `evidence/wave_b_check.py::bullet_cull_bounds` | 811 |
| AC-005 | `evidence/wave_b_check.py::controls_flip` | 905 |
| INV-001 | `evidence/wave_b_check.py::zone_index_formula` | 621 |
| INV-002 | `evidence/wave_b_check.py::pinned_geometry_unchanged` | 1114 |
| FORBID-001 | `evidence/wave_b_check.py::no_magic_offsets` | 991 |
| FORBID-002 | `evidence/wave_b_check.py::single_surface_query` | 1068 |

All nine are in `CHECKS` (1304–1315) and every check runs unconditionally (no `skip`), so the 9/9
claim is not a subset.

## 2. AC-001 amended clauses — verified, independently re-derived

I wrote my own meter (`/tmp/wb_independent.py`, does not import `wave_b_check.py`; constants re-parsed
from `GameConstants.swift` by my own regex: spriteW=48, body=46×63, inset=3; buried predicate
re-implemented) and got **byte-agreement on every pinned number**:

| quantity | meter | my independent run |
| --- | --- | --- |
| bounded ±16 (max |Δ| over 125) | 16 | 16 |
| hist Δ-vs-marker (new) | `{0:41, 16:83, -16:1}` | identical |
| hist base rule (37/59/29 control) | `{0:37, 16:59, -16:29}` | identical |
| preference pools | clear 71 / dirty 48 / kept 6 | identical |
| kept files (6, named) | `EXPECTED["spawn_kept_files"]` | identical list |
| buried base → after | 61 → 48 | 61 → 48 |

Also independently confirmed the corpus input: my own TMX gid decode (csv **and** base64 layers,
`& 0x1FFF_FFFF`, top = `pixelHeight − row·TH`) reproduces the committed parser's cell triples on
**125/125 maps** — so the 61/48 pair is not an artifact of a shared parser bug.

**Provenance of the base side (the question asked).** Two different mechanisms, and they must not be
conflated:

* *Base map **data*** — the mirror reads `Exolon/Resources/*.tmx` from the **working tree**, not from
  `git show`. That is sound only because the data is pinned, and I verified the pin outside the
  meter's own manifest: `git ls-tree -r 295690b -- Exolon/Resources` yields 125 blob OIDs that equal
  `tmx_base_hashes.json` **exactly** (`manifest == git == True`), and all 125 on-disk files hash to
  those base OIDs (`sha1("blob N\0"+bytes)`). So base-data ≡ working-tree data holds, verified.
* *Base spawn **rule*** — **not** git-derived. `wave_b_check.py:511` uses
  `v3_measurements.stable_feet` (the 20260919 audit tool) as the base position; the base product code
  never resolves a surface at all (`git show 295690b:Exolon/.../TMXLevelRuntime.swift:59-67` spawns at
  `worldBottomLeft(vitorc)`; `Player.refreshGroundSupport` only clears `isGrounded`). So `buried_base`
  (fields at `:522-523`, aggregated and bounded at `:689-693`) = "body-in-solid under the auditor's
  *model* of the base first settle step", and `git_show_base()` (`:585`) is called from exactly one
  place in the whole meter — `pinned_geometry_unchanged:1142`. Same pattern for the cull controls:
  `old_bullet_cull_bound()` (`:574`) and `old_gren = logicalSize.width + 24` (`:888`) are literals
  inside the meter, not reads
  of the base blob (I checked both against base: `git show 295690b:.../BlasterBullet.swift:42` =
  `width + 16`, `.../Grenade.swift:80` = `width + 24` → the reproduced values 528/536 are correct).
* *Direction of the residual risk*: favourable, not self-serving. Measured against the *literal* base
  spawn point (marker feet, no settle), buried = **84**, i.e. looser than the 61 the meter chose;
  after = 48 beats both readings. And the aggregate `buried_new <= buried_base` bound is not hiding a
  per-map regression: **0 maps** are clean-on-base → buried-after; 13 improved, 48 unchanged.

AC-001 scope disclosure (carried-Y, ~5–6 zone entries/playthrough) is printed by the check itself
(`:660-663`) and repeated in `wave_b_deltas.md:140` — present, as the amendment requires.

## 3. AC-004 — passes, both clauses

Muzzle-alive is arithmetically bound (`:823-824`: `cull ≥ clamp+muzzle` = 594 ≥ 578, `cull ≥ clamp+width`)
and the origin really is the shared constant (`Player.swift:269`, `:279`; clamp at `Player.swift:129`),
not a literal. Grenade policy: named bounds only (`Grenade.swift:84-85`), plus a tree-wide sweep for any
`position.x <…>` carrying `528`/`width+16`/`width+24` (`:863-866`) with the two legitimate 528-*as-spawn*
sites pinned instead of deleted (`:868-871`). Right-edge data claim verified independently: max solid
right edge = 560, 61 maps with collision right of 512 (meter `:880-882`).

## 4. `controls_flip` honesty — 12 named ablations: 3 reproduced verbatim, 1 new that breaks the net

`evidence/wave_b_ablations.txt` publishes 12 named ablations (A1–A8, B1–B4) plus baseline/final GREEN;
every one of the 12 shows a named `FAIL` — none is a no-op section. I reproduced three in `/tmp` copies
myself; each produced the **same failing check and the same message text** as published:

| # | my ablation (`/tmp`) | meter reaction | matches published |
| --- | --- | --- | --- |
| A | product preference branch deleted: `return clearBest ?? anyBest` → `return anyBest` | `FAIL controls_flip` — "Swift boundedSurfaceY потерял preference-ветку" | = `B1 preference deleted` ✅ |
| B | grenade cull reverted to inline `position.x < -24 \|\| … width + 24` | `FAIL bullet_cull_bounds` ×3 msgs (named-bounds, inline-literal, 528-стиль) | = `B3 grenade inline 536` ✅ |
| C | beam sort index tie-break `return a.offset < b.offset` removed | `FAIL beam_shared_hp_all_maps` — "Swift-сортировка потеряла index tie-break" | = `A5 beam tie-break removed` ✅ |

Two precision notes on those reddens (both honest but worth knowing): C reddens **only** via the
source-string guard (`:766`) — `ties == 0` across the corpus (`:761-763`), so no real map's grouping
can change; and A reddens **only** via that same class of guard, because on this corpus nearest and
preference select identically (the meter says so itself — see F-3).

**E (new, positive):** a silent product-only change *is* caught. `halfWindow: CGFloat(tileHeight)` →
`CGFloat(tileHeight * 2)` in `TMXMapLoader.swift:117` (no literal 16, mirror untouched) → `FAIL
spawn_ground_all_maps` ("harness разошёлся с зеркалом на картах ['L01S12','L01S13','L01S20',…]") + `FAIL
controls_flip` (live ≠ committed artifact). The pixel-exact product binding is load-bearing. Caveat on
the compared fields: the harness's `windowTops` column is recomputed inside `main.swift:74-76`, not
returned by the product — only `spawnFeet`/`markerY`/`groundY`/`groups` are product output (the E catch
came through `spawnFeet`).

## 5. Harness quality

`wave_b_harness/run.sh` builds the **real** `TMXMapLoader.swift` + `GameConstants.swift` (SpriteKit-free)
against `main.swift`; `awk` prepends exactly one `import FoundationXML` line and `diff <(sed '2d' copy)
loader` must be empty or the script exits 65 — the "+1 import" delta is genuinely byte-checked, not
asserted. Negative control is genuine and fatal-on-success: building without the CoreGraphics shim must
fail (it does: `no such module 'CoreGraphics'`), and a *passing* no-shim build exits 1. Fail-closed on
missing git/tooling is real (`:148-155` exits 2 if `v3_measurements` is unavailable; `:1043` and `:1144`
append errors instead of skipping).

Live-vs-committed byte-equality claim: **holds** — I ran `run.sh` myself and `cmp`ed against
`evidence/wave_b_swift.txt`: identical, md5 `f25029e95fd2d2974a4a3c9bb5ba8e42`. Committed
`wave_b_harness/last-run.txt` matches my live stderr except for the build-dir PID, and carries both
`OK:` control lines the meter greps for (`:976-979`).

Limit to state plainly: the harness compiles **2 of the 8** changed Swift files.
`TMXLevelRuntime`, `TMXTileMapRenderer`, `LevelObstacles`, `Player`, `BlasterBullet`, `Grenade` are
never executed — they are guarded by regex/string pins only.

## 6. Ablation battery vs meter idempotence

Two full runs of `wave_b_check.py` against the live tree (the meter is a writer of evidence files):
tree content fingerprint (my own SHA-256 over all non-`.git` files) **before = after = `b020c00f…`**,
`git status --porcelain` byte-identical, stdout identical, both rc=0. `write_if_changed` (`:440-450`)
does keep the tree static, so the ablation battery can be re-run inside a source-stability gate without
moving the fingerprint. The scratch build log is written under `tempfile.mkdtemp`, not the tree
(`:429-433`).

## 7. Gaps — what ships through this net

No Swift test target exists anywhere in the repository (`find` for `*Tests*`/XCTest returns nothing),
so the entire regression net for a SpriteKit game is this Python meter + a 2-file Linux harness.
Concretely uncovered, in descending materiality:

1. **Renderer/terrain rect geometry** (F-1) — the produced `collisionRects` feed `terrainRects`
   (`TMXLevelRuntime.swift:109-110`), which bullets, grenades and the egg collide with
   (`GameScene.swift:415,469,503`; `LevelObstacles.swift:609`). Zero binding.
2. **Beam death visuals** — AC-003's "destruction removes both visual segments together" is one
   substring pin (`:793-795`). `field.onDestroyed { [weak side] in side?.coverDestroyed() }`
   (`TMXLevelRuntime.swift:458`) and `coverDestroyed()` (`LevelObstacles.swift:788`) are never
   executed; the 25-hit pool *is* executed (`main.swift:47` → `BeamFieldModel`), the fan-out is not.
3. **SpriteKit runtime consumption of the corrected spawn** — the harness proves
   `resolvedPlayerBottom` returns Y; that `TMXLevelRuntime` hands it to `Player.teleport` and survives
   the carried-Y path is guarded only by `resolvedPlayerBottom(using: query)` presence (`:1100`).
   `release.md`/`test-plan.md` assign that to a manual macOS spot check — acceptable only if the PR
   body really carries the screenshot/notes, which `test-plan.md` demands ("record in PR").
4. **Piston lethality is a geometric model**, not the damage tick: `new_lethal` is an overlap of
   `[ground, ground+64]` with the foot band (`:553-554`), never executed against `Player` hitboxes.
5. **48 remaining buried spawns**: accepted debt is correctly disclosed (`release.md`,
   `rollback.md`, `wave_b_deltas.md:137`) and I confirmed 0 per-map regressions — but see F-4 on the
   published enumeration.

## Findings

**F-1 — BLOCKING. `pinned_geometry_unchanged` rect-stability sub-check is unfalsifiable; a live
collision-geometry mutation passes 9/9.**
`evidence/wave_b_check.py:330-332` — `query_collision_rects()` is `return self.old_collision_rects()`
(the *same* function), and `:1155` compares it to `old_collision_rects()`, so
`renderer_rects_identical_all_maps == 125` (`:1159`, `EXPECTED:128`) is `x == x`. The printed line
"rects идентичны на 125/125" (`:1160-1161`) and the comment at `:1139-1141` ("Это base-vs-new, а не
зеркало-vs-себя-зеркало") overstate what is proven: the only base binding there is four *anchor
strings* in the base blob (`:1146-1149`). Proof of impact — `/tmp/wbD`: both `CGRect(... y: run.top -
tileHeight ...)` lines in `Exolon/GameCore/Levels/TMXMapLoader.swift:251,255` changed to `y: run.top +
7.5` (shifts every solid surface; not dead code — `terrainRects`, `TMXLevelRuntime.swift:110`) →
**`RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC`, rc=0, 9/9 PASS**. Fix: make `query_collision_rects()` a
genuinely separate implementation of the *new* Swift algorithm (port it independently, as
`old_collision_rects` was ported from the base blob) and/or have the harness emit per-map rects so the
comparison is mirror-vs-product. Per the spec's own AC-005, this sub-check must not stay as-is.

**F-2 — MAJOR (test story). Without `swiftc`, F-1-class and E-class product drift goes green silently.**
`wave_b_check.py:419-420` returns `(None, "swiftc отсутствует")`, `:459-461` then sets
`attempted=False`, and `:970-974` prints an informational line but appends no error — the meter stays
9/9 against the *stale committed artifact*. Proof — `/tmp/wbF` (ablation E mutation + `PATH` without
`swiftc`): **9/9 PASS, rc=0**, with the tell only in prose (`артефакт Swift: коммиченный (совпал:
False)`). This also means a green receipt does not by itself prove the product was executed. Fix: make
"live harness executed and byte-equal" a hard assertion in `controls_flip` (or a receipt field the gate
requires), and note that on macOS `run.sh` deliberately exits 75 (`run.sh:34-36`) while `swiftc` exists
→ `attempted=True` → `:971` reddens the meter; so the meter is Linux-green-only, which contradicts
`release.md`'s "9/9 ≤3 s on head" as a Mac-developer metric. Worth one sentence in `test-plan.md`.

**F-3 — MINOR, disclose-only (already disclosed). The AC-001 preference clause is mutant-equivalent on
this corpus, and its only behavioural control runs on the Python mirror.** Ablation A reddens exactly
one check, and only via the substring pin `:933-935`; the product-vs-mirror comparison stays silent
because nearest and preference never disagree here. `wave_b_deltas.md:138` states this openly ("nearest
без preference дал бы ровно те же 125 выборов и те же 48 buried…"), and the fixture at `:925-931`
proves the *mirror's* preference. Residual: no executed-Swift evidence of the preference branch. Fix
(cheap): add a synthetic map to the harness corpus where nearest is buried and clear is farther, so
`main.swift` → `resolvedPlayerBottom` itself must return the clear top.

**F-4 — MINOR (SIG-001 enumeration). The 61/48 buried claim is count-complete but not name-complete.**
`write_deltas` (`:1213+`) emits the 125-row spawn table (marker/old/new/Δ/pool) and the 6 kept maps by
name, plus only the aggregate sentence `wave_b_deltas.md:137`. A reviewer therefore cannot see *which*
48 remain buried or *which* 13 improved without re-deriving it (I had to). SIG-001 promises per-map
tables "so any difficulty shift is visible to review". Fix: add a `buried(base)/buried(after)` column
to the spawn table — the fields already exist in `spawn_rows()` (`:522-523`).

**F-5 — MINOR (provenance wording). AC-001's "computed on the base tree 295690b" is model-based for the
rule and pinned-for-the-data, not `git show`-based.** See §2. Base *data* provenance is solid (I
verified it against `git ls-tree`); base *rule* is `v3_measurements.stable_feet`, and both cull controls
are hardcoded reproductions of base formulas. The manifest's own base claim (`tmx_base_hashes.json
"generated_from_commit"`) is self-declared and only checked as a string prefix (`:995-996`) — my
external `git ls-tree` check closes that hole, but the meter does not close it itself. Fix: hash the
base blob live (`git show 295690b:…`) for at least a sample of maps, or state in `change-spec.yaml`
that the base side means "base map data + audited base rule model".

**F-6 — PROCESS. The verification receipt is stale w.r.t. the current tree; drift is paperwork-only.**
`receipts/35bac25f12ae/verification.json` `created_at 2026-09-24T21:25:59+00:00`, mtime 21:25:59,
`tree_fingerprint caea24c89b4287b2…`. Recomputing with the project's own
`.grok-stack/adaptive_grok/util.py::tree_fingerprint` over the 32-file changed set gives
**`72d2624458d30af1…` → receipt does not match the tree.** Files newer than the receipt (exactly 4):
`tasks.md` 21:28:57 (the ticked box the final report notes), `release.md` 21:30:21, `rollback.md`
21:30:21, and `engineering/changes/20260919-…/evidence/__pycache__/v3_measurements.cpython-312.pyc`
21:30:24 — the `.pyc` is an import side effect of *this* review's meter runs and is filtered from the
fingerprint (`git ls-files --exclude-standard` / `_fingerprint_noise`), so it does **not** contribute to
drift. All eight product Swift files and every evidence file (incl. `wave_b_check.py` 21:19:27,
`wave_b_deltas.md` 21:21:25) predate the receipt: no product change, only documentation. Per
`AGENTS.md` ("a local receipt is stale after any repository change") the gate must be re-recorded after
F-1/F-2 land. Note `release.md` already anticipates a re-record ("B writer flagged receipt freshness
once already").

## Positives worth preserving

- The no-worse-than-base control is the *tighter* of the two available base readings and hides no
  per-map regression (independently recomputed: 84 / 61 / 48; 0 regressions) — the amendment-2 rejection
  of "delete the filter wholesale" is backed by numbers, not prose.
- Live product binding via a pixel-exact harness comparison, with a byte-checked single-import build
  delta and a fatal no-shim negative control — reproducible on any Linux box in ~3 s.
- Fail-closed design is real: missing `v3_measurements`/git aborts or errors rather than skipping
  (`:148-155`, `:1043`, `:1144`), empty seam blocks are themselves errors (`:1023-1025`), and the
  added-lines scan sanity-guards against a suspiciously empty diff (`:1057`).
- `write_if_changed` idempotence means the 12-ablation battery can be re-run inside a source-stability
  gate without moving the fingerprint.
- Unusually candid evidence: `wave_b_deltas.md:138` disclosed the preference mutant-equivalence before I
  found it.
