# Tasks — wave C (write owner: `general_implementer`)

Status: **all nine tasks done**; tree `/home/pall/projects/.exolon-wave-c/exolon` @ route base
`295690b`, no git commit/stage/push (controller owns git). Meter green: `RESULT:
ALL_WAVE_C_PROBES_PASS | probes=9 failed=0`, rc=0, **2.46 s** (≤ 120 s, stdlib only).

1. [x] **Locate the level factory + characterization before edits** →
      [`evidence/analysis-repo_explorer.md`](evidence/analysis-repo_explorer.md) written first, with a
      file:line map: the matcher is `TMXLevelRuntime.swift:351-414` (`case "source_marker":` at 351,
      seven `source.contains` tests at 356/361/366/369/371/380/394, chain **closing without an `else`
      at 407** = the real silent-drop path; `default:` at 409 is a different, object-*name* path),
      loader `TMXMapLoader.swift:305-343` (decoding semantics reused), `LEVEL_COMPILER_AUDIT.md` =
      stage-1 ASM input (exclusion evidence only), Linux contour
      `20260919-…-7db1f3/evidence/harness/run.sh`.
2. [x] **RED baseline meter** → [`evidence/wave_c_check.py`](evidence/wave_c_check.py)
      `::marker_coverage_all_maps` measured **76/127 covered, 51 lost on 32 maps, 8 of 11 distinct
      values claimed**; full output kept in
      [`evidence/baseline-meter-red.txt`](evidence/baseline-meter-red.txt) (rc=1, product Swift
      untouched at that point).
3. [x] **Three marker families + safe model + silent drop deleted** → new
      `TMXSourceMarkerKind` classifier and `TMXSafeModelMarker` record appended to
      `TMXMapLoader.swift` (existing harness file, so the Linux contour compiles the product truth);
      `mushroom`/`waggon` → `.inertScenery`, `gunMachine_BOTTOM` → `.unconfirmedAction`; the runtime
      chain became an **exhaustive `switch` with no `default:`** and a `case nil:` that appends to
      `unmatchedSourceMarkers`, so a new unhandled family is a compile error and an unmatched marker
      is an observable record the meter fails on.
4. [x] **GREEN 127/127 marker *objects* (11/11 distinct `sourceBlock` values) + disposition table +
      digest check** → `marker_coverage_all_maps`
      127/127 and 11/11 distinct; committed table
      [`evidence/marker-disposition-v1.json`](evidence/marker-disposition-v1.json) (all 11 families,
      per-family basis, counts, map lists, footprints) rendered by one command into
      [`evidence/marker-coverage.md`](evidence/marker-coverage.md) including the per-map table of all
      51 formerly-dropped markers on 32 maps; `unchanged_marker_output` compares against the golden
      pre-change digest `545e281f470c0900…` (`evidence/baseline-prechange-digest.json`) → identical,
      and all 7 legacy branch *fingerprints* (mutations, nodes, textures, CGRect geometry) unchanged.
5. [x] **Runtime registration — none required; see Deviations D1.** No new `.swift` file and no
      pbxproj edit: no new *rendering* type was needed because the safe model is a recorded entity
      drawn with existing `SKShapeNode` debug geometry, not a sprite. The only scene touch is the
      existing hitbox debug overlay (`GameScene.swift` +12 lines) so a safe model is identifiable in
      debug rendering (FORBID-002). No texture literal added — `no_invented_content` proves the
      image-literal set is unchanged.
6. [x] **Digest manifest + pin test + negative controls** →
      [`engineering/contracts/level-content-v1.json`](../../contracts/level-content-v1.json):
      125 maps, `unique_count: 101`, 24 declared pairs (23×L02/L05 + L03S09/L04S11), 4
      `background_identical` pairs, per-map `zone_index`, canonicalization `wave-c-canonical-1`
      documented in-file, `self_check.body_sha256` = `13b3f1f2dd314863…` (keyed binding; see D15).
      `level_pair_manifest_pinned` green with 5 real flips; `manifest_selfcheck` rejects 6 distinct
      tampers while accepting the honest body.
7. [x] **Content spec + README** →
      [`engineering/reports/level-content-uniqueness-v1.md`](../../reports/level-content-uniqueness-v1.md)
      (uniqueness model 101/24, all 24 pairs with zone numbers and backdrop files, the 4
      fully-identical pairs, the 0-based formula and its false-mismatch trap, regeneration
      commands); `README.md` gained a "Level content contract" section pointing at both.
8. [x] **Spec names, stdlib, timing, parse gates, gate** → all nine spec-named functions exist in
      `wave_c_check.py` (nothing else is named there); stdlib only; 2.46 s. `swiftc -frontend -parse`
      rc=0 for `TMXMapLoader.swift`, `TMXLevelRuntime.swift`, `GameScene.swift` — and the parse loop
      is now executed **by the meter itself** (`safe_models_are_labeled::swift_parse`, with
      `parse_gate_detects_a_broken_file` proving it can fail), not just reported in prose.
      The committed Linux harness `run.sh` **no longer compiles on the merged tree** (D21): B moved
      the collision query into `TMXMapLoader.swift`, which now references `GameConstants`, so the
      contour fails at `error: cannot find 'GameConstants' in scope`. Up to wave B it reported
      **`REAL MAPS ok=125/125 failures=0`** with its 1-import-line delta rule and no-shim control.
      **Attribution, precisely (test review F4):** `run.sh` *compiles* the classifier (it now lives in
      `TMXMapLoader.swift`, so it is genuinely type-checked — a real gain over `-frontend -parse`) and
      *executes the parser*; it never calls `classify` (`grep -c classify harness/main.swift` = 0).
      Classifier **execution** is `wave_c_check.py::swift_product_evidence`, which is where the
      executed 127/127 and `unmatched: {}` numbers come from — that contour was extended in this
      cycle to compile `GameConstants.swift` too, so it runs on the merged tree (D21).
      `ruff check .` and `bandit -c bandit.yaml -r .` clean.
      `python3 scripts/grok_verify.py --mode pr` recorded at the end (see `verification` receipt).
9. [x] **This file updated.** Git operations in the rebase cycle (per controller instruction):
   `git fetch`, `git rebase origin/main` (conflict resolved), one local commit of the post-rebase
   fixes, and **no push**. See the rebase-cycle section.

## Gate state at hand-off

`python3 evidence/wave_c_check.py`: **9/9 probes PASS, rc=0, ~4.3 s** (120 s budget; the extra ~1.3 s is the parse gate now covering 19 committed+working Swift files), with **64 named controls, all
true** (per-probe table regenerated in `evidence/green-meter-run.txt`; the count is re-measured from
`--json` output, never copied from a previous revision — it was 52 before the test review (48 of those honest) and the delta re-review
measured 59; the Rb-1 guard made it 60, and the N2 anchor-parity controls in D27 make it **64**). Product execution active: `product_executed: true`, `loaded 125/125`,
`unmatched: {}`, no-shim negative control true. Stdlib-only verified by AST import scan.

Gate evidence for this revision: the reviewer's F1/C10/C11 and R2 cases are **external** mutation runs
against the committed artifacts in isolated `/tmp` copies (pristine meta-control green first):
`evidence/f1-tamper-proof.txt`, `evidence/f2-f3-rendering-and-typecheck.txt`,
`evidence/bypass-closure-proof.txt`. The RED baseline was regenerated by the committed checker against
a verified byte-exact base tree (`evidence/baseline-meter-red.txt`, checker sha256 recorded in the
file). `ruff check .` and `bandit -c bandit.yaml -r .` clean; harness `REAL MAPS ok=125/125`.

Preflight `python3 scripts/grok_verify.py --mode pr --no-record` before this cycle:
**`RESULT: PASS | profiles=base`** (git-diff-check 4/4, change-spec 1 spec, contract-structure 1
contract, secret-scan, ruff, bandit, factory-unit, factory-postgres-exit, source-stability). The
**recorded** receipt is stale by design: the meter, contract and docs changed again during the fix
cycle, and route receipts are fingerprint-bound. Per controller protocol the final recorded gate and
the `verification` receipt are taken after `AUDIT-DONE`; `code_review`/`test_review` receipts belong
to the review agents. Earlier recorded runs that failed only on `source-stability` were caused by
audit agents writing into this package while the gate ran — expected noise, not a defect.

## Per-finding proof lines

- **P1-7 (issue #11)** — was: 76/127 markers resolve, 51 (`blk_waggon` 24, `blk_gunMachine_BOTTOM`
  18, `blk_mushroom` 9) vanish on 32 maps with no signal. Now: `marker_coverage_all_maps` =
  **127/127, 11/11 distinct, 0 lost maps, `silent_drop_path_removed: true`**, and the compiled product
  classifier itself reports `unmatched: {}` over 125/125 loaded maps
  (`evidence/green-meter-run.txt`, `evidence/marker-coverage.md` §Product execution).
- **P1-12 (issue #16)** — closed **by ruling**: stage 5 is the original game's recolored stage 2, so
  the 24 pairs are intentional content and are pinned by `level-content-v1.json`;
  `level_pair_manifest_pinned` proves the audited numbers reproduce (101 unique of 125, exactly the
  23+1 pairs, 4 pairs identical down to backdrop bytes: `zone_028≡103`, `zone_040≡115`,
  `zone_046≡121`, `zone_047≡122`).
- **FORBID-001** — `no_invented_content`: 282 files in `Exolon/Resources` are **blob-identical** to
  base `295690b` (0 invented, 0 rewritten, 0 deleted), uniqueness is still 101, the identical-pair set
  is still exactly the audited 24, and no new image/texture literal exists.
- **FORBID-002** — `safe_models_are_labeled`: the product returns a non-empty `safeModelLabel` for
  exactly the two safe-model kinds, the label reaches the `TMXSafeModelMarker` record, the record is
  surfaced by name in the debug overlay, and an unlabeled substitution fails the probe (control
  `unlabeled_placeholder_rejected`).
- **AC-005** — golden digest `545e281f470c0900…` recorded before the edit equals the digest after it,
  for all 76 covered markers on 37 maps, plus unchanged branch fingerprints for all seven substrings.
- **INV-001** — `zone_index_formula`: 117/117 maps with `zoneNumber` satisfy the 0-based formula, the
  8 keyless maps are exactly `L01S01…L01S08`, manifest `zone_index` agrees for all 125, and the naive
  1-based/naive-filename readings are required to produce 117 false mismatches (so the check is real).

## Deviations

- **D1 — task 5 runtime registration narrowed, on purpose.** No new Swift *object* type was added
  because no new object renders or interacts: all three families are already drawn by the baked
  `Original Static Scenery` image layer and already solid in the `Collision` layer (measured 51/51 on
  solid cells, all 32 maps carrying a full-frame image layer). Adding sprites would need new texture
  names, which is blocked twice over: `v3_measurements.py:331-337` fails any texture literal absent
  from `Exolon/Resources`, and it would double-draw over shipped art. Consequence: **zero pbxproj
  edits** (the wave-A 4-edit rule never triggers, since no new file landed) and the only scene change
  is debug-overlay rendering. `swiftc -frontend -parse` is the gate for that scene file because
  SpriteKit cannot be type-checked on this Linux host — see Residual risk R2.
- **D2 — `blk_gunMachine_BOTTOM` is a labeled safe model, not a gun.** Inventing the missing behaviour
  would violate the brief's own evidence: type 11 has 56 instances in the original but only 18 are
  exported with a BOTTOM marker, and the other 38 sit in 18 maps that have no BOTTOM marker at all.
  Its kind is therefore `.unconfirmedAction` with the reason in the label, and the separate
  "acquire `data_zone_data.asm` type-11" work stays out of scope (as the merged analysis ordered).
  Scope correction in **D26**: the mechanic itself is documented in-tree; only the numeric
  type-11 -> entity binding is missing.
- **D3 — one fixture in the pin probe mutates an in-memory copy, not a file on disk.** The synthetic
  divergent fixture is built by adding an object / changing one tile value in an `ElementTree` copy of
  `L05S03`, so no fixture file can ever be mistaken for shipped content under FORBID-001. It still
  flips both the digest and the pin assertion (`extra_object_flips_digest`,
  `changed_tile_flips_digest`, `divergent_fixture_flips_pin`).
- **D4 — the four hand-copied matcher mirrors are NOT collapsed in this change.** The merged analysis
  recommends collapsing them and amending the v3 report in the same change. Doing that here would edit
  another change package's committed evidence (`v3_measurements.py`, `linux_static_audit.py`, which
  also rewrites its own package's artifacts in place when run) — out of this route's scope and
  explicitly warned against. What this change does instead: `wave_c_check.py` parses the product
  source and never copies the literals, so the new gate cannot go stale the way those four can. The
  staleness of `v3_measurements.py` (`EXPECTED` still says read 76 / lost 51) is recorded as
  Residual risk R1.
- **D5 — `changed=11` on the first gate run included the change package itself**, which is expected
  paperwork, not product drift; `source-stability` reported the fingerprint remained stable.
- **D6 — `analysis-repo_explorer.md` records the meter's own count `blinker maps = 11`** (the merged
  §1 census lists 19 markers; distinct maps is 11, not 17 as an early draft of my table said). The
  disposition table and `ignored_types_disposition` now agree with the corpus on every row.
- **D7 — independent audit cross-check (`evidence/audit-repo_explorer.md`, controller-routed filename to
  avoid clobbering task 1's characterization).** It confirms, with its own implementation: 127/127 is
  real per-family handling and not a catch-all; the silent-ignore chain is deleted from source, not just
  unreached; **all 125 manifest digests reproduce byte-exactly**; `Exolon/Resources` unmodified vs
  `295690b`. Accepted items now closed: coverage doc re-synced to the meter, GREEN transcript committed
  (`evidence/green-meter-run.txt`), `requirements.md` filled.
- **D8 — the audit's AC-001/INV-001 wording nit is correct and adopted.** The zone formula is *verified*
  on the 117 maps that carry `zoneNumber`; for the other 8 (`L01S01…L01S08`) only the derived `zone_index`
  exists, and they are honestly null for the raw property. `change-spec.yaml` has since been amended by the
  controller (disposition-normative AC-001; INV-001 derived-for-125 / property-on-117, canonicalization
  version bound document-wide via `self_check.body_sha256`) and was **not** edited by me; `requirements.md`,
  the spec report and the README now match that amended text, and `zone_index_formula` +
  `manifest_selfcheck` check both halves.
- **D9 — the audit's caveat "resolved ≠ behaviour implemented" is now printed by the meter itself**, at
  the end of `marker-coverage.md`, and in `README.md` and `test-plan.md`, so the 127/127 headline cannot
  be misread as full original fidelity (50 live / 51 safe models / 21 no-op / 5 write-only).
- **D10 — design-judgment audit (`evidence/analysis-architect.md`) findings fixed in the meter.** Two real
  defects, both mine, both now closed with mutation-proof:
  (a) *the relabelling bypass* — flipping a committed `safe-model` row to `typed` with an empty label kept
  every probe green, which made FORBID-002's "identifiable in the meter output" a false statement. Fixed
  by enforcing the biconditional `disposition == safe-model ⟺ product isSafeModel(kind) ⟺ label present`
  over **all** rows in both `marker_coverage_all_maps` and `safe_models_are_labeled`; the auditor's exact
  repro now reddens those two probes (`evidence/bypass-closure-proof.txt`).
  (b) *the truncated rect capture* — `branch_fingerprint` matched `CGRect\(([^)]*)\)`, so it stopped
  inside `max(0, …)` and could not see `height: 272 → 999`, `width: 48 → 120`, or an added statement.
  Replaced with balanced-paren capture plus `numeric_literals`, and the decorative
  `branch_edit_detected` (`… is not None`) was replaced by four real controls: height edit, width edit,
  statement added, and a comment-only edit that must still be ignored.
  (c) *self-confirming golden* — AC-005's pre-change side is now derived from
  `git show 295690b:TMXLevelRuntime.swift` rather than only from a golden this tool wrote; the golden
  records the same base-derived values and is cross-checked against the blob on every run.
- **D11 — citation currency (audit items 5/F6).** `marker-disposition-v1.json` no longer carries bare
  `TMXLevelRuntime.swift:NNN` prose ranges: each row has `citations.runtime_arm` / `citations.classifier_test`
  (verified against the **current** tree on every run, with `stale_citation_rejected` and
  `out_of_range_citation_rejected` controls) and a separate `citations.route_base` naming `295690b`.
  `citation_policy.as_of` states explicitly that the working-tree ranges are not "as of a commit" because
  this change is uncommitted by design, and must be re-bound after any merge touching those files.
  `analysis-repo_explorer.md` gained an appendix mapping every route-base anchor to its post-edit line.
- **D12 — ruling language corrected everywhere in my files (citation audit F3/F9/F10/F11/F12/F1/F2/
  F4/F5/F7/F8).** Intentionality is now phrased as a ruling with its primaries named
  (`ORIGINAL_MECHANICS.md:166`, `exolon-full-audit-20260920-v3.md:37`, `level-graph.md:36`, and the ASM
  table's identical per-screen records for **23 of 24** pairs); `L03S09≡L04S11` is separated as a
  stage-3→stage-4 pair the premise does **not** reach, with its `solid=140` vs `solid=128` tension and the
  counterweight caveat (`solid=` matches 0/125 TMX screens) disclosed in the manifest `pair_notes` and the
  spec report; no closing doc claims the findings are closed (issues #11/#16 stay OPEN,
  `blocked-on-owner`); "127 `.tmx` tree-wide" corrected to **142** (125 + 17 fixtures) with a note that the
  merged file still carries the error; loader length 352, not 353; units aligned to the amended spec
  (24 duplicate **groups** = 24 pairs = 48 maps; 127 marker **objects** vs 11 distinct values);
  "identical method" downgraded to "reconstructed and proved equal **by output**"; the `L01S01 -> 000`
  example moved out of the "carries the property" sentence. `change-spec.yaml` was **not** edited (the
  controller's), and the docs now match its amended AC-001/INV-001/FORBID-001 wording.
- **D13 — the 24th-pair claim was checked, not copied.** Re-measured from `LEVEL_COMPILER_AUDIT.md`:
  `solid=`+action list identical for exactly 23 of 24 pairs, `L03S09` 140 vs `L04S11` 128 with both action
  lists empty; independently, both shipped maps have 64 nonzero `Collision` cells; and `solid=` equals the
  TMX collision count on **0 of 125** screens (6 within ±5). The manifest therefore asserts the premise
  for 23 pairs and records the discrepancy without converting it into either "no loss" or "data loss".

## Integration order — **A → B → C** (recorded for the reviewer; no code action now)

The first integration ruling from the design-judgment audit was A → C → B; the controller **reversed it to
A → B → C** after wave-B's architect produced the decisive evidence: wave C's classifier rewrite lands on
the *same* `beam_`/force-field arm that wave B semantically rewrites, whoever rebases last must adopt the
other's initializer under the type checker, and only wave B's meters understand pool semantics. So wave C
rebases last, onto a main that already contains B.

Consequences for this branch, and what was prepared for them:

1. **One conflict is expected**, at the `TMXLevelRuntime.swift` beam/`forceField` area. Resolve toward
   wave B's pool API **inside** the exhaustive switch — keep `case .forceField:`, keep `case nil:`
   recording `unmatchedSourceMarkers`, and keep **no `default:`**, since the missing-default property is
   what makes an unhandled family a compile error.
2. **AC-005 must be re-baselined for exactly one arm.** `unchanged_marker_output` reads its pre-change
   side from `git show <base>:TMXLevelRuntime.swift`, so after the rebase the `beam_` arm legitimately
   stops matching `295690b` while the other six must stay byte-identical. The meter now carries a
   narrow, fail-closed mechanism for that: `arm_deviations` + `deviation_ruling` in
   `evidence/baseline-prechange-digest.json`, populated by `--record-baseline --base <ref>`.
   Protocol and the executed verification:
   [`evidence/ac005-rebase-protocol.txt`](evidence/ac005-rebase-protocol.txt).
3. **Nothing was pre-excused.** `arm_deviations` is committed **empty** and the four
   `deviation_*` controls assert that a deviation cannot be a wildcard, cannot be uncited, cannot target
   the wrong digest, and is reported stale if the arm did not actually move. The end-to-end simulation
   (temporarily editing `height: 272 → 273`, then restoring byte-exactly) confirmed the probe reddens on
   the drift itself before any excuse exists.
4. No action until the controller's integration instruction after A and B merge; the close-out gate still
   waits for `AUDIT-DONE`.

- **D14 — merge-order change recorded.** This supersedes the A → C → B note in
  `evidence/analysis-architect.md` §5 (that section reasoned from the earlier order; its *technical*
  finding — one conflict in the beam area, and a re-baseline obligation for wave C's golden — is exactly
  what survives the reversal, which is why the mechanism above was built rather than re-litigated).

- **D15 — test review F1 (BLOCKING) closed: the contract self-check was value-blind.**
  `manifest_selfcheck` called `validate_manifest(manifest)` **without** `corpus_hashes`, so the
  corpus branch was dead inside the probe (it only ran in the generator); `maps[*].background` was
  only tested for emptiness and `maps[*].background_sha256` was never compared at all; and
  `body_sha256` was an unkeyed, recomputable digest, so the non-structural tamper controls only
  proved "the checksum moved". The reviewer's cases **C10/C11** (claim a foreign backdrop file /
  fabricate a backdrop digest) passed all nine probes with rc=0. Now: `validate_manifest` re-derives
  every data claim from the live tree (per-map canonical digest, backdrop name, backdrop bytes via
  the renderer's basename resolution, layer count, and hash-equality of each declared pair), the
  digest is keyed with an embedded binding, and every tamper control **re-seals before being judged**
  — so they test content, not checksum drift. Verified externally in an isolated copy, including
  **K10/K11/K12 re-sealed with the real key** (a forger who read the checker): all red.
  [`evidence/f1-tamper-proof.txt`](evidence/f1-tamper-proof.txt).
  Honest limit recorded in the probe output as `binding_limit` and in
  [`evidence/level-content-v1-binding-note.md`](evidence/level-content-v1-binding-note.md):
  a keyed digest in a public repo is a construction barrier, not a cryptographic one — it does **not**
  protect prose fields, and no doc may claim it does. AC-004's divergent-fixture half also moved
  *into* the probe AC-004 names (`declare_nonidentical_pair_rejected`), fixing the traceability gap.
- **D16 — test review F6: four decorative controls removed or made load-bearing.**
  `synthetic_unclaimed_detected` was true even when the product claimed nothing → now a
  sensitivity **and** precision pair (`unclaimed_values` helper). `new_texture_literal_detected`
  was a constant-true set identity → now `new_literals(before, now ∪ {x})` must yield exactly `{x}`
  **and** the honest comparison must yield `set()`. `honest_table_accepted` and
  `zero_based_formula_holds` were literal `not problems` restatements → deleted; the latter replaced
  by `formula_distinguishes_base_zero_from_base_one`, which fails on a mis-transcribed formula.
  Also replaced `uniqueness_shift_detected` (`unique != 125`) with a counting check that forcing one
  digest to be novel must raise uniqueness by exactly one. A source scan now finds **0** controls
  written as `= not problems` and no `x or not x` tautologies. Census at that revision: **59 named
  controls, all true** (64 after the N2 anchor-parity controls in D27) (per-probe table in `evidence/green-meter-run.txt`); the count is re-measured per run, never
  restated from memory.
- **D17 — test review F2/F3: the debug-rendering clause is now covered, and the type-check ceiling is
  measured instead of asserted.** Deleting the whole `GameScene` safe-model overlay loop used to leave
  every probe green (case R2) while FORBID-002 claims "identifiable in debug rendering". Added
  `overlay_binding_problems` (pure over the real source: loop consumes `currentLevel.safeModelMarkers`,
  draws `marker.rect` via `addDebugRect(`, passes `marker.label` through `label:`, helper still
  accepts it) with three controls; R2 now reddens `safe_models_are_labeled`. `swiftc -frontend -parse`
  was prose in five documents and wired into nothing — it is now executed by the meter over all three
  changed files, with a self-test that a deliberately broken file is rejected. F3 was attempted and
  cannot be closed here: `swiftc -typecheck` fails at `import SpriteKit`, and type-checking against a
  SpriteKit stub I wrote would only prove agreement with my own stub. **Verified and disclosed:** a
  *type* error (`forceFields.append(field.thisIsNotAMember)`) still passes all nine probes; so does
  `LevelObstacles.swift hitPoints = 25 → 1` (case R3), because AC-005 is a source-text golden, not an
  executed-output golden. Both statements are in `test-plan.md` §"Residuals the net cannot close".
- **D18 — test review F5/F7 wording.** R1 tightened from "cannot detect this fix" to what it actually
  does: the mirrors still **run green and publish pre-fix numbers about the post-fix tree** (`rc=0`,
  all their own controls OK), and the meter now reports the divergence loudly on every run
  (`stale_mirror_report` → `WARNING … v3_measurements.py still reports 76/127 … owner-route cleanup
  owed`) without editing another route's committed evidence. `baseline-meter-red.txt` was regenerated
  by the **committed** checker against a verified byte-exact base tree (`git checkout 295690b --
  Exolon/`, empty diff), so artifact and checker agree control-for-control; the 62-vs-64 control delta
  between the red and green runs is explained in the artifact itself (at base the meter's Swift probe
  program does not compile, so it refuses to publish an unexecuted product number; the two absent
  controls are the executed-product ones).

## Rebase cycle onto `3407c37` (waves A and B merged) — what happened, measured

- **D19 — the rebase itself.** `git fetch --all --prune` then `git rebase origin/main`.
  **Two** conflicts, not the forecast one: the foreseen
  `TMXLevelRuntime.swift` `source_marker`/`forceField` hunk, plus **`README.md`** (both wave A's
  "Structured gameplay event log" section and wave C's "Level content contract" section were
  appended at the same place — a pure both-added conflict, resolved by keeping both).
  Resolution of the Swift hunk followed `ac005-rebase-protocol.txt`: **my** exhaustive switch
  structure kept, **B's** beam semantics adopted inside the arm (`let box = …` +
  `beamBoxes.append(box)`), B's post-loop `TMXBeamGrouping.groups(for:)` + `BeamFieldModel` pool
  block untouched. Post-merge invariants verified: 0 conflict markers, 9 arms + `case nil:`,
  `unmatchedSourceMarkers.append` intact, the only `default:` left is the pre-existing outer
  object-**name** one at `:488`, `swiftc -frontend -parse` rc=0. Result `ed687a0`.
- **D20 — the re-baseline was executed and the deviation hatch turned out NOT to be needed.**
  `--record-baseline --base 3407c37` (the base this branch now replaces). `unchanged_marker_output`
  then reports `branches_changed_vs_base: []`, `deviations_honored: []`, `compared_against:
  "3407c37 (TMXLevelRuntime.swift)"`, and `arm_deviations` stays **empty**. The forecast single
  deviation did not materialise because the conflict resolution adopted B's arm body *verbatim*:
  the beam arm's fingerprint (`beamBoxes.append`, one `CGRect`, literals 0/240/272/48) is identical
  to the new base's. Recording a deviation the data does not show would have been exactly the
  self-confirming artefact the audits have been hunting, so none was written. The hatch remains
  armed and tested: 4 `deviation_*` controls plus the earlier end-to-end proof.
- **D21 — wave B's loader change broke two Linux contours, mine and the committed harness.**
  B moved the shared collision-surface query **into** `TMXMapLoader.swift`, which now references
  `GameConstants`; the file no longer compiles standalone. Consequences, both measured:
  (a) the committed harness `…/20260919-…-7db1f3/evidence/harness/run.sh` now **fails** (rc=1) at
  `error: cannot find 'GameConstants' in scope`, so its documented `REAL MAPS ok=125/125` is not
  reproducible on the merged tree — a one-line fix on their side (add
  `Exolon/GameCore/GameConstants.swift` to the build at `run.sh:51`); **not edited here**, it is
  another package's committed evidence and the break is wave B's, not mine;
  (b) my own `swift_product_evidence` broke the same way, so I extended it to compile
  `GameConstants.swift` alongside the loader — copied **byte-verified unmodified** (the copy is
  compared to the product file and the probe refuses on mismatch), keeping the loader's
  one-import-line delta rule and the no-shim negative control. Executed result on the merged tree:
  `loaded 125/125`, `unmatched: {}`, `product_negative_control_holds: true`.
- **D22 — Rb-1: the parse gate now covers committed history, not just the working diff.**
  `swift_targets()` = `git diff --name-only 295690b..HEAD -- *.swift` ∪ working diff ∪ untracked,
  which post-rebase yields **19 files** including A's `Diagnostics/*` and B's
  `BlasterBullet`/`TMXTileMapRenderer`/`Grenade`/`LevelObstacles` — none of which a
  working-diff-only scan would ever see again. New control
  `parse_gate_covers_committed_changes` reddens if the gate ever shrinks back to the working diff,
  and the verdict map is now keyed by **repository-relative path** because this tree has two
  different `main.swift` files that were silently overwriting each other's verdict under the old
  basename key. Independently: applying B's own FORBID-001 added-line patterns to the merged
  A+B+C product diff gives **0 violations** over 2826 added code lines.
  End-to-end proof (committed garbage in `BlasterBullet.swift`, working tree clean: OLD scan = 0 files
  and fully green, NEW scan = 19 files and exactly `safe_models_are_labeled` reddens naming the file):
  [`evidence/rb1-committed-garbage-proof.txt`](evidence/rb1-committed-garbage-proof.txt), which also
  records a caveat so nobody misreads an earlier run — on the same scratch tree the **pre-fix** checker
  failed 4 probes for unrelated reasons (stale citations + the broken contour), not for the garbage.
- **D23 — cross-route findings from running wave B's meter as my interference check.**
  `wave_b_check.py` on this branch: **every semantic probe PASSes** (125/125 geometry equivalence
  incl. 1437 rects base==new==executed, beams 10 fields × 25 HP = 250, spawn 119/125, pistons 46/46
  lethal, cull bounds, single surface query, zone formula) — my merge broke none of B's assertions.
  One probe fails, `no_magic_offsets`, and it is a **diff-scope artifact, not a code conflict**:
  their `wave_base()` is `merge-base(HEAD, origin/main)`, which while B was a live branch resolved
  to A's tip `17a742a` (correct: their own changes), but now that B is merged into `main` it resolves
  to `3407c37`, so their scan sees only wave C's 3 files / 95 code lines and trips their own
  "scan strangely empty" sanity threshold (`n_files>=7 and n_code>=150`). Reproduced in a
  **standalone clone** with `origin/main` pointed at `17a742a`: same meter, same tree → `added-lines:
  332 стронок кода в 9 изменённых продуктовых файлах`, **`ALL_WAVE_B_CHECKS_MATCH_SPEC`, rc=0**.
  So their green transcript is intact and my lines are inside their scan scope and clean; the
  durable fix is theirs (pin the scan to their own PR range, e.g. `17a742a..a4bc23f`, instead of a
  `merge-base` with a moving `origin/main`). Reported, not edited.
- **D24 — a self-inflicted hazard during this cycle, detected and repaired.** Reproducing B's green
  state first used `cp -a` of this **worktree**, whose `.git` is a *pointer* into
  `/home/pall/projects/exolon/.git/worktrees/exolon2`; a `git branch -f origin/main 17a742a` run
  there therefore wrote into the **shared** repository, creating a local branch literally named
  `origin/main` that shadowed the remote (making `git rev-parse origin/main` answer `17a742a`, which
  would have poisoned any later base computation, including my own `swift_targets` and the
  controller's merge). Detected by checking refs immediately after; repaired with
  `git update-ref -d refs/heads/origin/main` and verified: only `refs/remotes/origin/main = 3407c37`
  remains, `git status -sb` shows the expected tracking line, index clean (`git diff --cached`
  empty), `git diff HEAD -- Exolon/` empty. All later isolation work used
  `git clone --no-hardlinks` (independent refs), and the scratch copies were deleted.



- **D25 — what was deliberately NOT re-pointed.** The contract keeps
  `generated_from_commit: 295690b` and therefore `self_check.body_sha256 = 13b3f1f2dd314863…`.
  Verified reason: `git diff --name-only 295690b..origin/main -- Exolon/Resources` is **empty**, so the
  125 pinned digests, the 24 pairs and the 4 backdrop-identical flags describe exactly the same bytes
  at both commits; rebinding the field would churn the contract body, invalidate the digest value that
  the code reviewer independently recomputed and cited, and buy nothing. `no_invented_content`
  correspondingly still anchors its blob comparison at `295690b` — and it is that comparison, not the
  date field, that carries FORBID-001. AC-005's base is a separate matter and **was** re-pointed to
  `3407c37` (D20), because there the pre-change text really did move.

## Micro-batch (post-rebase verifier PASS) — N1/N2/N3

- **D26 — N1: a shipped claim was false and is now scoped correctly.** The `.unconfirmedAction`
  `safeModelLabel` (and the enum/arm comments, the disposition row and §2 of the characterization)
  asserted the gun-machine type "is not identifiable in-tree". `ORIGINAL_MECHANICS.md:36-41` documents
  the mechanic in-repo — bullet origin `turret.left + 2` / `turret.bottom + 56`, bullets travel left
  and are blaster-immune, the turret is grenade-destroyable for 150 points — and `:170` lists gun
  machines as required; the docs-researcher audit had already marked that VERIFIED. What is genuinely
  absent is only the **numeric type-11 → entity binding** for the *separate lower* cell (56 type-11
  actions in the original table, 18 exported alongside a BOTTOM marker, the other 38 in maps with none).
  The disposition is unchanged — recorded safe model, behaviour deliberately not implemented and **not
  armed** (arming is out of scope). The label literal is pinned against the committed table by
  `safe_models_are_labeled`, and the table row was rewritten from the Swift literal itself so the two
  cannot disagree; the executed product evidence still supplies the string, so the
  `unlabeled_placeholder_rejected` / `bogus_substring_rejected` flips remain live.
- **D27 — N2: the safe-model box sat 32 pt low while its comment claimed beaconBase parity.**
  `appendSafeModelMarker` anchored `max(0, bottomY - height)`, and since
  `bottomY = pixelHeight - syTop - 32`, the box covered source rows `sy+2 .. sy+4` — two rows under the
  marker — on all 32 affected maps, while `.beaconBase` (the cited equivalence:
  `pixelHeight - (sourceY + 3)*16`, `height: 48`) covers `sy .. sy+2`. Fixed to the truth the comment
  promised: callers now pass `topY: map.pixelHeight - syTop`, so `rect.maxY == pixelHeight - sourceY*16`
  exactly matches the beacon arm. This is debug-overlay geometry only — no collision, damage, score or
  spawn path reads `safeModelMarkers`, so AC-005 and the 76 covered markers are unaffected (verified:
  `branches_changed_vs_base` still empty). To stop prose and code drifting again, the meter now
  re-derives both top edges arithmetically from the source text and requires them to agree
  (`safe_model_anchor_problems`), with four controls — `anchor_parity_honest_accepted`,
  `anchor_regressed_to_bottomY_detected`, `anchor_single_row_shift_detected`,
  `anchor_beacon_side_shift_detected`. `anchor_parity_broken` deliberately counts only parity verdicts
  and refuses to treat a parse failure as a detection, because a control that "fires" when it cannot
  read the source asserts nothing.
- **D28 — N3 recorded, not acted on.** Wave B's `wave_b_check.py` will exit rc=1 on **any** later
  rebased branch, by design of its own `wave_base()` (`merge-base(HEAD, origin/main)`): once wave B is
  merged, that resolves to a base whose diff against HEAD no longer contains wave B's changes, so its
  `no_magic_offsets` sanity threshold (`n_files>=7 and n_code>=150`) cannot be met. All of B's semantic
  probes still pass on this tree, and their green transcript reproduces once the base is restored.
  Re-anchoring that scan is **wave E's scope**, not wave C's; noted here so a later verifier reading a
  red `no_magic_offsets` on a rebased branch does not mistake it for wave C interference.

## Residual risks

- **R1** — `v3_measurements.py` (committed evidence of package `20260919-…-7db1f3`) does **not** merely
  fail to notice this fix: **run on the fixed tree it still exits 0 with every one of its own controls
  `OK`, publishing numbers that are now false about this tree** — `markers_read = 76`,
  `markers_lost = 51`, `markers_lost_maps = 32`, `markers_lost_kinds = {waggon 24, gunMachine_BOTTOM 18,
  mushroom 9}` — because `v3_measurements.py:89` hard-codes `HANDLED = (...)`, a hand-copied mirror it
  never re-reads from Swift. `linux_static_audit.py:47-55` carries the same mirror. Post-fix truth is
  127/0/0. **Will misreport post-fix; owner-route cleanup owed.** Not edited here: it is another
  change package's committed evidence (and `linux_static_audit.py` rewrites its own package's artifacts
  in place when run). What this change did instead: `wave_c_check.py` parses the product source rather
  than copying literals, and every run now prints
  `WARNING … v3_measurements.py still reports 76/127 (rc=0) … owner-route cleanup owed, see tasks.md R1`
  (`stale_mirror_report`), so the two meters cannot disagree silently — while the pinned legacy table is
  still checked **equal** to the mirror tuple, because that tuple is what the audited baseline means.
- **R1a — PR-deviations line (for the pull request body, per test review F5):** *"The audit's own
  committed oracle `v3_measurements.py` still reports the pre-fix marker split (76/51) with `rc=0` on
  this branch's tree, because it mirrors the matcher as a hard-coded tuple instead of reading Swift.
  Wave C does not fix it (different package's evidence); wave C's meter detects the divergence and
  prints it as a WARNING on every run. Cleanup belongs to the audit route and should also amend the
  v3 report prose (§1 line 32 / §6 line 129), which the merged analysis already prescribes."*
- **R2** — **2 of the 3 changed Swift files are not type-checked on this host, measured (test review
  F3):** `swiftc -typecheck Exolon/GameCore/Levels/TMXLevelRuntime.swift` fails at
  `error: no such module 'SpriteKit'` (`:1:8`), and the only Linux contour in the tree is the
  CoreGraphics type-rename shim. Both files are now syntax-gated **by the meter** (not just by prose)
  over all three touched files, with `parse_gate_detects_a_broken_file` proving that gate can fail;
  `TMXMapLoader.swift`, which owns the classifier, is compiled **and executed**. Verified non-result:
  injecting a *type* error (`forceFields.append(field.thisIsNotAMember)`) leaves all 9 probes green.
  Closing this needs the macOS build: `addDebugRect(_:color:alpha:label:)`,
  `currentLevel.safeModelMarkers` and the exhaustive `switch` must be confirmed by `xcodebuild`
  (test-plan E2E). A hand-written SpriteKit stub was rejected as false assurance — the delta test
  review endorses that refusal ("a stub would type-check the scene against fiction").
  **Sequencing note:** the delta reviewer's merge condition ("`xcodebuild` must run and be recorded
  before merge, else F3 is must-fix") has since been **overruled by the owner's constraint** — no
  macOS hardware or Developer ID exists, so the condition is structurally unsatisfiable. `release.md`
  records the re-rule and F3 stands as an **accepted permanent residual**; the compensating controls
  on record are the executed parse gate over all 19 committed+working Swift files (D22), the
  overlay-consumer source assertions (D23/F2), and the compiled+executed contour for the file that
  owns this change's logic (D21).
- **R2b** — **AC-005 cannot see a collaborator's own behaviour change (test review F4).** It pins the
  marker records and each branch's *source text* (mutations, nodes, textures, balanced-paren `CGRect`
  geometry, numeric literals). Verified non-result: `LevelObstacles.swift` `var hitPoints = 25 → 1`
  leaves all 9 probes green (case R3). That file is untouched by this diff, but the AC-005 wording
  "byte-identical factory output" must be read as *this file's* branch output, not as "gameplay is
  unchanged". The controller owns the spec wording; the docs now say so explicitly.
- **R3** — `unmatchedSourceMarkers` is now recorded but nothing in the shipped game surfaces it at
  runtime; the enforcement point is this meter (and any future content import that adds a new
  `sourceBlock`). If runtime visibility is wanted, it belongs with the debug-HUD work, not here.
- **R5 (owner action, cross-route)** — the committed Linux harness
  `engineering/changes/20260919-…-7db1f3/evidence/harness/run.sh` **does not compile on the merged
  tree** since wave B moved the collision query into `TMXMapLoader.swift` (now references
  `GameConstants`): rc=1, `error: cannot find 'GameConstants' in scope`. Its documented
  `REAL MAPS ok=125/125` is therefore not reproducible by anyone re-running it. One-line fix in that
  package: add `"$ROOT/Exolon/GameCore/GameConstants.swift"` to the build at `run.sh:51`. Deliberately
  not done here (another route's committed evidence; the break is not wave C's). Wave C's own contour
  is fixed and does run on the merged tree (D21).
- **R6 (owner action, cross-route)** — wave B's `wave_b_check.py::no_magic_offsets` fails on any
  branch after their own merge, because its base is `merge-base(HEAD, origin/main)`: post-merge that
  yields wave C's diff (3 files / 95 lines) and trips their `n_files>=7 and n_code>=150` sanity
  threshold. All their semantic probes pass, and their green state reproduces when the base is
  restored (D23). Suggested durable fix: pin the added-lines scan to their own PR range rather than a
  moving `origin/main`.
- **R4** — The manifest is bound to `generated_from_commit: 295690b`. If the owner authorizes
  regenerating any of the 48 duplicated maps, the manifest must be regenerated in that same change
  (`--write-manifest` refuses if the pair set stops matching the pinned ruling).
