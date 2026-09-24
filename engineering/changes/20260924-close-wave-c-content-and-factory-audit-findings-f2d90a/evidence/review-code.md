# Code review — change `f2d90a` (wave C content + factory audit findings)

- Reviewer: `code_reviewer` (route `f2d90a858699`, `review_agents` includes `code_reviewer`)
- Tree: `/home/pall/projects/.exolon-wave-c/exolon` @ HEAD `295690b7fc72` (uncommitted working tree IS the change)
- Method: read `git diff HEAD` plus surrounding implementation. Nothing below is taken from the PR
  prose; every load-bearing claim was re-measured, and the meter's guarantees were falsified against
  real mutated files in an isolated `/tmp` copy. **The reviewed worktree was not modified**: the three
  product files still hash `202cd23c97e1f2c9904c…` / `91f354db8708a5375b92…` / `f2eb43f2f842524647dd…`
  and `git status --porcelain` is byte-for-byte the state I first observed.

## VERDICT: **PASS** — no blocking finding. 5 non-blocking findings, 1 of which I would fix in this PR.

---

## 1. `TMXMapLoader.classify()` — order preservation: **verified, not merely asserted**

The doc comment at `Exolon/GameCore/Levels/TMXMapLoader.swift:405-406` claims the seven original
tests keep their historical order because "no shipped value currently matches two of them, but that
is a property of today's data". I measured that property instead of trusting it:

- 11 distinct `sourceBlock` values exist across `Exolon/Resources/*.tmx` (127 `source_marker` objects).
- Values matching **more than one** of the ten matcher tests: **0**.
- First-match result of `classify()` equals the first-match result of the base `if/else` chain for all
  eight legacy values (`blk_beacon_base`, `blk_beam_down`, `blk_beam_up`, `blk_blinker`,
  `blk_changing_room`, `blk_control_beacon`, `blk_stage_end`, `blk_topdown_electro`).
- The three new tests are appended **last** (`:415-417`), so no legacy value can be stolen by them, and
  `blk_gunMachine_BOTTOM` contains none of the seven legacy substrings, so it cannot be stolen from the
  new tests either. Order is therefore safe in both directions for the shipped corpus.

Correctness of the three new families: `mushroom`/`waggon` → `.inertScenery`, `gunMachine_BOTTOM` →
`.unconfirmedAction` (`:415-417`). Both `.inertScenery` mappings sharing one label is deliberate and
consistent with `safeModelLabel` (`:393-403`). `isSafeModel` (`:382-390`) and `safeModelLabel`
(`:393-403`) each enumerate all 9 cases exhaustively — no arm can drift silently, because a missing
case is a compile error in an exhaustive non-optional switch (proven in §3).

Consistency of label/footprint: `isSafeModel == true` ⟺ non-empty `safeModelLabel` ⟺ disposition
`safe-model` is enforced **as an equivalence** (not just a presence check) by
`disposition_consistency()` (`evidence/wave_c_check.py:631-652`), applied tree-wide over all 11 rows in
two probes. I confirmed the executed product returns exactly that mapping (see §4).

**Footprint claims are true and I reproduced them under the product's own solid-cell semantics**
(`TMXTileMapRenderer.swift:134` masks gids with `& 0x1FFF_FFFF`; 0 flag-only cells exist in the corpus,
so the mask does not change the result). Measured from the shipped Collision layer at the marker cell:

| family | comment claim (`TMXMapLoader.swift:421-426`) | my measurement |
| --- | --- | --- |
| `blk_mushroom` | uniform 4x3 (9/9) | `(4,3)` × **9/9** ✔ |
| `blk_waggon` | 5x3 (21/24), 10/15-wide are merged neighbours | `(5,3)` 21, `(10,3)` 2, `(15,3)` 1 ✔ |
| `blk_gunMachine_BOTTOM` | 4 wide on 18/18, height bleeds into terrain | width 4 on **18/18**; height `(4,2)`×2, `(4,3)`×5, `(4,4)`×11 ✔ |

The comment honestly labels the gunMachine height as "a bounded placeholder, not a claim about the
original artwork" rather than overfitting a number to 11 differing instances. Good discipline.

## 2. `TMXLevelRuntime` exhaustive switch — **seven arms verbatim, no `default:`, `break` re-binding is a no-op**

`Exolon/GameCore/Levels/TMXLevelRuntime.swift:366` replaces the chain with
`switch TMXSourceMarkerKind.classify(sourceBlock: source)`.

- **Verbatim check (mine, not the meter's).** I extracted both revisions independently — base from
  `git show 295690b:…TMXLevelRuntime.swift` and the working tree — and compared each arm body with
  comments and whitespace normalized. All seven are identical: `beam_`, `topdown_electro`, `blinker`,
  `stage_end`, `changing_room`, `beacon_base`, `control_beacon` → `True` each. The diff confirms only
  condition lines moved; every body line is a context line.
- **`break` re-binding — analysed, benign.** This is the one thing that could have silently changed
  behaviour, so it is worth stating explicitly: in base, the `break` at the old `:357`/`:363` bound to
  the **enclosing `switch object.name`**; in the new code it binds to the **inner** switch
  (`:376`, `:379`). That is only safe because the outer `case "source_marker":` body ends with the
  chain in both revisions — I verified nothing follows it before `default:` at `:441`. If a future edit
  appends code to that case body, the two `break`s stop being equivalent. No change needed today.
- **No `default:` introduced** in the inner switch. The pre-existing outer `default:` at `:441-445`
  (unknown object *names*) is untouched. I closed that loop independently: the corpus contains 20
  distinct object names and the factory handles **20/20** — **0** shipped objects reach the outer
  `default:`. So the "no silent drops" claim is not undermined by an unmetered neighbour path.
- **Nil arm genuinely records** (`:435-438`), and `case nil:` is required for exhaustiveness over the
  optional — so the miss path cannot be deleted without the compiler noticing.

## 3. The central engineering claim ("a new family is a compile error") — **proven by real typecheck**

This is the load-bearing property of the whole change, and `evidence/green-meter-run.txt` only records
`swiftc -frontend -parse`, which does **not** type-check and therefore cannot prove it. So I proved it
myself with `swiftc -typecheck` on a mirror that lifts the enum verbatim out of the shipped file:

| variant | result |
| --- | --- |
| A) 9 arms + `case nil:`, no `default:` (the shipped shape) | **typechecks clean** |
| B) one arm removed (a forgotten new family) | **`error: switch must be exhaustive`** |
| C) `default:` added | clean — i.e. the guarantee depends entirely on B holding |

The claim is true as written at `TMXMapLoader.swift:357-359`. Residual, honestly disclosed by the
author as `tasks.md` **R2**: `TMXLevelRuntime.swift` and `GameScene.swift` are SpriteKit-bound and
cannot be type-checked on this Linux host, so the shipped switch itself is parse-gated only. My mirror
covers the *mechanism*; it cannot cover the real file's own type-check. That gap is macOS-only and
already tracked — it does not block, but the merge must not be declared complete before the macOS build
runs (test-plan E2E).

## 4. `GameScene` debug overlay — **all call sites safe; zero behaviour change for existing rects**

- Signature gains `label: String = ""` (`GameScene.swift:1129`). All **15** pre-existing call sites
  (`:1079-1117`) pass no label → default applies → identical behaviour. I enumerated them rather than
  assuming.
- `node.name` is assigned **only** when the label is non-empty (`:1137-1138`), so no existing overlay
  node gains a name; and `childNode(withName:` appears **0 times** in the product — no lookup can be
  disturbed by the very long reason strings now stored as node names.
- Placement is behind the existing gate: `debugOverlay.removeAllChildren()` at `:1076` then
  `guard showHitboxes else { return }` at `:1077`, with the new loop at `:1123` after it. Safe models
  are therefore **invisible outside the opt-in debug overlay**, and no `SKSpriteNode`/`SKTexture` is
  created for them — so the change cannot alter shipped gameplay visuals. `currentLevel` is the same
  implicitly-unwrapped runtime the loop at `:1081` already dereferences.

## 5. `wave_c_check.py` — **honest.** I re-ran it and I broke it on purpose

- **Live reproduction.** `python3 wave_c_check.py` on this tree → `RESULT: ALL_WAVE_C_PROBES_PASS |
  probes=9 failed=0`, and `unchanged_marker_output` reports
  `data_digest == golden_digest == 545e281f470c0900…`, `covered_markers 76`, `covered_maps 37`,
  `deviations_honored []` — matching `evidence/green-meter-run.txt`.
- **52 controls, named and executed — confirmed by counting, not by trusting the tally.** I parsed the
  live `--json`: 45 entries under `controls` across 8 probes + 7 under `tamper_controls` in
  `manifest_selfcheck` = **52 named, 52 true**. (A naive counter that only reads `controls` sees 45;
  the recorded tally is right.)
- **Base side genuinely comes from Git, not from a golden.** `route_base_source()` (`:590-593`) and
  `base_branch_fingerprints()` (`:595-603`) read `git show 295690b:TMXLevelRuntime.swift`;
  `no_invented_content` diffs `git ls-tree`/`git hash-object` blobs (282/282 identical);
  `base_image_literals()` greps literals out of `git show` blobs. AC-005 cannot be satisfied by
  editing a JSON in this package.
- **The matcher table is parsed out of the product, and the product is compiled and run.**
  `CLASSIFY_RE`/`classifier_kinds`/`classifier_labels` read the shipped Swift, and
  `swift_product_evidence()` builds `TMXMapLoader.swift` + a probe and executes it over all 125 maps,
  with a negative control that the build must **fail** without the CoreGraphics shim
  (`negative_control_build_fails`). This is what closes the "four hand-copied mirrors that cannot
  detect the fix" defect the package names.
- **I falsified the probes myself (this is the check that matters).** Mutating real files in a scratch
  copy and restoring each time:

  | mutation to shipped code | expected | observed |
  | --- | --- | --- |
  | pristine copy (control) | AC-005 green | **PASS** |
  | `forceField` arm `height: 272 → 999` | AC-005 red | **FAIL** ✔ |
  | `beaconBase` arm `width: 64 → 80` (arm ≠ beam_) | AC-005 red | **FAIL** ✔ |
  | `stageEnd` arm gains an extra statement, no rect change | AC-005 red | **FAIL** ✔ |
  | `blinker` arm `break` → a behavioural append | AC-005 red | **FAIL** ✔ |
  | delete the `case nil:` recorder line | AC-001 red | **FAIL** ✔ |

  Detection is not confined to the `beam_` arm its own controls exercise, and it catches statement- and
  behaviour-level edits, not just geometry. The meter is not self-certifying.
- **Pre-change red is on record and consistent** (`evidence/baseline-meter-red.txt`: 76/127, 3 unclaimed
  values, "the source_marker case has no unmatchedSourceMarkers.append path"), so the green run is a
  real transition and not a tautology.

## 6. `level-content-v1.json` + AC-005 re-baseline protocol guards — **fail-closed and narrow**

- Manifest recomputes clean: `contract=level-content-v1`, 125 maps, `unique_count=101`, 24 pairs,
  `canonicalization_version=wave-c-canonical-1`, and `self_check.body_sha256` **recomputes to the stored
  value** (`237e406dfc8d559d…`) over the body-minus-self-check, so a tampered entry breaks it. Seven
  tamper controls in `manifest_selfcheck` all flip red, including `honest_manifest_accepted`.
- `arm_deviations` is `[]` and `deviation_ruling` is `''` in the committed baseline → AC-005 is
  fail-closed today; `deviations_honored: []` in my live run confirms no arm is currently excused.
- The escape hatch is provably narrow (`wave_c_check.py:655-668` + four in-probe guards): it honors a
  deviation only when `from` **and** `to` both equal the real digests computed from the base blob, and
  both `authorized_by` and `reason` are non-empty; a deviation for an arm that did not actually move is
  reported **stale** (`:816-820`); an arm outside the seven is an error; wildcards are rejected.
  `evidence/ac005-rebase-protocol.txt` additionally records a 4-step executed simulation (edit→red,
  deviation→honored-but-vacuous-guard-fires, blanket second deviation→stale, restore→green) — exactly
  the A→B→C integration hazard, and the vacuous-rect-control guard
  (`:861-866`) is the right instinct: it refuses to let a mutation control silently stop testing
  anything after wave B lands. **This is the correct shape for a re-baseline protocol.**
- Residual (accepted, not a defect): the deviation record is self-attested plaintext in an evidence
  file — the only real authority against a dishonest entry is human review of the PR. That is what this
  report is for; nothing here is cryptographic.

## 7. AGENTS.md engineering rules

- **No silent drops** — satisfied on the sourceBlock path and *structurally* enforced (exhaustive
  switch + `case nil:` + compiler), not just commented. §2/§3.
- **Backward compatibility, 76 legacy outputs byte-stable — where is it PROVEN?** Two independent
  places, and I checked both: (a) AC-005's per-arm fingerprint of working tree vs
  `git show 295690b:…` (`branches_changed_vs_base: []`), which I independently re-derived with my own
  normalizer (§2) and whose detection power I demonstrated by mutation (§5); (b) `marker_baseline_
  reproduced` still re-yields the 76/51/32 split from the pinned legacy table. The honest limit: this
  proves *source-level* identity of the seven arm bodies plus the covered-marker projection; the runtime
  file itself is not compiled on Linux (R2). Given the `break` analysis in §2 and that no arm body
  changed, source identity is sufficient here.
- **Smallest vertical change** — 168 insertions / 8 deletions across 3 product files + README; pure
  append to `TMXMapLoader.swift` (`@@ -350,3 +350,95 @@`); no new service/DB/queue/framework; **no new
  dependency**; `git diff --name-only HEAD -- Exolon.xcodeproj/` is empty (0) — correctly, since no new
  `.swift` file was introduced; `Exolon/Resources` is blob-identical so no content was authored to
  dissolve the P1-12 pairs (FORBID-001 holds, `resource_files_base == working == 282`,
  `new_image_literals: []`).
- **Rollback coherence** — `rollback.md`'s "one step: `git revert <merge>`, coverage probes must go RED"
  is not a guess, and I verified it as an experiment: reverting the three product files in a scratch
  copy while keeping the evidence produced `WAVE_C_PROBES_FAIL | failed=3
  (ignored_types_disposition, marker_coverage_all_maps, safe_models_are_labeled)` with AC-005 correctly
  **green** (a revert restores base equality, so AC-005 *must* pass). That is exactly the documented
  expectation. "Data recovery" is trivially sound because resources are proven identical at every gate.
- **P1-12 ruling honesty** — unusually good: `ruling.decision` says "a ruling, not a sourced fact",
  `not_sourced` admits no primary states intentionality, and `pair_notes['L03S09/L04S11']` discloses
  that the stage-2→5 premise **does not reach** the 24th pair and explicitly refuses to claim "no
  unique data was lost" there. `level_pair_manifest_pinned` *enforces* the presence of that disclosure,
  so the caveat cannot be quietly dropped later. README repeats the distinction rather than flattening
  it. Both issues stay OPEN pending owner acceptance.
- **README before push** — updated with current counts and contract links. Note the generic
  architecture-link clause is inapplicable: this repo has no `architecture/` tree and README references
  none. `decisions.md` carries a lesson entry; `mistakes.md` does not exist in this repo (nothing to
  record is being omitted).
- Arithmetic in README re-derived independently: 127 = 51 safe-model + 26 no-op/write-only
  (`blinker` 19 + `topdown_electro` 2 + `stage_end` 5) + 50 gameplay (`beam_` 20 + `beacon_base` 13 +
  `control_beacon` 13 + `changing_room` 4). **Correct**, and "resolved is not implemented" is stated in
  the same breath.
- `evidence/__pycache__/*.pyc` is gitignored (`.gitignore:12`) and `git add -A --dry-run` stages no
  stray artifact.

---

## Findings (none blocking)

**F1 — Suggestion, worth fixing in this PR: the safe-model overlay rect is anchored 2 cells below the
footprint the same comment says it measured, and its comparison to `beaconBase` is arithmetically
false.** `TMXLevelRuntime.swift:462-464` states the box is "converted to pixels the same way
beaconBase converts its own … anchored so its top edge sits at the marker's source row". With
row→y = `pixelHeight - (row+1)*16` (`TMXTileMapRenderer.swift:139`):
- `beaconBase` (`:398-403`) `y = H-(sourceY+3)*16`, height 48 → covers source rows `sy … sy+2` — the true
  measured footprint (§1).
- `appendSafeModelMarker` (`:475`) `y = bottomY - height` where `bottomY = H - sy*16 - 32` → covers rows
  `sy+2 … sy+4`.
So the reason-labelled debug box sits **32 pt lower**, overlapping the scenery's bottom row and two
cells of the terrain beneath it. Impact is confined to the opt-in debug overlay (no physics/damage/
score/spawn consumer), so it is not a gameplay defect — but this change's whole thesis is that the
overlay is the *measurement instrument* that proves content was recorded and not dropped, and an
instrument that outlines the wrong cells on the 32 affected maps undercuts that. Fix: anchor like its
siblings' source-row truth, `y: max(0, map.pixelHeight - (sourceY + CGFloat(cells.height)) * 16)`, or
correct the comment to say the box hangs 2 cells below the marker row.
Failure scenario: debug overlay on a mushroom map outlines empty terrain two rows below the mushroom.

**F2 — Note (author-disclosed, correctly): `unmatchedSourceMarkers` has no consumer at all.** The
in-code comment at `TMXLevelRuntime.swift:49` says it is read "only by the coverage meter"; the meter
only greps for the append (`wave_c_check.py:708`) and its executed probe computes its own unmatched set
without instantiating `TMXLevelRuntime`. I confirmed tree-wide that no Swift, script or test reads the
array. `tasks.md` **R3** and `analysis-architect.md:98-103` already state this precisely, so it is a
disclosed residual, not a hidden one — but the comment at `:49` overstates observability and should say
"recorded for a future debug-HUD; enforced today by the meter". Enforcement today is real: AC-001 turns
red on any unclaimed value, including one injected into the corpus.

**F3 — Nice to have (meter precision): the case-arm span for the *last* arm bleeds into `case nil:`.**
`branch_body` (`wave_c_check.py:349-351`) stops a switch-form body at `case \.` / `default:` / a
brace-only line, and `case nil:` matches none of those — so `.unconfirmedAction`'s fingerprint includes
the nil arm's text. Harmless today (no legacy arm is last, and `safe_models_are_labeled` only *contains*
-checks that the bleed cannot satisfy on its own), but if arms are ever reordered so a legacy arm lands
last, AC-005 would compare a base `if` body against a bled switch body and could mask a deletion inside
the nil arm. Add `case\s+nil\b` to the stop pattern.

**F4 — Nice to have: `evidence/README.md` is still the 3-line factory stub** while the package now
carries a 1872-line meter, a machine-checked disposition table, a pinned manifest and four run logs.
The index that tells the next reader what to run and which file is the oracle is missing; today that
knowledge lives in the meter's docstring.

**F5 — Observation: `rollback.md` trigger 3 overstates blast radius.** "a shipped-map visual regression
attributable to newly-rendered safe models (32 maps)" is largely unreachable — safe models create no
sprite or texture and render only behind `guard showHitboxes` (§4), so no non-debug visual can change.
Keep the trigger if it means the overlay, but say so, so a future rollback isn't argued from an
impossible symptom.

---

## Summary (6 lines)

1. **PASS, nothing to block on.** All six briefed areas check out against the actual diff and
   surrounding code, and the two claims I refused to take on faith — order preservation and
   exhaustive-switch-as-compile-error — were re-proven independently (0/11 values match two matchers;
   `swiftc -typecheck` gives "switch must be exhaustive" when an arm is dropped).
2. The seven legacy arms are body-identical to `git show 295690b` (my own normalized diff), and the
   base↔new `break` re-binding is a provable no-op because the outer case body ends at the chain — the
   76-marker stability claim is genuinely proven, in AC-005's per-arm fingerprints plus the golden data
   digest, not merely asserted.
3. `wave_c_check.py` is honest: 9/9 green reproduced live, **52/52 named controls true** (45 `controls`
   + 7 `tamper_controls`), base side read from Git blobs, product classifier compiled *and executed* with
   a negative control — and I reddened it myself with four mutations in arms other than `beam_` plus
   removal of the nil recorder.
4. `TMXSafeModelMarker`/label/footprint are internally consistent and the three footprint numbers are
   exactly reproducible from the shipped Collision layer (mushroom 4x3 9/9, waggon 5x3 21/24 with the
   10/15 merges, gunMachine 4-wide 18/18) — only the safe-model rect **anchor** is off (F1).
5. `level-content-v1.json` self-check digest recomputes, and the AC-005 re-baseline protocol is
   fail-closed and provably narrow (exact-digest + named authorizer, stale deviation→error, wildcard
   rejected, recorded 4-step simulation); `rollback.md` was verified as an experiment — reverting the
   product files reddens exactly the three coverage/label probes and correctly leaves AC-005 green.
6. Five non-blocking findings, F1 being the one I would fix here (the debug overlay outlines the safe
   models 32 pt below their real cells while the change's thesis is that the overlay is the proof of
   recorded content); macOS type-check of `TMXLevelRuntime.swift`/`GameScene.swift` (author's R2) is the
   one thing still owed before the merge is declared complete.
