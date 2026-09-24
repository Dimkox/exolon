# Audit — repo_explorer (route analysis wave): wave C tree state, marker-coverage honesty, manifest recompute

Repo /home/pall/projects/.exolon-wave-c/exolon, branch codex/wave-c-content-factory-20260924, HEAD
295690b (= origin/main). Audit snapshot ~20:19 UTC 2026-09-24, writer in flight. All numbers
independently re-measured by the auditor (python stdlib, in-memory, no writes). Saved by the
controller under `audit-*` because the writer's Task-1 characterization already occupies
`analysis-repo_explorer.md` (no-clobber decision recorded here).

## 1. Diff inventory (measured vs HEAD 295690b)

Modified, uncommitted (Swift + docs, git status --porcelain):
- Exolon/GameCore/Levels/TMXMapLoader.swift (+92): new TMXSourceMarkerKind enum (:364), classify()
  (:407), safeModelFootprintCells() (:427), TMXSafeModelMarker struct (:438).
- Exolon/GameCore/Levels/TMXLevelRuntime.swift (+62/−8): safeModelMarkers/unmatchedSourceMarkers
  (:50-51); source_marker case rebuilt from if/else chain to exhaustive switch classify(...)
  (:363-437); appendSafeModelMarker (:466-477).
- Exolon/GameCore/GameScene.swift (+14): debug-overlay outlines of safe models labeled
  sourceBlock @ mapResource (:1118-1125); addDebugRect gains label: param.
- README.md (+6): "Level content contract" section — claims (125 files/101 distinct/23+1
  pairs/127-of-127) all verified true by this audit.

Untracked (new): engineering/contracts/level-content-v1.json;
engineering/reports/level-content-uniqueness-v1.md; the change package including the meter
evidence/wave_c_check.py (~76 KB), marker-coverage.md, marker-disposition-v1.json,
baseline-prechange-digest.json, baseline-meter-red.txt, and the writer's pre-existing
analysis-repo_explorer.md (filename collision — see §6).

Factory tooling: ZERO changes. git status --porcelain -- factory/ and -- Exolon/Resources/ empty;
scripts/, schemas/, Exolon.xcodeproj untouched (only __pycache__/*.pyc from a pytest run at 19:51).
Coverage meter lives in the change package, not factory/. No new .swift file (deviation D1 in
tasks.md: enum/struct appended to the existing loader file → no pbxproj change legitimately needed).

## 2. Real handling vs catch-all safe-model swallow

Real, family-specific handling; safe-model fallback IS counted as covered — exactly what the spec
authorizes, not a dodge.
- Three formerly-dropped families each have an explicit matcher arm in the product classifier:
  mushroom→.inertScenery, waggon→.inertScenery, gunMachine_BOTTOM→.unconfirmedAction
  (TMXMapLoader.swift:416-418). No catch-all: classify() ends in return nil (:419); runtime
  case nil: records into unmatchedSourceMarkers (TMXLevelRuntime.swift:435-437). Unknown future
  block = meter failure, not safe model.
- The meter's claim set is regex-extracted from the PRODUCT source at run time
  (wave_c_check.py:229 CLASSIFY_RE, :351 claimed_substrings), with a control that the meter
  collapses if product text is stripped (:596-598 meter_reads_the_product_not_itself).
  totals: post_change_covered=127, safe_model_markers=51.
- AC-001/P1-7 literally define coverage as "typed factory object OR explicitly labeled safe
  model"; distinction visible in marker-coverage.md disposition column (typed/safe-model/no-op/
  write-only); FORBID-002 probe wave_c_check.py:1081 safe_models_are_labeled + product reports
  isSafeModel with non-empty labels.
- Executed proof is genuine: swiftc present; meter compiles the actual product loader (same
  one-import delta as committed harness) and runs classify over all 125 maps; UNMATCHED → probe
  fails (:613-616); build succeeding WITHOUT the CoreGraphics shim → fails (:622-624); Swift
  absent → probe RED, not gray (:629-631).
- Disclosed caveats, not spec violations: (a) 127/127 = "resolved/claimed", not "behavior
  implemented" — blinker/topdown_electro stay no-op break arms, stage_end write-only, identical
  to legacy (LEGACY_BASELINE wave_c_check.py:74-86, reproduced red at 20:05); (b) substring
  matching keeps the legacy weakness (blk_mushroom_cannon would classify as scenery) deliberately
  so no shipped value changes bucket (comment TMXMapLoader.swift:403-406).

## 3. Silent-ignore path removed, with receipts

At HEAD the source_marker case was an if/else-if chain with NO final else (git show HEAD, lines
356-394) — unmatched fell through doing nothing: the true silent drop. Working tree: chain gone;
exhaustive switch TMXSourceMarkerKind.classify(...) with NO default: arm
(TMXLevelRuntime.swift:363-437) → new-enum-case-unhandled is a compile error, unknown-block hits
the nil arm. Meter mutation controls: missing_recorder_flips_probe (:599-604); requires
unmatchedSourceMarkers + return nil to exist (:570-589). Residual pre-existing (out of AC-001
marker scope): outer switch object.name still ends default: break (:441-445) — unknown object
NAME (not sourceBlock) intentionally ignored, unchanged from HEAD, commented. App never traps;
failure enforcement sits in the meter, per AC-001 wording.

## 4. level-content-v1.json — independent recompute

Auditor re-implemented wave-c-canonical-1 from the manifest's stated canonicalization (layer
arrays base64→LE-uint32 / csv; layer name/width/height/x/y; every object name/type/x/y/width/
height + sorted props; map-properties and imagelayer/tileset excluded; json.dumps sort_keys →
sha256) and recomputed ALL 125 maps. Every manifest digest reproduced byte-exactly (0 mismatches):
- 101 unique digests; 24 duplicate groups, each a pair: 23×L02Sxx≡L05Sxx (03..25) +
  L03S09≡L04S11 (sha256 1a91d3e7…); maps_covered_by_duplicates=48 confirmed.
- Declared pair spot values match (L02S03/L05S03=25fa25b4…, L02S16/L05S16=1fa0a045…); random 5-map
  set matches.
- background_identical flags verified by hashing actual PNGs for all 24 pairs: exactly the 4
  declared (L02S04/16/22/23 pairs) byte-identical; L03S09/L04S11 correctly false.
- self_check.body_sha256=6be262cb… recomputes; generated_from_commit = current HEAD.
- INV-001 zone formula: all 125 zone_index satisfy 0-based (stage−1)*25+(scene−1); non-null
  zone_number_property always equals it; 8 keyless maps (L01S01…L01S08) honestly null.
  Nit: AC/INV wording "all 125 maps" is exact for derived zone_index but only 117/125 for the raw
  property — wording should say so (controller fix at spec revision, not a data error).

## 5. TMX Resources integrity

git status --porcelain -- Exolon/Resources/ and git diff --stat: EMPTY. 125 .tmx + all
zone_*_original.png bit-identical to HEAD 295690b (content-addressed proof: recompute ran against
working tree, matched manifest from base commit). Post-19:43 mtimes are checkout-time only.
FORBID-001 holds.

## 6. In-flight / owed at close-out (snapshot)

- 19:45:45 state → approved (no implemented/verified transition yet).
- 19:55:07 writer's Task-1 characterization occupies this audit's assigned path → saved as
  audit-repo_explorer.md instead (no clobber).
- 20:02-20:05 disposition table, pre-change digest, RED baseline transcript (3 unclaimed families,
  51 lost, recorder absent; 6 controls green).
- 20:14 marker-coverage.md regenerated, 20:16 wave_c_check.py edited again → doc may lag meter by
  one revision: regenerate before closing.
- No GREEN full-run transcript in evidence/ yet (only red baseline + coverage tables); requirements.md
  still the unfilled template.

## Auditor summary (verbatim 8 lines)

1. Inventory: 4 modified files (3 Swift runtime + README), untracked = contract, uniqueness
   report, change package + meter; factory/ and scripts/ untouched (pycache only).
2. 127/127 is real per-family handling, not a catch-all; unknown → nil → recorded.
3. The meter counts labeled safe models as covered (51 of 127) — honest per AC-001 wording;
   caveat: "resolved" ≠ "behaviour implemented".
4. Silent-ignore path deleted from source, not just unreached; outer object-name default: break
   remains as before.
5. Manifest recompute: all 125 digests byte-exact; 101 unique; 24 pairs incl. L03S09≡L04S11;
   backgrounds correct; self_check and zone formula hold (8 keyless maps honestly null).
6. Resources proven unmodified against HEAD 295690b.
7. In-flight: coverage doc predates last meter edit — re-sync; green transcript owed; state still
   approved; requirements template empty.
8. Collision: writer's Task-1 evidence occupies the assigned analysis path — this file is
   audit-repo_explorer.md by controller decision.
