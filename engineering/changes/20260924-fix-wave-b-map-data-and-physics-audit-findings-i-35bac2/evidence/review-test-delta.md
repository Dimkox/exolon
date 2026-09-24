# Test review — DELTA re-review, wave B (`…-i-35bac2`)

Scope: re-verification of the fix round against my original report
[`review-test.md`](review-test.md). Read-only; the only file written by this pass is this one.
Tree `/home/pall/projects/.exolon-wave-b/exolon`, base `295690b`. All ablations ran in `/tmp/dN`
copies; `/tmp/dd_rects.py` holds my independent rect implementation.

## VERDICT: **PASS** — test story. Unambiguously.

Both blocking items are closed and I could not reopen either. My original case (`y: run.top -
tileHeight` → `+ 7.5`) now reddens the meter, the fix is bound to the real product (not to a mirror
talking to itself), and I confirmed the numbers with a **fourth** implementation of my own. No
previously non-blocking item became blocking. Remaining items are nits (N-1…N-6) plus one process
requirement (P-1: re-record the gate after this file lands).

## 1. What changed in the bytes I am reviewing

| file | before → after | mtime | note |
| --- | --- | --- | --- |
| `evidence/wave_b_check.py` | 84 185 → 89 638 B (1348 → 1446 lines) | 21:55:25 | three-way rect comparison, in-meter mutant battery, `TOOL_ABSENT` gate |
| `evidence/wave_b_harness/main.swift` | 3.0 → 7 335 B | 21:54:03 | adds `RECTS map= count= coords=` (`main.swift:71`, product `query.collisionRects`) |
| `evidence/wave_b_swift.txt` | 18 989 → 54 267 B | 21:56:19 | +125 `RECTS` lines (line types now: 125 SPAWN / 125 RECTS / 125 PLANESRC / 46 PISTON / 10 BEAM / 1 GEOMETRY / 1 BEAMPOOL / 1 SUMMARY) |
| `evidence/wave_b_ablations.txt` | 39 396 → 62 054 B | 21:56:57 | +§M12, §M13 (14 mutation sections, was 12) |
| `Exolon/GameCore/Levels/TMXMapLoader.swift` | — | 21:56:54 | `pistonGroundY` doc wording (R1-1 prose item) |
| verification receipt | `caea24c8…` → `a5ad67be…` | 22:03:00 | `created_at 2026-09-24T22:02:59+00:00`, status `pass` |

The 21:56:54 product edit is **behaviorally inert, verified**: I rebuilt the harness on the current
bytes myself and `cmp`ed against the committed artifact — byte-identical (stderr carries both `OK:`
controls, incl. the `+1 строка импорта` byte-check and the no-shim negative control). The meter itself
is unchanged in AC-001…AC-004 / FORBID output (same 119/125, 37/59/29, 46/46, 250/500, 594/564,
"237 added lines in 8 files"); only INV-002's line changed shape.

## 2. F-1 (was BLOCKING) — CLOSED, verified four ways

The tautology is gone: `query_collision_rects` (`wave_b_check.py:312-333`) is now a real port of the
new Swift merge (unique-tops insertion order → `sort(reverse=True)`, per-top cells sorted by x0, merge
on `sx == x1`), and the base side is a separate function `base_build_collision_rects` (`:337-374`)
reading raw **gids** via `v3.decode_layer` — a different input *and* a different traversal. I checked
structurally: neither calls the other, and a scan for `check(X == X)` / delegating accessors over the
whole 1446-line file returns **none**. The three sides are compared count + order + coordinates, with a
hard error when an artifact line is missing (`:1236-1243`).

My independent confirmations:

1. **Base side ≡ base blob.** I transcribed the deleted merge straight out of
   `git show 295690b:Exolon/GameCore/Levels/TMXTileMapRenderer.swift` (row-major while-merge,
   `y = pixelHeight − (row+1)·tileHeight`, `width = (column−start)·tileWidth`, `& 0x1FFF_FFFF`,
   `gids.count == width*height` guard) — the meter's port matches it line-for-line, and all four
   `anchors` at `:1222-1226` are present verbatim in that blob.
2. **Fourth implementation.** My own decoder (csv **and** base64 layers, cells from raw XML, no meter
   code in the path) agrees with the meter's base port, the meter's new port **and** the executed
   `RECTS` lines on **125/125** maps; my total = **1437** = `EXPECTED["renderer_rects_total"]`
   (`:129`, asserted `:1248`). The code reviewer reached the same 1437 from the base blob
   independently — two non-overlapping derivations, same number.
3. **My mutation reproduces as a red.** `/tmp/d1`, product `+7.5` at the two append sites (now
   `TMXMapLoader.swift:255,259` — they moved from `:251,255` when the doc comment landed):
   `FAIL pinned_geometry_unchanged` ("rect-геометрия рассинхронизирована" per map, print line shows
   `на 0/125 (всего 0 rect'ов)`) + `FAIL controls_flip` (live ≠ committed artifact) → rc=1. Published
   §M12 carries the identical output. Two harder cases also flip: **D2** `tops.sort(by: >)`→`<`
   (order, counts equal) and **D3** `width: run.x1 - run.x0 + 1` (count *and* order preserved) → both
   rc=1. So the comparison is genuinely coordinate- and order-sensitive, not count-sensitive only.
4. **In-meter battery is real** (`:994-1016`): picks a victim map with ≥2 distinct rects, asserts the
   clean comparison holds, then asserts `base_r != y+7.5`, `base_r != reversed`, `new_r != x+16`, and
   hard-errors if no such victim exists (`:1004`). Correctly layered: the battery proves the
   *comparison* can redden; the product binding comes from side (c) + the gate below.

## 3. F-2 (was MAJOR) — CLOSED

`main():1431-1436`: green checks + `swiftc` absent + no explicit opt-in ⇒ prints
`RESULT: TOOL_ABSENT …` and returns **3**. Verified on already-mutated trees: **D4b**
(`halfWindow ×2`, no swiftc) → 9× PASS lines but `RESULT: TOOL_ABSENT`, **rc=3**; **D1b** (the `+7.5`
rect mutation, no swiftc) → same, **rc=3**. The silent-green path I demonstrated last round is closed;
only the explicitly named `--artifact-only` opt-in returns 0 (see N-4).

## 4. My other cases: status on the new bytes

| my case | re-run | result |
| --- | --- | --- |
| spawn `halfWindow` ×2 (my positive control) | **D4** | adopted as **ablation #13** (`§M13`); my run reddens `spawn_ground_all_maps` with the *same five maps* as published (`L01S12, L01S13, L01S20, L01S22, L01S23`) + `controls_flip` |
| delete preference branch | **D5** | still reddens `controls_flip` only (string guard `:933-935`) — F-3 unchanged, still disclosed, non-blocking |
| grenade inline literal | **D6** | still reddens `bullet_cull_bounds` ×3 — cull controls intact |
| beam index tie-break | **D7** | still reddens `beam_shared_hp_all_maps` via the string guard only (corpus `ties == 0`) — F-5 unchanged, non-blocking |
| `fallbackPlaneY` (new probe) | **D11/D12** | `−0.5` invisible (artifact `fmt` is `%.0f`, `main.swift:52-55`) → N-3; **`−16` (a full tile) reddens** `piston_anchor_all_pistons` on exactly the 3 shaft pistons `L01S15/L02S23/L05S23` + `controls_flip` + `no_magic_offsets` (the ±16 added-line scan caught my own synthetic mutation) → the executed plane is transitively bound, so the unasserted plane columns are a nit, not a hole |

## 5. Decorative-control census (my §4/§7 work, re-run) — IMPROVED

* Unfalsifiable comparisons: **1 → 0**. No `check(X == X)`, no accessor returning its own comparee.
* Composition on the new bytes: 123 `check()` calls; 11 pure source-substring guards + 12 regex-on-source
  guards (≈19 % textual); 42 references to the executed artifact. Every AC-001/AC-002/AC-003/INV-002
  numeric claim now has an executed side (spawnFeet, per-piston groundY, beam groups, pool simulation,
  rect coords).
* Missing-evidence handling is fail-closed for SPAWN/PISTON/BEAM/RECTS; one asymmetry remains (N-1).
* Stdlib-only and 3.1 s (budget 60 s) — AC-005's own clauses still hold.

## 6. Receipt freshness (my original F-6) — CLOSED, with a standing caveat

`receipts/35bac25f12ae/verification.json`: `created_at 2026-09-24T22:02:59+00:00`, status `pass`,
`tree_fingerprint a5ad67be5a00bc4b…`; recomputing with the project's own
`.grok-stack/adaptive_grok/util.py::tree_fingerprint` gives **`a5ad67be5a00bc4b…` → BOUND**. At that
measurement the only files newer than the receipt were **2** `__pycache__/*.pyc` from *my* meter runs
(22:07:27, 22:11:12), and those are filtered from the fingerprint — so the gate did bind the post-fix
bytes, including the `TMXMapLoader.swift` doc edit and both original review reports
(`review-test.md` 21:44, `review-code.md` 21:49). The fingerprints quoted in those two reports
(`caea24c8…` and `1b4a8398…`) are historical and are correctly superseded.

**P-1 (measured, not predicted):** this pass moved the fingerprint — with `review-test-delta.md`
written, `tree_fingerprint` is now `06404364af73cc29…` ≠ the receipt's `a5ad67be5a00bc4b…`. The drift
list is four files, all reviewer-side: `review-code-delta.md` (22:17:23, the code reviewer's delta —
**a second writer in the same tree**) and `review-test-delta.md` (22:17:50, this file), plus the two
meter `.pyc` files (fingerprint-filtered). So the gate must be re-recorded **once, after both review
writers have settled**, and again after the PR rebase onto post-A `main`, as `release.md` already
requires. The re-record is cheap and safe: two further meter runs left my tree fingerprint at
`9862ad3f…` unchanged (before and after), `git status` and stdout identical, 3.1 s.


## Open nits (none blocking; no spec clause left unproven)

* **N-1** `wave_b_check.py:941-942` — AC-004's executed-constants cross-check is `if geom:` guarded, so
  a missing `GEOMETRY` line *skips* instead of failing, unlike the hard `RECTS`/`SPAWN` errors
  (`:1236-1243`). Proved: `/tmp/d9`, artifact with the `GEOMETRY` line deleted + `--artifact-only` →
  9/9 rc=0. One-line fix: error when `geom` is empty. (Exposure needs a doctored artifact, not just a
  missing toolchain.)
* **N-2** `:1009-1010` / `§M12` — when the *product* is the thing that diverged, the battery reports
  `victim …: чистое сравнение уже разошлось — контроль бессмысленнен`, i.e. it blames the control. The
  verdict is still a correct red on the right check; wording only.
* **N-3** `main.swift:52-55` `fmt` prints `%.0f`, so SPAWN/PISTON/PLANESRC columns cannot express
  sub-tile drift (D11 passed at `−0.5`), while `RECTS` uses `%.1f`. Consider `%.1f` throughout, or
  state the 1-px granularity in the meter header's "пиксель-в-пиксель" claim.
* **N-4** `--artifact-only` still returns rc=0 on a mutated product (`/tmp/d1` probe) — legitimate as an
  explicit opt-in (the line prints `коммиченный (--artifact-only)`), but pinning the artifact's SHA-256
  in `EXPECTED` would make even the offline mode detect a stale artifact.
* **N-5** `release.md:19` — "12-ablation battery" is stale; `wave_b_ablations.txt` now carries 14
  mutation sections (A1–A8, B1–B4, M12, M13). Conservative direction, but the metric is quoted in the
  go/no-go evidence. Also cosmetic: two headings are glued (`### M12 restored; ### M13 …`,
  `M13 restored; ### FINAL GREEN baseline`) and `### R1-1 battery …` is a header with no run under it.
* **N-6** `PLANESRC` (125 artifact lines) and the 4th field of `SPAWN` (`plane`) are parsed
  (`:523-524`, `:529-532`) but never asserted; harmless given D12's transitive binding, but they inflate
  the apparent executed-coverage surface.

## Numbering note (so the record is unambiguous)

My original report carried **F-1…F-6** (two blocking, four non-blocking); there was no **F-7**, and the
decorative-control census was §4/§7 analysis rather than a numbered finding. Mapping used above:
F-1 rects tautology → **closed**; F-2 silent-green without `swiftc` → **closed**; F-3 preference
mutant-equivalence → unchanged, non-blocking (disclosed at `wave_b_deltas.md:138`); F-4 per-map buried
enumeration → **not addressed** (`wave_b_deltas.md` untouched at 21:21:25; buried appears only as the
aggregate at `:137`), still non-blocking — I re-derived the 48 names independently last round, so it
costs a reviewer effort, not correctness; F-5 base-side provenance → **improved** (the base algorithm is
now git-anchored *and* ported independently; base *data* remains pinned via the manifest, which I
re-verified against `git ls-tree 295690b`); F-6 receipt staleness → **closed** (P-1 keeps it a standing
step, not a defect).

## Disposition

Test story **PASS** at this fingerprint. Required before merge, in order: apply N-1 (or accept it as a
disclosed nit), refresh the `release.md` ablation count (N-5), then re-run `wave_b_check.py` and
re-record the gate once all writers in this worktree have settled (P-1). No product change is required
by this review; the SpriteKit visual item (code review R1-2) and the macOS play-checks in
`release.md` remain the human's call, and this pass confirms they are genuinely outside what the Linux
net can prove.
