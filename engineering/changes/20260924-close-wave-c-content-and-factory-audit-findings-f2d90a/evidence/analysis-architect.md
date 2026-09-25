# Architect audit — wave C in-flight (change f2d90a)

Read-only audit of the **working tree** at `/home/pall/projects/.exolon-wave-c/exolon`, branch
`codex/wave-c-content-factory-20260924`, route base `295690b`. No file in the tree was modified by
this audit (the one `evidence/__pycache__/` artifact my Python imports created was deleted).

**Tree fingerprint at citation time** (`git hash-object`, working tree, all uncommitted):

| File | blob |
| --- | --- |
| `Exolon/GameCore/Levels/TMXLevelRuntime.swift` | `fdf1293241195f7d12e71d915201d32e4d37f46c` |
| `Exolon/GameCore/Levels/TMXMapLoader.swift` | `f299fcf14f79dbf6165eff9a93e1b46126219acb` |
| `Exolon/GameCore/GameScene.swift` | `b42053f7f9acad3bacd1d0285b4e165cf0adf61d` |
| `engineering/contracts/level-content-v1.json` | `2b4fe408af254d882afe4f0397070df7c2e65142` |
| `evidence/wave_c_check.py` | `9d2527f834c30ba2f497c404052e0c0e9bd71454` |
| `evidence/marker-disposition-v1.json` | `be9946c3eaed35a2884a7a2c579f7b51d45d24b3` |
| `change-spec.yaml` | `7b864da69e763429003d320c33ff34c13a387a6c` |

**The tree moved while this audit ran.** `tasks.md` grew from 9 unchecked items to 137 lines with a
Deviations section, `TMXLevelRuntime.swift` gained a comment correction (56→57 insertions),
`change-spec.yaml` re-worded INV-001, and `analysis-docs_researcher.md` / `audit-repo_explorer.md` /
`green-meter-run.txt` appeared, all mid-session. Line citations below were re-taken after the last
observed write; anything cited may still be stale. Consequence for the gate: see §6.

Product diff is 4 files, +167/−8 (`GameScene.swift` +14, `TMXLevelRuntime.swift` +56/−7,
`TMXMapLoader.swift` +92, `README.md` +6). No new `.swift`, no `Exolon/Resources` change, no
`Exolon.xcodeproj` change.

## Verdicts

| # | Question | Verdict |
| --- | --- | --- |
| 1 | typed-vs-safe boundary enforceable? | **MINOR** — enforceable for *labeling*, not for the *choice*; one demonstrated false-green |
| 2 | runtime creep / pbxproj | **SOUND** |
| 3 | manifest canonicalization | **SOUND** (one MINOR binding-wording gap in INV-001) |
| 4 | unchanged-output guarantee for the 76 | **MINOR** — claim is true, the probe that guards it is partly decorative |
| 5 | rebase risk vs waves A/B | **MINOR for wave C, BLOCKING for integration order** — proven 1 conflict + guaranteed AC-005 red |

---

## 1. Typed vs safe: a rule, or author intent? — MINOR

**What is machine-enforced (stronger than usual, verified):**

- The table is product code, not prose: `enum TMXSourceMarkerKind` with `isSafeModel`
  (`TMXMapLoader.swift:364`, `:382`) and `safeModelLabel` (`:393`); `classify(sourceBlock:)` returns
  `nil` for nothing-matched (`:407`). The runtime switches over it **exhaustively with no `default:`**
  (`TMXLevelRuntime.swift:366`, arms `:418` `:427` `:435` `case nil:`), so a new enum case is a
  compile error until the runtime handles it. That is a real, non-bypassable rule.
- The meter does not trust its own regex: `swift_product_evidence()` (`wave_c_check.py:444`) copies
  the loader to a temp dir with the harness's one-line `import FoundationXML` delta, compiles and
  **runs** `classify` over all 125 maps, and *requires* the build without the CoreGraphics shim to
  fail (`:468`, control `negative_control_build_fails`). Probes consume `evidence['is_safe']`,
  `['kind_for']`, `['labels']` from that execution (`:1136-1157`).
- Cross-checks that do hold: safe row ⇒ non-empty label equal to the product literal (`:1105-1108`);
  typed kind carrying a label is a failure (`:1156`, "hides the distinction"); every product-safe
  kind must have a non-empty product label (`:1151-1155`); a corpus family with no committed row
  fails AC-002 (`missing`, `:699-701`); the matcher must keep an `unmatchedSourceMarkers.append`
  path or AC-001 goes red (`:570-572`).
- I ran the meter on the current tree: **9/9 PASS, `product_executed=true`, 2.49 s** (SIG-001 ≤120 s).

**Where the boundary is still author intent.** AC-001 says each marker "resolves to a typed factory
object or an explicitly labeled safe model". Neither half is what the meter proves. It proves the
matcher *claims* the substring. `marker-coverage.md` (committed) shows 21 of the 127 are `no-op`
(`blk_blinker` 19, `blk_topdown_electro` 2 → `break`, footprint `0x0`) and 5 are `write-only`
(`blk_stage_end` → `stageExitMarkers`, read nowhere). 127/127 is green with 26 markers that produce
no entity. The package is honest about this (legend in `marker-disposition-v1.json`, analysis §2
"127 = 50 live + 26 no-op/write-only + 51 dropped"), but the AC wording overstates, and nothing
stops a future family being routed to a `break` arm and counted as resolved.

**Demonstrated false-green (the direct answer to "can someone add a marker as safe silently?").**
I took the committed table, changed `blk_waggon` (24 markers — the largest formerly-lost family) from
`disposition: "safe-model", label: "SAFE-MODEL inert-scenery…"` to `disposition: "typed", label: ""`,
left everything else alone, and re-ran the three guards against that table in memory:

```
safe_models_are_labeled : True      ignored_types_disposition: True      marker_coverage_all_maps : True
```

`evidence/is_safe[kind]` is consumed only for rows already declared `safe-model`
(`wave_c_check.py:1091`, `:1148`); there is no `disposition ⟺ is_safe` equivalence check, and
`safe_model_families`/`markers_covered_by_safe_models` in the output are derived from that same
tamperable field. So a contributor cannot add a safe model *invisibly* (the product label, the debug
node and the table row are forced), but they **can** declare one as `typed` and FORBID-002's
"identifiable in the meter output" becomes a false statement. One-line fix in either probe:

```python
if (row['disposition'] == 'safe-model') != bool(evidence['is_safe'].get(row['kind'])):
    problems.append('%s: disposition %r contradicts the product isSafeModel=%r'
                    % (block, row['disposition'], evidence['is_safe'].get(row['kind'])))
```

Also worth recording: `classifier_labels()` (`:280-293`) captures only the **first** identifier of a
comma-list `case` arm, so `product_labels` in the meter output lists just
`forceField/inertScenery/unconfirmedAction`; the executed evidence covers all nine kinds, so this
only degrades the source-parse fallback, not the green run.

**Runtime observability nit.** `unmatchedSourceMarkers` (`TMXLevelRuntime.swift:51`, append `:438`)
is read by nothing in the product — the comment at `:49` says "only by the coverage meter", which is
true only in the sense that the meter greps for the append. The class of defect P1-7 was (a drop
invisible to everything) is closed for *shipped* maps because the meter enumerates the corpus; a map
that never goes through the meter would still drop silently with no log. Acceptable for a green-tier
change, worth a line in the change package.

## 2. Runtime creep — SOUND

- New types: exactly one enum (`TMXMapLoader.swift:364-435`, 9 cases + `isSafeModel` + label +
  `classify` + `safeModelFootprintCells`) and one value struct (`:438-444`). Plus one private helper
  (`TMXLevelRuntime.swift:466-478`) and two stored properties (`:50-51`). No service, no registry, no
  protocol hierarchy, no subsystem: the runtime half is 56 added lines, 13 of which are comments.
- Placement is deliberate and load-bearing: the classifier lives in `TMXMapLoader.swift` because that
  is the only `.swift` on the Linux contour (analysis §4, harness rule "exactly one added import
  line"), which is what makes the executed proof possible. Documented at
  `analysis-repo_explorer.md:169` (§6 pbxproj bullet) and §8.3.
- No gameplay reach: `safeModelMarkers` has exactly one consumer,
  `GameScene.swift:1123`, inside the hitbox debug overlay; `debugOverlay.removeAllChildren()` at
  `GameScene.swift:1076` precedes it, so the up-to-51 extra nodes per level do not accumulate.
  `grep -rn safeModelMarkers Exolon/` returns that one call site plus declarations/comments.
  `sourceHazards` (the kill-player array, `GameScene.swift:575`) is untouched — the disposition
  table lists routing into it as forbidden.
- `addDebugRect` gained a defaulted `label: String = ""` (`GameScene.swift:1129`) written to
  `node.name`; nothing enumerates `debugOverlay` children by name, so no behavioral change for the
  other 12 call sites. `swiftc -frontend -parse` rc=0 for all three touched files (re-run here).
- **pbxproj 4-edit rule: respected by avoidance.** `git diff --name-only -- Exolon.xcodeproj/` is
  empty; `git status -uall -- Exolon/` shows three ` M` files and no new file; 18 `.swift` on disk
  vs 18 `lastKnownFileType = sourcecode.swift` entries — registration is 18/18 unchanged. The rule
  itself is recorded (wave A, cited in `tasks.md:11` of wave A and `analysis-repo_explorer.md:169`),
  and `tasks.md:35` (D1) states the reason no rendering type was needed. Nothing to audit in the
  pbxproj — that is the correct outcome.
- FORBID-002's "never a silent **visual** drop" rests on the claim that the 51 cells are already
  drawn by the baked scenery. I checked independently: all **32** affected maps carry exactly one
  `imagelayer` (`Original Static Scenery`) whose `zone_NNN_original.png` resolves on disk — zero
  exceptions. So no hole opens in normal play, and `no_invented_content` proves no new
  image/texture literal exists (282/282 resource blobs identical to `295690b`,
  `new_image_literals: []`).

## 3. Manifest canonicalization — SOUND (one MINOR wording gap)

- **Version tag: present** — `canonicalization_version: "wave-c-canonical-1"` plus a structured
  `canonicalization` block (`id`, `includes`, `excludes`, `serialization`, `authority`), checked at
  `wave_c_check.py:832` and rejected on swap by the tamper control `version_swap_rejected`.
- **Separation is exactly the merged audit's.** Merged authority
  `20260919-…-7db1f3/evidence/perfile/level-graph.md:154-159` gives 96 (tiles) / 96 (Collision) /
  **101 (tiles+objects)** / 121 (+background bytes +tileset resolution), 24 groups, 48 maps, and the
  same 4 fully-identical pairs (`:37-39`, `:167-168`). The manifest records 101 / 24 / 48 / those
  same 4 pairs, and `canonicalization.excludes` names precisely `imagelayer` references, backdrop
  bytes, map properties and tilesets — while recording the backdrop *per pair* as
  `background_identical` + `background_a/b`, and per map as `background`/`background_sha256`.
  `level_pair_manifest_pinned:846-851` re-derives each flag from PNG bytes (basename resolution as
  the renderer does it, `TMXTileMapRenderer.swift:84-85`), so the 4-vs-20 split is not a typed claim.
- **The pair list is a derived check, not a hand-typed list that can drift.** `identical_pairs` is
  re-verified three ways: every declared pair must still be hash-equal (`pair_violations`, `:822`),
  every *undeclared* hash collision must be absent (`undeclared_collisions`, `:827`), and the
  declared set must equal `DECLARED_PAIRS`, which the script *generates*
  (`[(f'L02S{xx:02d}', f'L05S{xx:02d}') for xx in range(3, 26)] + [L03S09/L04S11]`, `:85-86`) rather
  than typing out. Per-map digests are recomputed from the corpus and diffed (`drift`, `:817`).
  Only `DECLARED_FULLY_IDENTICAL` (`:88`) is literal — and it is contradicted by the byte-derived
  check above, so a wrong literal fails. Controls flip on a synthetic divergent fixture, a new
  collision, one added object and one changed tile (`:854-890`), plus 6 tampers rejected by
  `manifest_selfcheck` (`:946-976`) including a re-ordered pair and a background swap; `self_check
  .body_sha256` (`6be262cb…`) covers everything but itself, so a hand-edited digest fails.
  FORBID-001 has its own guard (`no_invented_content`: blob equality over `Exolon/Resources` +
  `unique == 101` + pair set unchanged + no group of >2).
- **MINOR.** INV-001 (current `change-spec.yaml`) says the canonicalization version "is recorded
  **with every hash**". The manifest records it once at document level; the 125 per-map entries and
  24 pair entries carry no `canon` field (`maps.L01S01` = background/object_layers/scene/sha256/
  stage/tile_layer_count/zone_index/zone_number_property). It is bound transitively through
  `self_check.body_sha256`, and `build_manifest` stamps `canonicalization_version` into the baseline
  too, so the *intent* is met. Either add `"canon": CANON_VERSION` per entry (and require it in
  `validate_manifest`), or reword the invariant to "bound to every hash by `self_check.body_sha256`".
  Do not leave the wording claiming something the artifact does not contain — this repository has a
  standing citation-integrity history (`d4c7a58 docs(audit): final citation-integrity sweep`).

## 4. Unchanged-output guarantee for the 76 markers — MINOR

**The claim itself is true — I proved it independently of the meter.** Extracting the seven legacy
arms from `git show 295690b:…TMXLevelRuntime.swift` (as `if/else if` bodies) and from the working
tree (as `case .kind:` arms), then diffing them line-by-line with comments stripped:

```
beam_ 4/4 topdown_electro 1/1 blinker 1/1 stage_end 1/1 changing_room 8/8 beacon_base 9/9 control_beacon 10/10
→ code-identical-ignoring-comments = True for all seven
```

Dispatch order is preserved (the seven tests keep their positions inside `classify`, `TMXMapLoader.swift:407-421`,
with the three new tests appended after them), so no marker re-buckets. The golden baseline is
genuinely pre-change, not self-fulfilling: `baseline-prechange-digest.json` records
`classifier_kinds_at_record: []` (the enum did not exist yet) and `claimed_at_record` = the seven
legacy substrings, and the golden digest `545e281f470c0900…` matches today's recomputation.

**But the guard is weaker than its own AC wording and partly decorative:**

- `covered_marker_digest` digests the **input** `source_marker` records of legacy-matched families
  (`covered_marker_records`, `:539-551`) — geometry/props from the TMX. It cannot move unless the
  resources move, which `no_invented_content` already pins at blob level. So that half of AC-005
  mostly re-proves a different probe.
- The output half is `branch_fingerprint` (`:333-350`), a regex summary: mutating calls,
  `SKTexture(imageNamed:)`, `image:`, node names, `rect_count` and `CGRect\(([^)]*)\)` bodies.
  The rect regex stops at the **first** closing paren, so every rect string in the golden file is
  truncated (`beam_` → `'x: sx, y: max(0, bottomY - 240'`, no width/height). I mutation-tested the
  current source in memory:

  | injected edit to the `beam_` branch | fingerprint changed? |
  | --- | --- |
  | `height: 272` → `height: 999` | **no** |
  | `width: 48` → `width: 120` | **no** |
  | add a whole extra statement (`let zz=1`) | **no** |

- The probe's declared flip for this half is `branch_edit_detected` (`:1017`), which is literally
  `branch_fingerprint('beam_', …) is not None` — it proves locatability, not edit-sensitivity, and
  cannot fail. The header of `wave_c_check.py:24-26` promises "Every probe owns at least one
  *mandatory flip*: a synthetic mutation that must make its own assertion fail". For
  `unchanged_marker_output` the three real flips are all on the input-digest side. This is precisely
  the class of decorative control this repository has been auditing for.
- Not affected: an edit inside a helper a legacy branch calls (`addDestructible`, `beaconBase`
  arithmetic outside `CGRect(…)`) is invisible for the same reason.

**Cheapest fix (keep it in wave C):** balance the rect capture (`CGRect\(((?:[^()]|\([^()]*\))*)\)`)
plus statement-signature capture, and turn `branch_edit_detected` into a real mutation — feed
`branch_fingerprint` an in-memory copy of the source with one width changed and require the result to
differ from golden. Or downgrade the AC-005 wording from "byte-identical factory output" to what is
actually pinned (unchanged input projection + unchanged branch mutation/node/texture signature) and
cite the `git diff` as the byte-level argument.

## 5. Rebase risk vs waves A/B — MINOR for this branch, BLOCKING for integration order

All four wave branches point at the same base `295690b` with **zero commits**; every wave is
uncommitted working-tree state in a sibling worktree (`.exolon-wave-b`, `.exolon-wave-d`, and wave A
in `/home/pall/projects/exolon`). I ran a real 3-way merge in `/tmp` (base / wave-C working file /
wave-B working file) — no repo file touched:

| File | conflicts |
| --- | --- |
| `TMXLevelRuntime.swift` | **1** (`rc=1`, conflict markers at merged line 382) |
| `TMXMapLoader.swift` | 0 (both waves append types at disjoint offsets: wave-B after `struct TMXMapData:82`, wave-C at `:353-444`) |

The conflict is exactly the P1-7/P1-5 collision: wave-B rewrites the `beam_` arm body
(`git diff` in `.exolon-wave-b`: `forceFields.append(field)` + `rootNode.addChild(field.node)` →
`beamBoxes.append(box)`, plus a post-loop `TMXBeamGrouping` builder and a new `ForceFieldBarrier(hitbox:field:)`
signature) in the very lines wave-C converted from `if source.contains("beam_")` to `case .forceField:`.
Textual resolution is mechanical (keep `case .forceField:`, take wave-B's body, keep wave-C's
`case nil:` recorder), **but after any merge order that admits wave-B,
`unchanged_marker_output` will fail** — the golden `beam_` fingerprint
`mutations: ['forceFields.append','rootNode.addChild']` no longer matches. That failure is correct
and desirable (wave-B genuinely changes beam field construction, P1-5), yet the change package does
not mention it, and §4 shows the fingerprint is only sensitive to *this particular* edit because it
captures mutating calls. Required before either branch merges:

1. Record in the wave-C package (or a short-lived integration change) that `beam_`'s AC-005 golden
   entry must be re-recorded at the integrated tree with an explicit ruling, and that
   `baseline-prechange-digest.json` is bound to `295690b` (`base_commit` field) — do not silently
   re-point it at a post-wave-B tree.
2. Prefer **wave-C before wave-B** for the `source_marker` shape change: wave-B's P1-5 work then
   rebases onto the exhaustive switch, where a new family is a compile error, instead of onto the old
   chain. If wave-B lands first, wave-C's `classify` must additionally absorb `beamBoxes`.
3. Shared-file exposure is otherwise low: wave-A currently touches only `Player.swift` locally but
   plans `TMXLevelRuntime.swift:236` (entityID) and a GameScene emission sweep + F1 overlay
   (`tasks.md:24,29` of wave A) — `:236` is below wave-C's first runtime edit at `:46`, and wave-C's
   only GameScene edit is `:1123`/`:1129`. Real conflict probability there is the debug-overlay
   region, not the marker path. Wave-A adds ~5 new `.swift` files and therefore owns the pbxproj
   4-edit churn; wave-C adds none, which is the single best rebase property of this branch.
4. `engineering/contracts/` is created by wave C first (`level-content-v1.json`); wave-A plans
   `engineering/contracts/schemas/gameplay-event-v1.schema.json` — different paths, no content
   conflict. No canonicalization clash either: wave-B's `tmx_base_hashes.json` is *git blob sha1* of
   whole `.tmx` files (a read-only guard), a different slice from `wave-c-canonical-1`, and it does
   not enter `engineering/contracts/`.

## 6. Gate state observed

- `python3 wave_c_check.py` (current tree): **`RESULT: ALL_WAVE_C_PROBES_PASS | probes=9 failed=0`**,
  2.49 s, `product_executed=true`. Writes nothing into the repo (temp dir only; verified by
  `find -newermt` after the run).
- `swiftc -frontend -parse` rc=0 for the three touched Swift files.
- `python3 scripts/grok_verify.py --mode pr --no-record`: everything **PASS** except
  `source-stability`. It flapped during this audit — FAIL → PASS → FAIL across three runs minutes
  apart, with `tasks.md`, `marker-coverage.md`, `change-spec.yaml`, `analysis-docs_researcher.md`,
  `audit-repo_explorer.md` and `green-meter-run.txt` appearing underneath it. **This is the write
  owner editing concurrently, not a meter defect**; `find -newermt '-2 minutes'` confirms it. The AC-001
  `{"receipt": "verification"}` cannot be recorded while two agents write the same tree — the
  implementer must settle, then re-run and record; a receipt taken now is stale by construction.
- `ruff`, `bandit`, `secret-scan`, `contract-structure` (1 contract), `change-spec` (1 spec),
  `git-diff-check 4/4`, `factory-unit`, `factory-postgres-exit`: PASS in the same runs.
- `requirements.md` is still the untouched template (`- [ ] Given ..., when ..., then ...`) while
  `change-spec.yaml` carries the real AC text — cosmetic, but the typed authority and its prose
  sibling should agree before the PR.

## Recommended actions, in priority order

1. Add the `disposition ⟺ evidence['is_safe'][kind]` assertion (§1) — one line, closes the only
   demonstrated false-green, and give it a flipping control.
2. Make `branch_edit_detected` a real mutation and fix the truncated `CGRect` capture, or reword
   AC-005 to the weaker claim actually pinned (§4).
3. Resolve INV-001's "recorded with every hash" wording vs the document-level version tag (§3).
4. Record the wave-B `beam_` re-baseline decision and the merge-order ruling in the change package
   before either branch is pushed (§5).
5. Optional prose tightenings: AC-001 "typed factory object" ⇒ "typed arm (object, no-op or
   recorded)", and the `unmatchedSourceMarkers` "read by the coverage meter" comment (§1).

None of these is a product-code change. The product half of wave C is minimal, well-placed and
independently confirmed to be output-preserving.
