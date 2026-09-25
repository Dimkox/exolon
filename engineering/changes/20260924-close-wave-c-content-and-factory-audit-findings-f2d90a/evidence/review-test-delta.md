# Test review — DELTA re-review, change f2d90a (wave C)

- Reviewer: `test_reviewer`, read-only; second pass over the fixes to findings F1-F7 of
  `evidence/review-test.md`. Base `295690b7fc72`, tree `/home/pall/projects/.exolon-wave-c/exolon`.
- Date: 2026-09-24. Report path: `evidence/review-test-delta.md`.
- Method discipline: every claim below was re-measured on the **current bytes**, in a private
  `/tmp/mut2/<id>` copy per case (`shutil.copytree`, never a mutate→restore path — see §Trust).
  `A00-pristine` (unmutated copy) → `ALL_WAVE_C_PROBES_PASS`, rc=0, so every red is caused by the
  mutation and not by the harness.

## Verdict

**PASS on the test story.** F1 is resolved and I verified it under a **stronger** forger model than
the fix's own controls. F2, F5, F6, F7 are resolved. F3 and F4 are **acceptable disclosed residuals**,
not must-fix, subject to one merge condition on F3 (§F3). No new blocking defect found. Nothing in
the 59-control census is circular, constant or tautological by my own static audit.

| Finding | Status | My independent evidence |
| --- | --- | --- |
| **F1** contract value tamper | **RESOLVED** | 9 keyed-re-seal forgeries + map-drift + map-edit-with-regen: **all red**. Only the residual they name (prose weakening) survives. |
| **F2** GameScene / rendering | **RESOLVED** | overlay delete → red; syntax error in each of 2 non-compiled files → red; gate self-tests its own falsifiability |
| **F3** type error in `TMXLevelRuntime.swift` | **ACCEPTED RESIDUAL** (conditional) | my C03 reproduces their recorded negative exactly (green) |
| **F4** AC-005 text-local golden | **ACCEPTED RESIDUAL** | my C06 (`hitPoints 25→1`) still green |
| **F5** stale v3 mirror | **RESOLVED as far as scope allows** | meter now prints 2 explicit WARNINGs; cross-checks its own pinned tuple against the mirror |
| **F6** 4 decorative controls + wording | **RESOLVED** | 59/59; static audit clean; AC-001 wording corrected at source |
| **F7** baseline provenance | **RESOLVED** | recorded checker sha == worktree sha; verdicts reproduce exactly |

## 1. Meter and census on current bytes

`python3 evidence/wave_c_check.py` → `RESULT: ALL_WAVE_C_PROBES_PASS | probes=9 failed=0`, rc=0,
**2.9 s** (SIG-001's ≤120 s still met). `--json` census: **59 control assertions across 9 probes**,
all true — matching `green-meter-run.txt:116` ("TOTAL: 59 named controls, 59 true") and the parent's
claim. Per-probe: coverage 6, baseline 3, disposition 6, pin 5, selfcheck **11** (was 7),
unchanged 11, no-invented 5, safe-models **9** (was 6), zone 3.

One precision note on the number: **59 assertions, 58 distinct names** — `bogus_substring_rejected`
is asserted in two different probes (`ignored_types_disposition` and `safe_models_are_labeled`),
which is legitimate (two different guards) but means "59 named controls" should be read as
59 assertions. My earlier "48 load-bearing + 4 restatements" is superseded: the current figure is
**59 load-bearing / 59 true**.

Static audit (not a spot check): I enumerated all 59 runtime keys from `--json`, mapped each to its
source expression, and pattern-matched for the failure forms I had flagged — `not problems`
(circular), literal `True` (constant), `x or not x` (tautology), the `zz_control` set identity, and
the self-referential `blk_zz_control` literal. **Result: NONE flagged.** Verified the specific ones:

- `honest_table_accepted` and `zero_based_formula_holds`: **0 occurrences** — deleted.
- `zero_based_formula_holds` → `formula_distinguishes_base_zero_from_base_one` (`:1787-1791`): asserts
  the 0-based reading *matches* L02S03's recorded `027` **and** the 1-based reading *does not* — fails
  if the formula is mis-transcribed, which `not problems` cannot.
- `synthetic_unclaimed_detected` (`:824-826`) → sensitivity **and** precision over the extracted
  `unclaimed_values()` helper (`:742-748`): the second conjunct (`not unclaimed_values(distinct, claimed)`)
  is exactly what kills the old insensitivity — with `claimed = set()` it now goes False.
- `new_texture_literal_detected` (`:1562-1564`) → `new_literals(before, before|{x}) == {x}` **and**
  `new_literals(before, now) == set()`, over the extracted helper whose docstring (`:751-754`) names
  the constant-True form it replaces.
- `uniqueness_shift_detected` (`:1567`) → `!= 125` replaced by "forcing one digest to a novel value
  must raise the unique count by exactly 1".

## 2. F1 — re-verified under a stronger threat model than the fix claims

The design change is the right one: `validate_manifest` (`:1261`) now re-derives every data claim from
`Exolon/Resources` — per-map canonical digest, the backdrop the map actually references, the sha256 of
that backdrop's bytes, `background_count` vs real `imagelayer` count, pair hash-equality, and
`unique_count` from the corpus; `corpus_hashes` defaults to a fresh recomputation (`:1270-1271`) and
all four call sites are accounted for (`:1346`, `:1358`, `:1394`, generator `:1954`) — **no call site
can skip it**, and passing `{}` explicitly would fail closed (every map "not present in the corpus").
The seal is keyed on `INTEGRITY_BIND` (`:1242`), and the code says out loud (`:1237-1241`, `binding_limit`
`:1401-1406`) that the seal is *not* the teeth — the live re-derivation is.

My forger model: a party who has **read the checker source and knows the key**. I imported
`body_digest` from the committed checker and re-sealed every tamper correctly, on a **different victim
map** than their control uses wherever possible, then ran all nine probes:

| id | tamper on the committed contract, then **keyed re-seal** | result |
| --- | --- | --- |
| K10 | `L02S16.background` → `zone_999_original.png` (my original C10) | **RED** — `declares background 'zone_999_original.png' but the map references 'zone_040_original.png'` |
| K11 | `L02S16.background_sha256` → `ab×32` (my original C11) | **RED** — `…but the resolved file bytes are '60d81c4d0bb11cf4'` |
| K12 | `L02S16.sha256` flipped one hex char | **RED** on 2 probes (`level_pair_manifest_pinned`, `manifest_selfcheck`) |
| K13 | **swap two whole map entries** (L02S16 ↔ L05S16) so every field stays internally consistent — my hardest case | **RED** on 2 probes (`manifest_selfcheck`, `zone_index_formula`) |
| K14 | drop the backdrop claim on **L03S09** (their `drop_background_layer_claim_rejected` targets L02S16; mine cannot coincide) | **RED** — empty declared vs real bytes |
| K15 | declare `L01S01/L01S02` identical while **keeping 24 entries** (so the count check passes) | **RED** on 2 probes |
| K16 | gut the ruling prose (`decision` → `"x"`, `premise_citations` → `[]`) | **RED** via `level_pair_manifest_pinned` |
| **K17** | **weaken** wording (`caveat`/`source_tension` → `"see notes"`) keeping every asserted field non-empty | **GREEN** — matches their disclosed limit exactly |
| B01 | edit a shipped `L01S01.tmx`, leave the contract alone | **RED** on 3 probes |
| W18 | edit `L01S01.tmx` **and** regenerate the contract the legitimate way (`--write-manifest`) | **RED** — `1 resource files rewritten: Exolon/Resources/L01S01.tmx` |

W18 is the case that could have leaked and does not: the contract and the corpus can be brought into
agreement by a regeneration, but FORBID-001's blob comparison against the route base is the backstop,
so the two guards together close the loop. Their own `f1-tamper-proof.txt:21-29` matrix reports the
same verdicts for C7-C11/K10-K13, and my re-derivation agrees row-for-row on every case we share.

**F1 is closed.** The only surviving bypass (K17) is precisely the limit stated in
`binding_limit` and `level-content-v1-binding-note.md`: an armed forger can soften *narrative* wording
while keeping every asserted field present. That is a real but bounded residual — the data claims, the
pair set, the uniqueness count, the zone formula and the shipped bytes cannot be forged this way, and
the ruling's *existence*, keyword and citations are still asserted.

**Irreducible threat model, stated once:** anyone who can edit `wave_c_check.py` can weaken any of
this. The fix protects against editing **only the contract JSON**, which is the correct and only
achievable claim; it does not (and cannot) protect against editing the guard. `INTEGRITY_BIND` raises
the cost of an *unaware* forger, not of an *armed* one.

## 3. F2 — closed, and the gate now self-tests

- `GAME_SCENE_SWIFT` added (`:61`) and included in `CHANGED_SWIFT` with the other two (`:64`);
  `safe_models_are_labeled` reads it (`:1694`) and asserts the overlay binding — the loop
  `for … in currentLevel.safeModelMarkers`, that it draws `marker.rect` through `addDebugRect`, that
  it passes `marker.label`, that `addDebugRect` still takes `label:`, and that `debugOverlay` exists.
  New controls: `honest_overlay_binding_accepted`, `overlay_deletion_detected`,
  `overlay_label_strip_detected`.
  **My C02** (delete the entire overlay block — exactly my old R2 case) → **RED** on
  `safe_models_are_labeled`: *"GameScene.swift never reads safeModelMarkers: a recorded safe model has
  no debug rendering (FORBID-002 'in debug rendering')"*. The message names the clause it protects.
- `swift_parse_gate()` (`:669`) executes `swiftc -frontend -parse` per file, returns `None` (reported,
  never passed) when the toolchain is absent, and is asserted on all three changed files —
  green run shows `{"GameScene.swift": "ok", "TMXLevelRuntime.swift": "ok", "TMXMapLoader.swift": "ok"}`.
- `parse_gate_selftest()` (`:690`) is the part I would have asked for unprompted: it feeds the gate an
  unclosed-brace file **and** a well-formed file and requires broken≠ok ∧ good==ok, as control
  `parse_gate_detects_a_broken_file`. My **C04** (unclosed `addDebugRect(node`) and **C05** (appended
  `func zzBroken( {`) → both **RED**, with the compiler's own message quoted. So the prose claim in
  `test-plan.md:17` is now an executed, reproducible, falsifiable check.

## 4. F3 — ACCEPTABLE RESIDUAL (not must-fix), with one merge condition

My **C03** (`forceFields.append(field.thisIsNotAMember)`) → `ALL_WAVE_C_PROBES_PASS`, rc=0 —
identical to their recorded negative at `f2-f3-rendering-and-typecheck.txt:41-49`.

I accept this as a residual rather than a must-fix, for four reasons:

1. It is a **host ceiling, not a design weakness**: SpriteKit/CoreGraphics cannot be type-checked on
   Linux, and they **deliberately declined** to write a SpriteKit stub. That is the right call — a stub
   would type-check the scene against fiction and manufacture false assurance, which is the exact
   failure mode this change exists to eliminate.
2. The file that owns this change's *logic* is the strongest-covered one: `TMXMapLoader.swift`
   (classifier + safe-model kinds) is genuinely **compiled and executed** in `swift_product_evidence`
   (`:435-514`), with the no-shim control proving the repository file is what was built.
3. The residual is bounded and stated in three places, including the sharp sentence *"AC-005/FORBID-002
   must not be read as covering a Swift type error in those two files"* — which is exactly the wording
   correction I asked for.
4. The syntax gate (§3) still catches the cheap class of breakage in both files.

**Condition, unambiguously:** the macOS build (`xcodebuild -project Exolon.xcodeproj -target Exolon`)
must actually run and be recorded in this PR before merge. If the PR merges with F3's residual and
*without* that build, then two of the three changed Swift files have had **zero** semantic verification
and I would restate F3 as **must-fix / blocking**. The change's own `test-plan.md:16` already names
this as the E2E step, so this is a sequencing requirement, not new scope.

## 5. F4 — ACCEPTABLE RESIDUAL, with a wording correction owed

My **C06** (`LevelObstacles.swift:766` `var hitPoints = 25` → `1`) → all 9 probes **green**. Expected:
`fingerprint_body` (`:572-588`) is a branch-body text projection, so collaborator semantics are out of
its scope by construction. Accepting as a residual — pinning transitive object behaviour would need a
runtime harness for `TMXLevelRuntime`, which needs SpriteKit, i.e. the same ceiling as F3.

But one wording item is genuinely owed and is cheap: `change-spec.yaml` AC-005 still reads *"generate
byte-identical factory output"*. After the AC-001 fix (now *"all 127 source_marker INSTANCES (11
distinct values)"* — verified corrected, my F6 item closed at the source), AC-005 is the last criterion
whose text claims more than its probe measures. Suggested precise form: *"…keep byte-identical
factory **branch** output (source-level fingerprint per arm, read from the immutable base blob)"*.
Same for INV-001's tail: *"bound transitively … through the recomputable self_check.body_sha256"* now
**understates** the mechanism (keyed seal + live re-derivation) and should point at
`level-content-v1-binding-note.md`. Non-blocking, wording only.

## 6. F5 / F7 — resolved

- **F5**: `stale_mirror_report()` reads both other-package mirrors (`v3_measurements.py:89` `HANDLED`,
  `linux_static_audit.py` `HANDLED_SOURCE_SUBSTRINGS`) and the meter now prints, on every green run:
  `WARNING (not a failure of this change): v3_measurements.py still reports 76/127 (rc=0) …`
  (×2). It also pins its own legacy tuple against the mirror's — so drift in *the baseline definition*
  is noticed too. This is the right resolution for out-of-scope evidence: silence was the bug.
- **F7**: `baseline-meter-red.txt:5` records `checker sha256 = 5ad27c98…401edbc0`; I computed
  `sha256sum evidence/wave_c_check.py` = `5ad27c98…401edbc0` — **identical**. I then re-ran the
  committed checker against `git checkout 295690b -- Exolon/`: same `RESULT: WAVE_C_PROBES_FAIL |
  probes=9 failed=3 ignored_types_disposition,marker_coverage_all_maps,safe_models_are_labeled`, rc=1,
  and `diff` of all nine PASS/FAIL verdict lines against the artifact is **empty**; 50 true-controls
  both sides. The artifact and the generator now agree control-for-control, which was the whole ask.

## 7. Gate record (as requested)

- `python3 scripts/grok_verify.py --mode pr` receipt
  `.grok-stack/runtime/receipts/f2d90a858699/verification.json`: `status: pass`, created
  **22:13:15Z** (after the fixes), `changed_file_inventory.union_count = worktree_count = 34`
  (matches "changed=34"), `source-stability: pass` — *"repository fingerprint remained stable"*.
- Product bytes are unchanged by the test work, which I confirmed directly rather than by trusting the
  receipt: `sha256sum` prefixes `91f354db` (`TMXMapLoader.swift`), `202cd23c` (`TMXLevelRuntime.swift`),
  `f2eb43f2` (`GameScene.swift`) — identical to what my first review saw, and `git diff 295690b --stat`
  is still `4 files changed, 168 insertions(+), 8 deletions(-)`.
- Receipt `criterion_ids` is still `["AC-001"]` — only AC-001 names a receipt in the spec, so this is
  spec-conformant, but 8 of 9 criteria have no fingerprint-bound receipt of their own. Noting, not
  blocking.

## 8. Trust assessment of the self-disclosed R4 near-miss

They reported that their **first** R4 verification looked like a *catch* and was not: a helper had
`cd`'d into the evidence dir, which broke the previous case's restore path, so R3's syntax damage was
still in the file and the parse gate had caught *that*; re-running R4 isolated gave the negative
(`f2-f3-rendering-and-typecheck.txt:52-56`).

My weight on this is **positive**, for three reasons: (1) the corrected conclusion is exactly what I
independently measured in C03, so the final record is right; (2) the discarded false-positive was kept
in the evidence rather than quietly deleted, and is annotated with why it matters; (3) the failure mode
they describe — a green result that is an artifact of the harness — is the precise subject of this
change, and self-catching it is the behaviour the change is trying to institutionalise.

Operationally it does cost something: any claim of theirs produced by a **mutate→restore in one tree**
path deserves less weight than one produced by a fresh copy per case. I removed that exposure rather
than arguing about it: my driver takes a **fresh `copytree` per mutation** with no restore path at all,
plus one unmutated `A00-pristine` control, so every result in §2-§6 is independent of their
methodology. Nothing in this verdict rests on a shared-tree restore.

## 9. Residuals carried forward (all non-blocking)

1. **K17** — an armed forger may weaken contract *narrative* wording while keeping every asserted field
   non-empty. Disclosed in `binding_limit` + the binding note. Accept.
2. **F3** — no type-check for `TMXLevelRuntime.swift`/`GameScene.swift` on this host. Accept **conditional**
   on the macOS build running in this PR (§4).
3. **F4** — collaborator semantics outside branch bodies are unpinned by AC-005. Accept; fix AC-005 /
   INV-001 wording (§5).
4. **Mirror cleanup** — `v3_measurements.py` / `linux_static_audit.py` still publish pre-fix numbers;
   now loudly warned about, still another route's scope (owner backlog).
5. **Receipt coverage** — 8/9 criteria have no criterion-bound local receipt; the meter is the witness.
6. `evidence/__pycache__/wave_c_check.cpython-312.pyc` is stale relative to the current source.
   Harmless (script execution never reads it) but it is clutter inside a committed evidence dir.
7. Census phrasing: "59 named controls" = 59 assertions / 58 distinct names.

## Reproduction

```bash
cd /home/pall/projects/.exolon-wave-c/exolon/engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a
python3 evidence/wave_c_check.py                       # 9/9 PASS, 2.9 s, + 2 mirror WARNINGs
python3 evidence/wave_c_check.py --json                # 59 control assertions, all true
# delta battery (fresh copytree per case; logs /tmp/mut2/*.log):
python3 /tmp/mut2/drive2.py                            # A00, K10-K17, B01, C02-C06, D01-D06
python3 /tmp/mut2/w18.py                               # map edit + legitimate --write-manifest
# F7: cp -a tree /tmp/mut2/redbase && (cd redbase && git checkout 295690b -- Exolon/) && run meter
```

## Disposition for the orchestrator

- This file is the only thing this re-review wrote; no tracked file was touched, and the meter re-run
  after writing it still reports `ALL_WAVE_C_PROBES_PASS`.
- Suggested receipt for the delta pass (the first pass' report stands as written; this one supersedes
  its verdict):
  `python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/review-test-delta.md`
- **Staleness:** writing this file changes the tree fingerprint, so the `pass` verification receipt
  (`d37c26afa1c4`, created 22:13:15Z) is stale from now on. Re-run
  `python3 scripts/grok_verify.py --mode pr` after this report is on disk and before anything is
  declared complete; no product file needs to change for that, so the product hashes above stay valid.
