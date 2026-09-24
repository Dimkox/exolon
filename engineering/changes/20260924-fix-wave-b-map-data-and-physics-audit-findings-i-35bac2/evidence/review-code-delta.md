# Delta re-review — wave B (closure of code R1-1 + test F-2)

Change: `20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2`
Tree: `/home/pall/projects/.exolon-wave-b/exolon` @ base `295690b`
Predecessor: `review-code.md` (BLOCK, single Critical R1-1 = tautological INV-002 rect check)
Role: `code_reviewer`, READ-ONLY. This file is the only write; the real tree is byte-identical to the state
under review (verified: `cmp` of both mutated-in-clone files + `git status` unchanged + fingerprint below).

## FINAL VERDICT: **PASS** for the delta scope. R1-1 is closed and I verified it by breaking it myself.

I lift my BLOCK. You may record the code-review receipt on this word. Nothing in the delta scope is
blocking; three non-blocking follow-ups are listed (D-1, D-2, and two carried-over items that were *not*
addressed — R1-3, R1-4), none of which affects merge correctness of the product change.

---

## 0. What actually changed since `review-code.md`

Product: **comment-only change, +4 lines** — `TMXMapLoader.swift:227-231` (the `pistonGroundY` doc), which is
exactly my R1-4 wording point about the shaft pistons. `git diff` of the old vs new product delta shows no other
change; code-line count in the meter's added-lines scan is still 237 ✓. All six of my original verdicts therefore
stand unchanged.

Evidence/paperwork: `wave_b_check.py` (three-way rect check + §4b mutant battery + TOOL_ABSENT exit),
`wave_b_harness/main.swift:67-75` (new `RECTS` emission), `wave_b_swift.txt` (125 `RECTS` lines),
`wave_b_ablations.txt` (§M12/§M13), `rollback.md`, `release.md`, `tasks.md` review close-out.

Method: mutation experiments ran in a throwaway clone **`/tmp/mut`** (`rsync` of the tree without `.git`, then
`git init` + `git fetch` from the main repo + `git read-tree 295690b` so `git diff 295690b`, `git show 295690b:`
and the blob manifest all behave as in the real worktree — verified: the clone reproduces the change as
"8 files, 419 insertions(+), 87 deletions(-)"). The real tree was never mutated. `swiftc` 6.4 at
`/opt/swift/usr/bin/swiftc`, so the executed leg really compiled and ran in every experiment.

---

## 1. My `y: run.top + 7.5` mutation reproduced — INV-002 reddens, restore re-greens ✅

Baseline in the clone: `RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC`, rc=0,
`rects base-порт==new-порт==исполненный на 125/125 (всего 1437 rect'ов)`, live harness byte-equal to the
committed artifact.

| # | mutation (in `/tmp/mut`, product source) | rc | `pinned_geometry_unchanged` | `controls_flip` |
|---|---|---|---|---|
| A | both `y: run.top - tileHeight` sites → `+ 7.5` | **1** | **FAIL** — 0/125 maps agree, 0 rects (`RESULT: MISMATCH`) | **FAIL** ("victim L01S03.tmx: чистое сравнение уже разошлось" + live≠artifact) |
| B | flush site only (`TMXMapLoader.swift:259`) → `+ 7.5` | **1** | **FAIL** — 0/125 | **FAIL** |
| C | in-loop site only (`:255`, multi-run rows) → `+ 7.5` | **1** | **FAIL** — 50/125 agree (267 rects) ⇒ 75 maps diverge | **FAIL** |
| D | `tops.sort(by: >)` → `tops.sort()` (rect order) | **1** | **FAIL** — 12/125 agree ⇒ 113 maps diverge | **FAIL** |
| restore | product file `cmp`-identical to real tree | **0** | PASS — 125/125, 1437 | PASS |

Mutant D's "113 maps" independently reproduces the order-mutant count I measured on my own transcription in the
first review (113) — the two implementations disagree in exactly the same set of maps, which is itself evidence
the comparison is geometry- and order-sensitive rather than string-matched.

Mechanism, confirmed by reading: leg (c) is **compiled product code**, not a mirror —
`main.swift:71` `let rects = query.collisionRects` from the live `TMXMapLoader.swift` copy that `run.sh` builds
(still under its one-import-line byte delta control), and `harness()` feeds the **live** output into the
comparison (`_harness_result["artifact"] = parse_artifact(artifact_text if not live else live)`), so a product
edit reaches the check in the same run. `EXPECTED["renderer_rects_total"] = 1437` is pinned numerically
(`:129`, asserted at `:1248`), so a defect shared by all three ports would still redden on volume.

## 2. §M12 chronology and the §4b synthetic-mutant battery ✅

`wave_b_ablations.txt` structure: `baseline GREEN` → A1-A4, B1-B4, A5-A8 (12 pre-review ablations) →
`FINAL restore GREEN` → **`### R1-1 battery (post-review): three-way rect check mutation controls`** →
`### M12 product collisionRects y := run.top + 7.5 (reviewer's case)` → `### M12 restored; ### M13 spawn
halfWindow doubled (2 tiles)` → `### M13 restored; ### FINAL GREEN baseline`. 18 sections; each mutant is
followed by its restore and a green re-run, so the chronology is explicit.

* §M12's logged output matches my own run A line-for-line: `rects base-порт==new-порт==исполненный на 0/125
  (всего 0 rect'ов)`, `FAIL pinned_geometry_unchanged` with per-map `base=N new=N exec=N/N` (i.e. counts agree,
  coordinates don't), `FAIL controls_flip`, and `артефакт Swift: живой (совпал: False)` — the harness
  byte-control fires too. §M13 (halfWindow×2, my R1-4 concern) reddens `spawn_ground_all_maps` via
  "harness разошёлся с зеркалом" ✓.
* §4b (`wave_b_check.py:992-1014`) is a genuine falsifiability guard, not decoration: it demands a victim map
  with ≥2 distinct rects, demands the clean three-way comparison agree *first* (otherwise "контроль
  бессмысленнен"), then requires `base_r != mut_y` (**"+7.5 (случай ревьюера)"** — literally my case),
  `base_r != mut_order`, `new_r != mut_base`. My experiments A-D additionally prove that guard is not the only
  line of defence: a mutant that leaves the synthetic battery green still reddens the corpus comparison.

Chronology nit (cosmetic, D-3 below): the 14 pre-review runs still print the superseded line
`rects идентичны на 125/125` — the very wording R1-1 showed to be vacuous — separated from the corrected wording
only by the `post-review` section header at `:364`.

## 3. Do the base-port anchors really bind to the base blob? ✅ (with one honest narrowing)

* All four anchor strings are present in `git show 295690b:Exolon/GameCore/Levels/TMXTileMapRenderer.swift` and
  **absent from the working-tree renderer** (tested each string in both texts; the near-miss at
  `TMXTileMapRenderer.swift:71` is the visual-sprite placement `y: map.pixelHeight - CGFloat((row + 1) * …)`,
  which does **not** satisfy the anchor `let y = …`). So the anchors can only be satisfied by the base commit's
  deleted function, never by the current file.
* `git_show_base()` shells out to `git -C ROOT show 295690b:<path>` — a literal sha, not `HEAD`/a branch — and
  the check is fail-closed: `base_renderer is None ⇒ errs.append(...)` (red, not skipped). Verified live in the
  clone, where the object had to be fetched from the main repo.
* The anchors do not by themselves prove the port is a faithful transcription (they only prove the blob still
  contains that algorithm). I closed that gap myself: **my own independent transcriptions** vs the meter's ports
  over all 125 maps —
  `base_build_collision_rects` vs my base-from-blob port: **0 mismatches**;
  `query_collision_rects` vs my new-Swift port: **0 mismatches**;
  executed product `RECTS` leg vs my base port: **0 mismatches**; total **1437** in both. The three legs are
  textually and algorithmically distinct (gids row-major while-merge vs unique-top cell merge vs compiled Swift),
  so base-vs-new is now genuinely base-vs-new.

Residual (D-2): I re-introduced the tautology *in the clone's meter only* — `new_rects = base_rects` at the
comparison site — and the run stayed **green (rc=0)**. The claim "string-anchored … so the port cannot silently
drift" (`tasks.md:140`) is therefore slightly stronger than reality: no check detects an alias collapse of the
*base-vs-new* leg. The blast radius is small — with the same alias in place, my product mutation still reddened
(rc=1, 0/125) because the executed leg stayed independent — so the shipped-geometry guarantee is machine-guarded
while only the "reproduces base" framing is guarded by review + the 1437 pin. Suggest a cheap fixture where the
two algorithms provably differ (a synthetic map whose insertion-order top list differs from row order), asserted
`base_port != aliased_port`.

## 4. F-2 closure (swiftc absence can no longer be silently green) ✅ tested on this host

* `env PATH=/usr/bin:/bin python3 wave_b_check.py` (swiftc lives in `/opt/swift/usr/bin`, so it is genuinely
  missing): prints `RESULT: TOOL_ABSENT (swiftc недоступен; … для оффлайн-режима нужен --artifact-only)` and
  exits **rc=3** even though all nine checks printed PASS against the committed artifact — the distinct
  non-green code is exactly the fix.
* `env PATH=/usr/bin:/bin … --artifact-only`: **rc=0**, and the footer labels the source honestly —
  `артефакт Swift: коммиченный (--artifact-only) (совпал: False)`. Offline mode is opt-in and self-disclosing.
* `tasks.md:126-128` documents both behaviours. Accurate.

## 5. The four new product comment lines (the only product delta) — one factual error

`TMXMapLoader.swift:226-230` asserts the three shaft pistons' "hit span holds **no Collision cell at all**" and
that they "rise over a **bottomless shaft**". Recomputing the tread spans (`x0 = markerX+3`, `width 42`,
limit `= anchor+64 = 64`):

| piston | tops in tread span | tops ≤ limit | map-wide `fallbackPlaneY` |
|---|---|---|---|
| L01S15 x=128 | 160, 192 | none | 48 |
| L02S23 x=400 | 272 | none | 48 |
| L05S23 x=400 | 272 | none | 48 |

So the span **does** contain Collision cells; what is absent is any cell **at or below the raised-tread line**,
which is the actual condition in `groundY(x0:x1:atOrBelow:)`. The rest of the sentence is correct and useful —
the fallback really is the global `fallbackPlaneY` (48 on all three), the identification of the three rows is
exact, and "exactly the plane the shipped piston/fallback code used" checks out (`TMXLevelRuntime.swift:89`
publishes the same plane as `groundY`). Comment-only, no behavioural consequence: propose
"no Collision cell **at or below the tread line**" and drop "bottomless".

## 6. Gate receipt / fingerprint reconciliation

* The re-recorded receipt is genuine and **currently binds**:
  `.grok-stack/runtime/receipts/35bac25f12ae/verification.json` → `kind=verification`, `status=pass`,
  `criterion_ids=['AC-005']`, `created_at=2026-09-24T22:02:59Z`, `tree_fingerprint=a5ad67be5a00bc4b…`;
  recomputing `adaptive_grok.util.tree_fingerprint` on the real tree returns the same value.
* **Discrepancy to reconcile:** the identifier quoted to me (`9491fdcaa2…`) does **not** appear anywhere in that
  receipt (all fields searched; the values present are `a5ad67be5a…` tree, `f4d5af9a3ab9…` spec fingerprint,
  `4ac8c84c8ab7…` spec digest, route `35bac25f12ae`, base `295690b…`). If `9491fdcaa2…` came from a console line,
  it is not the tree fingerprint the receipt binds to — worth checking before you cite it in the PR body.
* This file will stale the receipt (the change package is untracked and `changed_files` includes it via
  `git ls-files --others --exclude-standard`), so re-record `python3 scripts/grok_verify.py --mode pr` after the
  reviewers settle. Note `__pycache__/` is git-ignored, so the meter's byte-compile side effects do **not** move
  the fingerprint; `write_if_changed` also kept `wave_b_deltas.md`/`wave_b_swift.txt` byte-stable through my five
  meter runs in the clone.

## 7. Carry-over status of my earlier non-blocking items

* **R1-2 (piston retracted sprite draws over the ground)** — correctly restated with my 43/46 number and deferred
  to a human macOS play-check in `tasks.md`; `release.md` unchanged on this point. Open by design, not blocking.
* **R1-3 (spawn lower-Y tie-break exercised by 0/125 maps, no synthetic equidistant fixture)** — **not**
  addressed. `wave_b_check.py:732` still asserts only the corpus pick; §4b added mutants for the *rect* leg but
  none for the spawn tie. Flipping `top < anyBest!` in `TMXMapLoader.swift:209` would still keep everything green.
* **R1-4** — half applied: the piston prose was fixed (and is where the new D-1 error lives), but
  `change-spec.yaml` AC-001 still reads "within one **half-tile** (+/-16 px)" while the code passes
  `halfWindow = CGFloat(tileHeight)` = one full tile; equal today only because 125/125 maps are 16 px tiles.
* **R1-5** (`beamFields` unread registry, handlers not cleared) — untouched; still fine to ship.
* **R1-6** — fixed: `rollback.md` now says `pinned_geometry_unchanged` and `single_surface_query` are
  **expected red** after revert ("the earlier 'stay green' claim was wrong by design") ✓.

## Findings

| id | sev | conf | file:line | summary |
|---|---|---|---|---|
| D-1 | Nice to have | high | `Exolon/GameCore/Levels/TMXMapLoader.swift:227-230` | New comment states the three shaft pistons "hold no Collision cell at all" / sit over a "bottomless shaft"; the tread spans do contain cells (tops 160/192 on L01S15, 272 on L02S23 and L05S23) — the true condition is "no cell **at or below** the raised-tread line (anchor+64)". Comment-only. |
| D-2 | Nice to have | high | `evidence/wave_b_check.py:1233-1244` (residual proved in `/tmp/mut`) | Nothing detects a re-alias collapse of the base-vs-new leg: setting `new_rects = base_rects` keeps the meter green (rc=0). The product-geometry guarantee survives (my mutation still reddens, rc=1) thanks to the executed leg and the 1437 pin, so this is a hardening suggestion: add a synthetic fixture where the base and new algorithms necessarily differ and assert the two ports disagree. |
| D-3 | Nice to have | high | `evidence/wave_b_ablations.txt` (`:2-25`, `:339-363`) | 14 pre-review runs still print the superseded vacuous line `rects идентичны на 125/125`, and one of them is titled `FINAL restore GREEN`, which reads as final unless the reader notices the `post-review` header at `:364`. Also `release.md:20` still says "12-ablation battery" while the log now holds 14 mutants + 2 green baselines. Label the pre-review block, or amend the count. |

### Closing note
R1-1 is resolved in the way I asked for: three independent implementations of the geometry, one of them the
compiled product, compared on count, order and coordinates, backed by a mutant battery that I re-ran and
reproduced, and a magnitude pin that matches my own measurement (1437). The check can now fail, and I made it
fail. **Delta scope: PASS.**
