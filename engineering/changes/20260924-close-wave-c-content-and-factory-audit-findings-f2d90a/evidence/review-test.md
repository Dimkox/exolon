# Test review — change f2d90a (wave C content + factory audit findings)

- Reviewer: `test_reviewer` (read-only), route `f2d90a858699`, base `295690b7fc72`, tree
  `/home/pall/projects/.exolon-wave-c/exolon`.
- Date: 2026-09-24. Scope: the **test story only** (spec↔probe fidelity, contradictory controls,
  harness, baseline artifacts, per-map coverage, net gaps). Product architecture, docs and diff
  quality are out of scope for this report.
- No tracked file was touched. Every mutation ran in a private `/tmp/mut/<id>` copy
  (`shutil.copytree`, `.git` gitdir pointer resolves to `/home/pall/projects/exolon/.git/worktrees/exolon2`,
  so `git show 295690b:…` still works inside the copies). `git status` before and after this review
  is identical (4 `M`, 3 `??`).

## Verdict

**FAIL on the test story as scoped — one blocking finding (F1), which is a ~4-line fix.**
Everything else is either genuinely strong or already disclosed. The meter is not decorative: 9/9
probes exist and are green in 2.6 s, product execution is real, the baseline artifact reproduces
exactly, and 11 of the 12 controls I flipped independently did redden. F1 is blocking because
AC-004's own wording makes an unflippable control fatal, and I found a tamper of a committed
contract artifact that no probe in the net can see.

| # | Question | Answer |
| --- | --- | --- |
| 1 | Spec id → named probe exists and asserts | 8/8 ids, 9/9 symbols resolve (AST-checked); AC-004 does not deliver its claim; AC-001 mislabels its own quantity |
| 2 | Independent flips of 5/52 controls | 12 flips run; 11 reddened, **1 class does not** (F1) |
| 3 | `harness/run.sh` executed / no-shim intact | Ran it: rc=0, `REAL MAPS ok=125/125 failures=0`, no-shim control intact. **It never calls `classify`** — release.md:21 mis-attributes |
| 4 | `baseline-meter-red.txt` vs `git show` base | Reproduced: same 3 FAIL / 6 PASS, rc=1, same 76/51/32/127, same `data_digest`. Control lists predate the committed checker |
| 5 | Per-map coverage of the 3 families / 32 maps | **Enumerated**, in 3 consistent forms; my independent recount matches all 32 rows, 51 markers, zone column, 0 disagreements |
| 6 | Gaps | F1 (contract value tamper), F2 (in-diff `GameScene.swift` = 0 coverage), F3 (type error green), F4 (AC-005 text-local), F5 (stale v3 mirror runs green), F6/F7 minors |

---

## 1. Spec id → probe fidelity

All 8 criteria (`AC-001..005`, `INV-001`, `FORBID-001..002`) name `evidence/wave_c_check.py::<symbol>`.
Every path exists and every symbol resolves to a real `FunctionDef` (AST check), and all 9 are in
`PROBES` (`wave_c_check.py:1526-1536`). `python3 evidence/wave_c_check.py` on the working tree:
`RESULT: ALL_WAVE_C_PROBES_PASS | probes=9 failed=0`, rc=0, **2.6 s**, stdlib-only → SIG-001 met.

| id | probe | asserts the criterion? |
| --- | --- | --- |
| AC-001 | `marker_coverage_all_maps` | **Yes, strongly.** Claims are derived from the product (`loader_claims`/`runtime_chain`, :696 and :344-348), a synthetic unclaimed value is checked, the silent-ignore path is probed three ways (:708-711), and the coverage number is *executed*: `swift_product_evidence()` compiles the loader and runs `TMXSourceMarkerKind.classify` over all 125 maps (:435-514). If the Swift contour cannot run, the probe **appends a problem instead of passing** (:768) — that is the right default. Normative disposition column is enforced as an equivalence (:777, :632-655). |
| AC-001 | `marker_baseline_reproduced` | **Yes.** Re-measures the corpus with the pinned 7-substring legacy table and requires 76/51/32/11 + per-family counts, with real sensitivity (`drop_beam_raises_lost_to_71`, `drop_all_loses_everything`, `narrower_table_cannot_lose_less`). |
| AC-002 | `ignored_types_disposition` | **Yes.** Table↔corpus↔product triangle: count, maps, `maps_list`, substring-in-claims, kind-in-enum, 22 machine-re-read `file:line` citations (:896-916), and executed `kind_for`/`counts` per row (:919-935). Verified by my C1/C2/C3 flips. |
| AC-003 | `level_pair_manifest_pinned` | **Yes, strongest probe.** 125 digests vs corpus, 24 declared pairs actually hash-equal, *undeclared* collisions rejected, unique==101, `background_identical` re-derived from resolved PNG bytes (:1037-1040), `pair_notes`/`ruling` disclosure enforced. |
| **AC-004** | `manifest_selfcheck` | **No — not as written.** See F1. |
| AC-005 | `unchanged_marker_output` | **Yes for the claim it makes.** The pre-change side is read from `git show 295690b:TMXLevelRuntime.swift` (:590-604), so it cannot be talked into agreeing by editing a golden; the golden is itself cross-checked against the blob (:1210-1212); the re-baseline hatch is exact-transition + citation only (:620-630). See F4 for what "factory output" does **not** cover. |
| INV-001 | `zone_index_formula` | **Yes** for the formula (117 present / 8 honest-null, both directions pinned, naive 1-based and filename readings must false-positive). Its second half — "bound transitively … through the **recomputable** `self_check.body_sha256`" — is the weak link F1 exploits: a recomputable unkeyed digest is an accident guard, not a tamper guard. |
| FORBID-001 | `no_invented_content` | **Yes.** Blob-identity against the base tree via `git ls-tree` + `hash-object` (:1285-1295), uniqueness and the identical-pair set must not move, and no new image/texture literal vs base (base literals re-read from blobs, :380-400). Verified by my D1/D2 flips. |
| FORBID-002 | `safe_models_are_labeled` | **Partly.** The meter-visible half and the product-source half are enforced and executed (:1398-1418, my E2/G1/G2 flips). The clause "identifiable **in debug rendering**" has no executable evidence at all — see F2. |

## 2. Independent contradiction controls (12 flips, all in `/tmp/mut/`)

Method: copy the tree, mutate **committed artifacts**, run the **named** probe (and, for the
gap probes, all 9). A pristine copy of the unmutated tree was run first as the meta-control:
`pristine-green` → `ALL_WAVE_C_PROBES_PASS`, rc=0 — so any red below is caused by the mutation.

| id | mutation (independent of the meter's own self-tests) | named control | result |
| --- | --- | --- | --- |
| C1 | `marker-disposition-v1.json`: `blk_mushroom.count` +1 | `bogus_count_rejected` | **RED** — `table count 10 != corpus 9` + product disagreement |
| C2 | same table: `blk_waggon.kind` → `zzNotDeclaredAnywhere` | `bogus_kind_rejected` | **RED** |
| C3 | same table: `blk_waggon.maps_list` last entry → `L01S01` | (problem check) | **RED** — `maps_list disagrees with the corpus` |
| C4 | `TMXLevelRuntime.swift`: legacy `beam_` arm `height: 272` → `288` | `branch_rect_height_edit_detected` | **RED** — `branch output for 'beam_' changed vs the base and no authorized deviation covers it` |
| C5 | runtime: rename `case .stageEnd:` → `.stageEndZZZ:` | — | **RED** on 2 probes (`ignored_types_disposition`, `unchanged_marker_output`) |
| C6 | committed `L02S03.tmx`: `zoneNumber 027` → `028` | `zero_based_formula_holds` | **RED** — `zoneNumber 28 != (stage-1)*25+(scene-1) = 27` |
| **C7** | manifest: flip `maps[L01S01].sha256` **and recompute `body_sha256`** | `flip_one_map_digest_rejected` | `manifest_selfcheck` **STAYS GREEN**; only `level_pair_manifest_pinned` reddens → **F1** |
| C8 | manifest: swap `maps[L01S01].background` + recompute | `swap_background_file_rejected` | RED, but *only* because my tamper coincided with the probe's own (it edits `sorted(maps)[0]` too) — `schema_errors` was **empty**. Control is idempotency-fragile → **F1** |
| C9 | manifest: drop one declared pair + recompute | `drop_one_pair_rejected` | **RED** (structural `identical_pairs must hold 24` survives rehash) |
| D1 | new literal `SKTexture(imageNamed: "zz_invented")` in `GameScene.swift` | `new_texture_literal_detected` | **RED** via the *problem* check, not the control (see F6) |
| D2 | copy `L01S01.tmx` → `L01S99.tmx` in `Exolon/Resources` | `invented_file_detected` | **RED** — `1 resource files invented` + pair set moved |
| E1 | runtime: rename every `unmatchedSourceMarkers.append` → `silentlyDropped.append` | `missing_recorder_flips_probe` | **RED** — `an unmatched marker is still dropped without a signal` |
| E2 | loader: replace the `SAFE-MODEL inert-scenery…` literal | `unlabeled_placeholder_rejected` | **RED** on `safe_models_are_labeled` |
| G1 | table: `blk_waggon` disposition `safe-model`→`typed`, label emptied | `safe_relabelled_as_typed_reddens_coverage` | **RED** on 2 probes — independently reproduces `bypass-closure-proof.txt` |
| G2 | table: promote documented no-op `blk_blinker` to `safe-model` | `typed_promoted_to_safe_rejected` | **RED** on 2 probes |

Task asked for 5; 12+ were run because a single class did not flip. Note the honest self-tests in
the meter are *in-process proxies* (they feed doctored text to pure functions); every row above
instead edits the committed artifact and re-runs the probe, which is the stronger form — and it is
where C7/C8/C10/C11 diverge from what the in-process control reports.

## 3. `evidence/harness/run.sh` (package 7db1f3, unchanged by this diff)

`git diff 295690b -- …/20260919-…-7db1f3/` is empty — the change reuses the committed harness
rather than editing it (`tasks.md:14`, `rollback.md:25`), which is the right call. I ran it on this
tree, output to `/tmp/f2d90a-review/harness-run.txt` (**not** to the tracked `last-run.txt`):

- rc=**0**; step 5 prints `REAL MAPS ok=125/125 failures=0 []`; malformed fixtures behave as
  documented (`f08_csv_short`/`f09_b64_trunc`/`f11_enc_xml`/`f17_huge_dims` THREW, `f14_unclosed`/
  `f15_empty` OK) — matching the committed `last-run.txt` byte-for-byte on the aggregate line.
- **no-shim negative control intact**: step 6 aborts if the build *succeeds* (`run.sh:58-62`) and
  printed `OK: без стаба не собирается (… no such module 'CoreGraphics')`. The gate is fail-closed
  (`exit 1`), macOS-refusal (`exit 75`) and the exactly-one-import-line delta check (`exit 65`)
  are all present and were exercised by the successful run.
- **But the classifier is not executed by `run.sh`.** `grep -c classify harness/main.swift` = **0**.
  `main.swift` only calls `TMXMapLoader.load` and dumps geometry. So `release.md:21`'s
  "REAL MAPS 125/125 failures=0 (classifier executed, not merely parsed)" mis-attributes: `run.sh`
  *compiles* the classifier (it now lives in `TMXMapLoader.swift`, so it is genuinely type-checked —
  a real gain over `-frontend -parse`) and *executes* the parser. Classifier **execution** is
  `wave_c_check.py::swift_product_evidence` (:435-514), which I verified independently: green run
  reports `product_executed: true`, `loaded` 125/125, `unmatched {}`, and its own no-shim control
  `product_negative_control_holds: true`. The claim is true of the net, false of the harness.

## 4. Baseline artifacts vs `git show 295690b`

`evidence/baseline-meter-red.txt` is **consistent with the base tree** — I reproduced it rather
than trusting it: fresh copy + `git checkout 295690b -- Exolon/` (verified identical to base) +
the *current* checker →

- same verdict: `RESULT: WAVE_C_PROBES_FAIL | probes=9 failed=3
  ignored_types_disposition,marker_coverage_all_maps,safe_models_are_labeled`, rc=1 (artifact's
  own `rc=1` line matches); the same 6 probes PASS;
- same numbers: `markers_total 127`, `markers_covered 76`, `markers_lost 51`, `lost_maps 32`,
  `distinct_source_blocks 11`, `lost_kinds {waggon 24, gunMachine_BOTTOM 18, mushroom 9}`,
  `claimed_by_matcher` = the 7 legacy substrings, `classifier_kinds []`,
  `silent_drop_path_removed false`, `resource_files_base 282`;
- `data_digest == golden_digest == 545e281f…` at base **and** in the green run → AC-005's record
  half is genuinely unchanged pre/post (independently, base loader = 352 lines with 0 hits for
  `TMXSourceMarkerKind|unmatchedSourceMarkers`, base runtime = 7-branch `source.contains(` chain
  at lines 356-394; `baseline-prechange-digest.json.base_commit` = the route base,
  `arm_deviations: []` → AC-005 is fail-closed today).
- **Provenance caveat (F7):** the artifact was generated by an earlier checker revision. Its
  `unchanged_marker_output` lists 4 controls incl. the since-removed `branch_edit_detected` (today
  there are 11, `bypass-closure-proof.txt` §"Also closed" documents the replacement), and it shows
  no citation-staleness lines where my base re-run reports 22 (`check_citation` gained corpus
  re-reading later). Headline numbers match; byte-equality of the detail blocks does not.

## 5. Per-map coverage of the 3 families on the 32 affected maps

**Enumerated, not aggregated** — and verified twice over:

1. `marker-disposition-v1.json` carries `maps_list` per family (14 waggon + 15 gunMachine_BOTTOM +
   6 mushroom; union 32) plus `zones`/`footprint_cells`; `ignored_types_disposition` re-derives
   each row's map set from the corpus and rejects disagreement (:866-869) — proven by C3.
2. `marker-coverage.md` "The 51 formerly-dropped markers, per map" is a **32-row table** (map, zone,
   kinds × counts, marker total).
3. My own recount (independent of the meter — direct TMX walk with the 7 legacy substrings) gives
   `markers=127, formerly_lost=51, maps_with_loss=32`; the markdown map set equals the recount set,
   `maps_list` union equals it too, **0 of 32 rows disagree** on count, kind set or zone column, and
   the marker column sums to 51.

Residual: nothing re-validates `marker-coverage.md` itself (it is `--write-dispositions` output; the
probes read the JSON, not the markdown). A hand-edit of the table would not be caught. Low risk,
since the JSON it derives from is checked.

## 6. Gaps — what regression can ship through this net

### F1 — BLOCKING. AC-004's named probe is bypassable at value level; a tampered committed contract passes all 9 probes

`engineering/contracts/level-content-v1.json` is this change's **contract artifact**
(`change-spec.yaml` `contracts.json_schema`) and it stores per-map `sha256`, `background` and
`background_sha256`. AC-004 requires "a tampered manifest declaration fails the manifest self-check;
absence of any flip is itself a failure."

- `manifest_selfcheck` calls `validate_manifest(manifest)` **without** `corpus_hashes`
  (`wave_c_check.py:1145`), so the corpus-comparison branch at `:1128-1134` is dead in the probe —
  it only runs inside the *generator* (`:1680`).
- `validate_manifest` never checks `maps[*].background` against reality (`:1111-1113` only tests
  emptiness) and **never checks `maps[*].background_sha256` at all** (`background_digests()` at
  `:202-213` computes exactly the needed value and is used only for the 24 pairs' boolean).
- `self_check.body_sha256` is an **unkeyed, recomputable** sha over the body (`:1136-1138`,
  `INV-001` says "recomputable" out loud; `self_check.regenerate_with` documents the command).
  So the only thing the 6 non-structural tamper controls actually test is "did the checksum move".

Proven by three runs (each: mutate the committed contract in a `/tmp` copy, recompute
`body_sha256`, run the whole net):

| id | tamper | `manifest_selfcheck` | whole net |
| --- | --- | --- | --- |
| C7 | `maps[L01S01].sha256` flipped | **PASS** | RED only via `level_pair_manifest_pinned` |
| C8 | `maps[L01S01].background` → `zone_999_original.png` | RED *by coincidence* (`schema_errors` empty; the probe's own `t5` targets the same field) | 1 probe |
| **C10** | `maps[L02S16].background` → `zone_999_original.png` | — | **`ALL_WAVE_C_PROBES_PASS`, rc=0** |
| **C11** | `maps[L02S16].background_sha256` → `abab…` (fabricated) | — | **`ALL_WAVE_C_PROBES_PASS`, rc=0** |

C10/C11 are the shipping case: the pinned contract can assert a backdrop file and a 64-hex digest
that the maps do not have, and the entire 9-probe net — including the probe whose stated purpose is
tamper evidence — stays green. AC-004 by its own words is then unsatisfied.

Fix (small, no new dependency): in `manifest_selfcheck`, pass the corpus
(`validate_manifest(manifest, canonical_hashes())`, the parameter already exists) and add per-map
`background == background_refs(root)[0]` / `background_sha256 == background_digests(root)[0]`
checks in `validate_manifest` — then C7/C8/C10/C11 all flip, and the 6 tamper controls stop
depending on the checksum alone. Also target the probe's own `t5`/`t1` at a map other than
`sorted(maps)[0]` so they cannot coincide with a real tamper.

### F2 — `GameScene.swift` is in the diff and outside the net entirely; FORBID-002's rendering clause is untested

`grep -n "GameScene\|SpriteKit\|SKScene" wave_c_check.py` → **0 hits**. The file is never opened by
any probe (`all_image_literals` at `:350-356` scans all of `Exolon/**/*.swift` but only for image
literals). Proof: **R2** — delete the entire `currentLevel.safeModelMarkers` overlay loop this change
added to `GameScene.swift` → **`ALL_WAVE_C_PROBES_PASS`, rc=0**.

FORBID-002's statement requires a safe model to be "identifiable in the meter output **and in debug
rendering**, never a silent visual drop". The meter enforces the first (label literal, executed
`is_safe`/`labels`, `appendSafeModelMarker` wiring, `TMXSafeModelMarker.label`) and nothing for the
second. This is *disclosed* — `test-plan.md:19-24` assigns it to a manual macOS hitbox-overlay spot
and `tasks.md:236-238` (R2) admits the file is syntax-gated only — so it is not a hidden defect. But the
criterion is stated as satisfied while one of its two clauses rests on an unperformed manual step,
and there is no executable artifact for it.

Aggravating factor: **`swiftc -frontend -parse` is not wired into any runnable gate.** It appears
only in prose (`test-plan.md:17`, `tasks.md:54,113,236`, `analysis-architect.md:123,273`,
`decisions.md:9`); `grep -rn "swiftc\|frontend -parse" scripts/` finds nothing in `grok_verify.py`.
I ran it myself for the record: rc=0 for all three touched files (`GameScene.swift`,
`TMXLevelRuntime.swift`, `TMXMapLoader.swift`) — so today's claim is true, but it is a hand-run
result with no reproducibility and no gate to keep it honest.

Fix: add the three-file `swiftc -frontend -parse` loop as a probe (or a `run.sh`-style sibling), and
either downgrade FORBID-002's wording to "meter + source label" until the macOS spot is performed, or
pin the rendering contract textually (assert `GameScene.swift` contains `safeModelMarkers` and the
labeled `addDebugRect(… label:` call site, which a probe already reading `Exolon/**/*.swift` could do
in 5 lines).

### F3 — a hard Swift type error in the file that owns this change's factory stays green

**R1** — `forceFields.append(field)` → `forceFields.append(field.thisIsNotAMember) …` in
`TMXLevelRuntime.swift` → **all 9 probes PASS** (and `-frontend -parse` would not catch it either:
parse is syntax-only). Only `TMXMapLoader.swift` is compiled; `TMXLevelRuntime.swift` is
regex-scanned (`source_marker_case`, `branch_body`, `balanced_block`) with no type awareness. The
same class of miss covers the new `TMXSafeModelMarker` construction sites. This is the accepted
Linux ceiling (`tasks.md:236-238`), but the test story should say plainly that **nothing on this host
type-checks 2 of the 3 changed Swift files** — the harness covers the third.

### F4 — AC-005's "byte-identical factory output" is a source-*text* golden, not an output golden

**R3** — `Exolon/GameCore/Objects/LevelObstacles.swift:766` `var hitPoints = 25` → `1` (a real
behaviour change for the 12 `blk_beam_down`/`blk_beam_up` force fields inside the 76 covered
markers) → **all 9 probes PASS**. `fingerprint_body` (`:572-588`) captures only what is *inside* the
branch body (`x.append`, `addChild`, `CGRect(…)`, `SKTexture(imageNamed:)`, integer literals), so
anything reached through a collaborator's own file is invisible, and `LevelObstacles.swift` is never
opened. AC-005's wording ("generate byte-identical factory output") therefore overstates what is
measured: it pins branch-body text + marker-record projection. Not a defect in *this* diff
(`LevelObstacles.swift` is untouched, and I confirmed the 4 files in the diff are the only changes),
but a hole in the "regression cannot ship" reading of AC-005.

### F5 — the stale v3 mirror does more than "cannot detect this fix": it still runs green and publishes the pre-fix numbers about the post-fix tree

`tasks.md:231-235` (R1) rates this as an audit-backlog item. Measured, it is worse:

```
$ python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py
markers_read            = 76        # post-fix truth: 127
markers_lost            = 51        # post-fix truth: 0
markers_lost_maps       = 32
markers_lost_kinds      = {'blk_waggon': 24, 'blk_gunMachine_BOTTOM': 18, 'blk_mushroom': 9}
controls:  OK  markers_probe_flips
```

`v3_measurements.py:89` hardcodes `HANDLED = ("beam_", "blinker", …)` — a hand-copied mirror of the
matcher it never re-reads — and exits **0** with all its own controls OK while asserting numbers that
are now false about the current tree. `evidence/linux_static_audit.py` in the same package carries
the same mirror. This is exactly the failure mode `wave_c_check.py`'s header (:32-36) cites as the
reason it parses the product instead of copying literals. Since the fix touches another package's
committed evidence, the *scope* call in tasks.md is defensible, but the net has no control that
would notice a stale mirror contradicting it, and the risk entry understates it. Minimum: add a
cross-check probe (or a one-line banner + `markers_read` recomputation) so the two meters cannot
disagree silently.

### F6 — three decorative controls and two wording/traceability defects (non-blocking)

These do not weaken the net (each is backed by a real problem check or another control that does
flip — I verified D1/E1/G1 externally), but three of the "52 named controls" cannot fail:

- `no_invented_content::new_texture_literal_detected` (`:1325-1326`) is a constant-True set
  identity: `(now ∪ {zz_control}) − before − (now − before)` = `{zz_control}` for **every**
  reachable state; it goes False only if the route base itself contained `zz_control`. The real
  teeth are the problem check at `:1313` (D1 proved it).
- `marker_coverage_all_maps::synthetic_unclaimed_detected` (`:731-733`) stays **True even if the
  product tested nothing** (I evaluated it with `claimed = []`) — it is insensitive to the exact
  failure it names.
- `safe_models_are_labeled::honest_table_accepted` (`:1462`) and
  `zone_index_formula::zero_based_formula_holds` (`:1517`) are `not problems` — literally `ok`'s own
  first term restated (the latter is even excluded from `ok` at :1519-1521), so neither adds
  sensitivity. A truthful "52 controls" census is therefore **48 load-bearing + 4 restatements**.
- AC-001 wording (`change-spec.yaml:5`): "127/127 **distinct** `source_marker` values" — 127 is
  marker *instances*; distinct `sourceBlock` **values are 11** (green run: `markers_total 127`,
  `distinct_source_blocks 11`, `dispositions_committed 11`). Both readings are asserted by the
  probe, so no test is missing, but the headline number is mislabelled in `change-spec.yaml:5`,
  `OBJ-001.success_metric`, `test-plan.md:7` and `tasks.md:27`. The JSON's own `totals.units`
  gets it right ("11 distinct values / 127 instances") — the prose did not follow it.
- AC-004 traceability: its evidence names `manifest_selfcheck` for the "synthetic map fixture that
  diverges from a declared-identical pair" half, but `divergent_fixture_flips_pin` and
  `new_collision_flips_pin` live in `level_pair_manifest_pinned` (`:1069-1074`). `manifest_selfcheck`
  contains no fixture assertion at all.

### F7 — provenance of `baseline-meter-red.txt`

See §4: numbers reproduce exactly, but the artifact predates the committed checker (4 vs 11
controls in one block, no citation-staleness lines). One sentence in the artifact header ("generated
by checker revision X; the generator has since gained `check_citation` and the balanced-paren rect
capture") would stop a reader from expecting byte-equality.

## What I did not verify

- Any macOS/SpriteKit behavior: `xcodebuild`, the hitbox overlay, the E2E "one map per newly-fixed
  type renders" step in `test-plan.md:16`. Unavailable on this host (and `run.sh:19-21` correctly
  refuses to run the Linux contour on Darwin).
- Whether the 32 affected maps *play* correctly with safe models — no probe claims that; the
  safe-model arrays are explicitly documented as not feeding physics/damage/score/spawn
  (`TMXLevelRuntime.swift:44-50`), and I confirmed `safeModelMarkers` has exactly one consumer
  (`GameScene.swift:1123`) — which is precisely the untested surface (F2).
- The GitHub-side trust gate (out of scope for a test review).

## Reproduction

```bash
cd /home/pall/projects/.exolon-wave-c/exolon/engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a
python3 evidence/wave_c_check.py                      # 9/9 PASS, 2.6 s
python3 evidence/wave_c_check.py --json | head -400   # control census (52 keys)
../20260919-*/evidence/harness/run.sh | tee /tmp/harness.txt   # 125/125, no-shim control
# mutation lab (all copies under /tmp/mut, tree untouched):
python3 /tmp/mut/drive.py pristine-green C1-disp-count C4-arm-rect C6-zone-tmx E1-drop-recorder D1-new-image-literal
python3 /tmp/mut/serial.py    # C5 C7 C8 C9 E2 R1 R2 R3 with full logs in /tmp/mut/ser-*.log
python3 /tmp/mut/c10.py       # contract background tamper  -> ALL GREEN (F1)
python3 /tmp/mut/c11.py       # contract background_sha256  -> ALL GREEN (F1)
python3 /tmp/mut/extra.py     # G1/G2 normative disposition column
python3 /tmp/mut/recount.py   # independent 32-map/51-marker recount
```

## Disposition for the orchestrator

- This report is the only file this review wrote (`evidence/review-test.md`); no tracked file was
  touched and the meter re-run after writing it still reports `ALL_WAVE_C_PROBES_PASS`.
- The `code_review` receipt is deliberately **not** recorded here (out of the read-only scope given
  to this reviewer). Suggested owner action, noting the verdict is **fail**:
  `python3 scripts/grok_review.py code_review --status fail --report engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/review-test.md`
- **Staleness warning:** adding this file changes the repository tree fingerprint, so the existing
  fingerprint-bound `verification` receipt (`.grok-stack/runtime/receipts/f2d90a858699/verification.json`,
  `tree_fingerprint 12b01911…`, `criterion_ids: ["AC-001"]`, changed-file count 29) is now stale
  against this tree. `python3 scripts/grok_verify.py --mode pr` must be re-run after the F1 fix
  lands, not before.
- Recommended order: fix F1 (4 lines, no dependency) → re-run the meter and add C7/C8/C10/C11-style
  corpus-bound controls → then decide whether F2's rendering clause is closed by the macOS spot or by
  wording. F5 belongs to the audit backlog but its risk entry should be re-worded per §6.
