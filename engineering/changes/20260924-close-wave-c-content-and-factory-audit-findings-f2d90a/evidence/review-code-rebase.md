# Rebase verification — change `f2d90a` (wave C onto A+B main)

- Reviewer: `code_reviewer`, follow-up to `evidence/review-code.md` (round 1, pre-rebase bytes)
- Tree: `/home/pall/projects/.exolon-wave-c/exolon` @ **HEAD `4bebb3e5e5d7`**, `origin/main` =
  **`3407c378e2ed`**, `merge-base(HEAD, origin/main)` = `3407c37`
- Effective change is now **committed**: `3407c37..HEAD` = `ed687a0` (all product changes) +
  `4bebb3e` (evidence/docs only — it touches **no** product file). The working tree is clean, so
  "uncommitted tree IS the change" no longer holds; scope = `git diff 3407c37..HEAD`.
- READ-ONLY held: the real worktree is byte-untouched (`git status --porcelain` → 0 entries after all
  runs) and, critically, **no ref pollution**: every mutating experiment ran in a
  `git clone --no-hardlinks /tmp/bclone` with its **own** `.git` dir, so no write could land in the
  shared worktree gitdir. Re-checked at the end: `git show-ref | grep -c 'heads/origin'` → **0**.
  (I deliberately did *not* `cp -a` this time — that is precisely how the `refs/heads/origin/main`
  incident arose.)
- `wave_b_check.py` writes `wave_b_deltas.md` into its own evidence dir on every run, so it was run in
  the clone only; running it in place would have moved the tree fingerprint and stale-ed every receipt.

## VERDICT: **PASS for merge.** All six briefed items verified; the writer's claims reproduced exactly.
One substantive new finding (N1, wording — not a blocker), plus my round-1 F1 confirmed still unfixed.
I do **not** reintroduce F3: the owner re-rule in `release.md` (2026-09-25, "нет у меня маков") makes it
an accepted permanent residual, and the mitigations are now *executable* rather than prose (§G).

---

## (1) `TMXLevelRuntime` beam area — **BOTH sides preserved, proven by set difference**

The airtight test: which lines did each side contribute, and did the merge lose any?

- Lines present in B's main (`3407c37`) but **absent** in HEAD: **exactly 7**, and they are precisely
  the seven legacy `if / else if source.contains("…")` condition lines that `classify()` replaces.
  Nothing else from B vanished.
- Lines contributed by C's commit but absent from HEAD: **0**.
- C's added lines are **byte-identical** to what I reviewed in round 1 (85 in `TMXMapLoader.swift`,
  12 in `GameScene.swift`, 55 in `TMXLevelRuntime.swift` — all three `diff` comparisons `IDENTICAL`),
  so every round-1 verdict (order preservation, footprint measurements, label/isSafeModel
  equivalence, debug-overlay gating, `break` re-binding analysis) carries over unchanged onto these
  bytes.
- **C's exhaustive switch survived:** `switch TMXSourceMarkerKind.classify(sourceBlock: source)` at
  `TMXLevelRuntime.swift:415`, 9 `case .X:` arms (`:416,419,424,427,429,438,452,465,474`),
  `case nil:` at `:482`, and **no `default:` inside the marker switch** (verified by indent-scoped
  regex over the switch body). The single `default:` at `:488` is the pre-existing
  `switch object.name` arm — legacy, and round 1 established 20/20 shipped object names are handled.
- **B's beam machinery survived untouched:** `beamBoxes: [CGRect] = []` (`:282`),
  `beamBoxes.append(box)` inside `case .forceField:` (`:418`, with B's rect
  `CGRect(x: sx, y: max(0, bottomY - 240), width: 48, height: 272)` intact), and the post-loop
  `for group in TMXBeamGrouping.groups(for: beamBoxes)` (`:508`) → `ForceFieldBarrier(hitbox:…,
  field:)` / `forceFields.append(side)` / `beamFields.append(field)`. I byte-compared both post-loop
  regions against `3407c37`: **2328/2328 and 1396/1396 chars, identical**. The forceField body is
  B's (`beamBoxes.append`), the arm label is C's — the correct merge, not a side winning.
- `break` re-binding still safe: the outer `case "source_marker":` body still ends at the inner
  switch (`:488` `default:` follows), so inner-vs-outer `break` remains a no-op (round-1 §2).

### B's meter, run by me on this tree — writer's claim **reproduced exactly**

| `wave_base()` | result |
| --- | --- |
| `merge-base(HEAD, origin/main)` = **3407c37** (this branch's real condition) | **8/9 PASS**, `FAIL no_magic_offsets`, rc=1 |
| pinned to **17a742a** (B's own base) | **9/9 PASS**, `RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC`, rc=0 |

The *sole* error at 3407c37 is B's own sanity threshold, not a violation:
`added-lines скан странно пуст: файлов=3 строк=95` (requires ≥7 files / ≥150 code lines). There are
**zero** `FORBID-001 added …` findings, and at 17a742a the scan covers **332 code lines in 9 files**
— which *includes* wave C's 95 added lines — and still reports 0 violations. So:

- every SEMANTIC probe of B passes post-rebase (`spawn_ground_all_maps`,
  `piston_anchor_all_pistons`, `beam_shared_hp_all_maps`, `bullet_cull_bounds`, plus
  `zone_index_formula`, `controls_flip`, `single_surface_query`, `pinned_geometry_unchanged`);
- wave C introduces **no** ±16 / 528 / 544 / 560 / per-map literal under B's FORBID-001 rules;
- the trip is a scoping artifact of `wave_base()` (`wave_b_check.py:646-660`) on a rebased branch, and
  it fails **loudly** rather than vacuously — correct fail-closed design.

## (2) README both-added resolution — **clean, no truncation**

`HEAD == base(3407c37) + appended C block` evaluates **True**. 49 base lines → 56 lines, **0 base lines
missing**. Both sections present in order: `## Structured gameplay event log (wave A, 2026-09-24)`
(:25) and `## Level content contract` (:51); all 7 C-added lines present verbatim, including the
P1-12 ruling wording and the issue-#11/#16 "remain OPEN" status line. A's bullet list (P1-9/P1-4/P1-8/
P1-6) is fully intact above C's section.

## (3) Refs hygiene — **confirmed repaired and staying clean**

- `git show-ref | grep 'heads/origin'` → **empty** (no `refs/heads/origin/main`).
- `git show-ref | grep 'heads/'` shows only the 9 legitimate local branch refs.
- `git rev-parse origin/main` → `3407c378e2ed17ad223f13b85792cd68b2155025` ✓ (correct remote-tracking
  ref, under `refs/remotes/`, where it belongs).
- Re-verified after my own clone-based experiments: still 0. My `origin/main` pins for the B
  reproduction were created with `update-ref refs/remotes/origin/main …` **inside the clone**, whose
  `.git` is a real directory (independent object store), so nothing could write through a worktree
  pointer.

## (4) Rb-1 — **closed; the fix demonstrably bites (and the old gate was worse than broken)**

`swift_targets()` (`wave_c_check.py:681-699`) now unions three sources: `295690b..HEAD`,
`git diff HEAD`, and untracked `*.swift`. `BASE_COMMIT` stays **`295690b`** (the route base — they
re-anchored AC-005's *arm* baseline but did **not** quietly shrink the parse gate), giving
**19 targets** including `BlasterBullet.swift`, `Grenade.swift`, `TMXTileMapRenderer.swift`.

My own committed-garbage probe in the clone:

| | result |
| --- | --- |
| Append `struct CommittedGarbage { let broken: Int` (unclosed) to `Exolon/GameCore/Weapons/BlasterBullet.swift` **and commit it** (tree clean vs HEAD) | `safe_models_are_labeled` **FAIL** → `swiftc -frontend -parse failed for Exolon/GameCore/Weapons/BlasterBullet.swift: :65:1: error: expected '}' in struct` → `RESULT: WAVE_C_PROBES_FAIL` |
| **Control** — the pre-Rb-1 derivation (working diff only) at that same commit | **0 targets, verdicts `{}`** → garbage **completely invisible** |
| Guard control on the honest tree | `parse_gate_covers_committed_changes: true` (requires targets ∖ working-diff ≠ ∅ **and** one of BlasterBullet/TMXTileMapRenderer/Grenade present) |

The control is stronger than the writer's claim: after the rebase *and* the commit, the old
working-diff derivation degenerates to **nothing at all** — the gate would have been vacuously green
over zero files, not merely missing one file. The file I chose is one wave C never touches, so this is
exactly the silent-drop-the-tree failure mode Rb-1 described.

## (5) Re-baseline honesty — **verified by independent three-way arm fingerprints**

I recomputed each of the seven legacy arm bodies (comment/whitespace-normalized) across
`295690b → 3407c37 → HEAD`:

| arm | 295690b | 3407c37 (B) | HEAD (C) | 3407c37→HEAD equal | **295690b→3407c37 changed** |
| --- | --- | --- | --- | --- | --- |
| `beam_` | `255b9c7f5fec` | `032dd2537e1f` | `032dd2537e1f` | ✔ | **yes** |
| `topdown_electro` | `14ebe56a5008` | `14ebe56a5008` | `14ebe56a5008` | ✔ | no |
| `blinker` | `14ebe56a5008` | `14ebe56a5008` | `14ebe56a5008` | ✔ | no |
| `stage_end` | `e1380bad8777` | `e1380bad8777` | `e1380bad8777` | ✔ | no |
| `changing_room` | `5961bb7db5e7` | `5961bb7db5e7` | `5961bb7db5e7` | ✔ | no |
| `beacon_base` | `2e7aea5fbdd1` | `2e7aea5fbdd1` | `2e7aea5fbdd1` | ✔ | no |
| `control_beacon` | `a62f4f87080b` | `a62f4f87080b` | `a62f4f87080b` | ✔ | no |

**Exactly one** arm differs between the old and new base, and it is B's intentional, B-meter-verified
beam-pool rewrite (`ForceFieldBarrier(hitbox:)`/`forceFields.append`/`rootNode.addChild` →
`beamBoxes.append(box)`). So:

- the re-anchor to `3407c37` absorbed **one legitimate externally-gated change and zero drift** — no
  unrelated arm got laundered past AC-005;
- `arm_deviations: []` with `deviation_ruling: ''` and `deviations_honored: []` is **honest**, not
  convenience: after re-anchoring, no arm deviates, so nothing *may* be excused. They did not add a
  beam_ deviation to paper over it;
- `ac005-rebase-protocol.txt`'s own precondition ("re-baseline only if every non-beam arm is still
  identical") is **independently satisfied** — the six non-beam arms match even the original
  `295690b`;
- coverage was preserved, not lost: B's beam rewrite is still asserted, now by B's
  `beam_shared_hp_all_maps` (green), rather than by C's AC-005;
- `covered_marker_digest` is unchanged from round 1 (`545e281f470c0900…`, `covered_markers 76`,
  `compared_against "3407c37 (TMXLevelRuntime.swift)"`), i.e. the rebase moved the reference blob and
  not the projection.

## (6) Contours, run by me

- **`wave_c_check.py`: 9/9 PASS, 60 named controls, 52→60 all true, 0 problems.** I counted from live
  `--json`: 6+5+11+3+6+5+10+11+3 = **60** (`manifest_selfcheck` reports under `tamper_controls`, so a
  naive counter sees 49 — matches the writer's 60 exactly). Includes the executed-product contour and
  its negative control.
- **A's `gameplay_log_check.py`: `RESULT: PASS (28/28 checks passed)`, rc=0** on the rebased tree —
  including `touched_swift_files_parse_clean` (13 files, injected-garbage control),
  `stream_invariants` (179 671 records / 39 streams) and `kill_switch_no_file`. It did not dirty the
  clone.
- **B's `wave_b_check.py`:** see §1 — 8/9 here, 9/9 with its own base.
- `git status Exolon/Resources` → **0** (FORBID-001 guard holds at the merged state too).

## (G) Bonus: I attacked the test-review F1 fix (AC-004's corpus branch) — it holds

Round 1 I verified the manifest seal recomputes; I did **not** notice that `manifest_selfcheck` called
`validate_manifest(manifest)` without `corpus_hashes`, so the data-vs-manifest branch never ran in the
probe. The package now says so openly (`evidence/level-content-v1-binding-note.md`). I reproduced both
attacks in the clone:

- fabricate `maps.L02S16.background = zone_999_original.png` and re-seal with the old construction →
  **FAIL**, two independent reasons (corpus says the map references `zone_040_original.png`; the new
  salted `INTEGRITY_BIND` binding rejects a re-seal computed without it);
- fabricate `background_sha256 = 'ab'×32` and re-seal **correctly** with `body_digest` → still **FAIL**:
  `declares background_sha256 'abababab…' but the resolved file bytes are '60d81c4d0bb11cf4'`.

That is the right architecture — the seal is only an accident guard (and `binding_limit` says so
honestly); the live corpus re-derivation is the authority. `manifest_selfcheck` grew 7 → 11 tamper
controls. Separately, R1's staleness is now surfaced as explicit non-fatal WARNINGs for both
`v3_measurements.py` and `linux_static_audit.py` instead of being silent.

---

## New findings

**N1 — Suggestion, and the one thing I'd genuinely change: the shipped safe-model label states a false
epistemic claim about `blk_gunMachine_BOTTOM`.**
`Exolon/GameCore/Levels/TMXMapLoader.swift:641` renders
*"a distinct source action cell exists but **its type is not identifiable in-tree**; behaviour
deliberately NOT implemented"*. But `ORIGINAL_MECHANICS.md` §**"Stationary gun machine"** (:36-42) does
identify and specify it in this repository: random firing cadence from the original RNG; bullet origin
at the action cell `X` / `Y+3` original px, i.e. 4×4 projectile centre at
`turret.left + 2`, `turret.bottom + 56` in the 2× conversion; bullets travel left and are not
blaster-destroyable; the turret is grenade-destroyable for 150 points via the generic destroyable
table — and `:170` lists "gun machines" among the action markers that **must** have a runtime
implementation. This package's own `analysis-docs_researcher.md:70` verified that anchor
("OM 36-41 = 'Stationary gun machine' ✓ **VERIFIED**"), and `tasks.md` D2 rules the disposition without
ever engaging that section. What is genuinely missing is only the **numeric type-11 → entity binding**,
because `game_init_actions.asm` / `data_zone_data.asm` are not in the tree (their 56-vs-18 argument
stands for that narrow claim).

Why it matters: the label is the artifact that *propagates* — into the debug overlay node names,
`marker-disposition-v1.json`, and the coverage table. Read literally it tells the next agent there is
nothing to learn here, which is what would keep an OM:170-required mechanic unimplemented forever. The
*code action is correct* (record, label, do not arm, do not invent) and I am not asking to arm it.
Fix is cheap and self-propagating: reword to e.g. *"mechanics documented in-tree at
ORIGINAL_MECHANICS.md:36-42; action-type binding not derivable (game_init_actions.asm absent); NOT
implemented"* — the string exists in exactly 2 places (`TMXMapLoader.swift:641`,
`marker-disposition-v1.json`) and `safe_models_are_labeled` enforces their equality, so the meter
guarantees the reword cannot be half-applied. Then carry "implement stationary gun machine" as an
explicit open item rather than a closed "unknowable".

**N2 — Carry-over, still unfixed (my round-1 F1, unchanged by this round):** the safe-model overlay
rect anchor. `TMXLevelRuntime.swift:539-541` still claims the box is "converted to pixels the same way
`beaconBase` converts its own … anchored so its top edge sits at the marker's source row", while the
helper's `rect:` line (`:551`) computes `y = max(0, bottomY - height)` = rows `sy+2…sy+4`, whereas
`beaconBase` (`:445-450`) covers
`sy…sy+2` — **32 pt low**, overlapping the scenery's bottom row plus two cells of terrain. Round 1's
added-line comparison proves these bytes are identical, so nothing was fixed here. Partially mitigated
now: `overlay_binding_problems` + `overlay_deletion_detected` / `overlay_label_strip_detected` /
`honest_overlay_binding_accepted` assert that the overlay consumes `safeModelMarkers`, draws each
recorded rect and carries the label — but nothing asserts the rect covers the right cells, so a bound
outline can still be a wrong outline. Debug-only ⇒ non-blocking; fix it in the same wording pass as N1
(`y: max(0, map.pixelHeight - (sourceY + CGFloat(cells.height)) * 16)`, or correct the comment).

**N3 — Integration note, not a wave-C defect:** because `wave_base()` resolves to `merge-base(HEAD,
origin/main)`, B's meter exits **rc=1 on any later rebased branch**, for a reason unrelated to that
branch (its added-lines scan shrinks to the successor's 3 files). The fail-closed threshold is the
right behaviour, but the series contour will read as "wave B mismatched" to anyone running it on
wave C/D. Recommend B's package re-anchor or `main` record the caveat. Wave C must not edit B's meter.

**N4 — Nit (unchanged from round 1 F4):** `evidence/README.md` is still the 3-line factory stub while
the package now holds a 2294-line meter, 2 new proof files, a binding note and 3 review reports.

## Superseded / deliberately not raised

Round-1 **F3** (two of three Swift files parse-gated, not type-checked) is **not** a merge condition per
the owner re-rule in `release.md` (2026-09-25): no macOS/Developer ID exists, so it is an accepted
permanent residual and I will not reintroduce it. The mitigations are now executable, which is the
right response: the parse gate covers all 19 committed-since-base Swift files with a falsifiability
self-test (`parse_gate_selftest`, and my N/A-but-real garbage probe), the overlay consumers are
source-asserted, and `rendering_evidence_limit` states the boundary instead of hiding it. Round-1 F2
(`unmatchedSourceMarkers` unobserved) and F5 (rollback trigger wording) stand unchanged and remain
non-blocking.

## Summary (6 lines)

1. **PASS for merge at `4bebb3e`.** Conflict zone 1 preserved **both** sides: C's exhaustive
   `classify()` switch (9 arms + `case nil:`, no `default:` at `:415-482`) and B's `beamBoxes.append`
   plus byte-identical post-loop grouping (`2328/2328`, `1396/1396`); the only 7 lines lost from B are
   the 7 legacy condition lines C replaces, and 0 C-only lines vanished.
2. **B's meter claim reproduced exactly**: 8/9 here with the sole failure being its own
   `n_files>=7 and n_code>=150` threshold (`файлов=3 строк=95`) and **zero** FORBID-001 violations;
   pinning `wave_base` to `17a742a` gives **9/9 `ALL_WAVE_B_CHECKS_MATCH_SPEC`** over 332 added code
   lines — which include wave C's, so C introduces no ±16/per-map literal.
3. **Re-baseline is honest**: my three-way arm fingerprints show exactly one arm (`beam_`) differs
   between `295690b` and `3407c37` — B's gated rewrite — so `arm_deviations: []` reflects genuine
   equality with the new base, not an excuse recorded for convenience, and AC-005's own precondition
   ("every non-beam arm identical") holds even against the original base.
4. **Rb-1 closed and biting**: committed syntax garbage into `BlasterBullet.swift` (clean vs HEAD, a
   file wave C never touches) reddens their meter with the exact parse error, while the old
   working-diff derivation at that commit yields **0 targets / `{}` verdicts** — the pre-fix gate was
   vacuous over nothing, not merely incomplete.
5. **README, refs and all three contours check out**: `HEAD == base + appended C block` with 0 base
   lines lost and both sections intact; `refs/heads/origin/*` empty and `origin/main = 3407c37`
   (my experiments isolated in a `--no-hardlinks` clone so no write-through was possible); `wave_c_check`
   **9/9 with 60/60 controls**, A's `gameplay_log_check` **28/28 rc=0**, `Exolon/Resources` untouched;
   and I independently broke and then correctly re-sealed the manifest — both attacks now red.
6. **Two things to change, neither blocking**: **N1** the shipped label's "its type is not identifiable
   in-tree" is contradicted in-repo by `ORIGINAL_MECHANICS.md:36-42` + `:170` (reword in 2 places, the
   meter enforces equality, and carry "implement gun machine" as open); **N2** my round-1 overlay
   rect-anchor error (32 pt low) is still present and still debug-only. F3 stays superseded per the
   owner re-rule.
