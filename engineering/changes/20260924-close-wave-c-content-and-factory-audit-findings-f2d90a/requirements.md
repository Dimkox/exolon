# Requirements — Close wave-C content and factory audit findings in the Exolon repository: P1-7 (of 127 source_marker values only 76 are covered by the level factory matcher; blk_waggon, blk_gunMachine_BOTTOM and blk_mushroom are silently ignored on 32 maps - add the factory types or an explicit safe visual-object model) and P1-12 (only 101 of 125 maps are unique: 23 L02/L05 pairs and L03S09/L04S11 are identical - rule on intentionality explicitly, pin the identity with a committed digest manifest test and document it in the level spec).

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] **AC-001** Given all 125 shipped maps, when the factory matcher is applied to their 127
  `source_marker` objects, then each is resolved by the product classifier into an explicitly
  dispositioned arm — typed behavior, labeled safe model, or documented no-op/write-only — and an
  unmatched marker is recorded (`unmatchedSourceMarkers`) and fails the meter: the silent-ignore path is
  gone, not merely unreached. The disposition column is **normative evidence**, so `disposition ==
  safe-model ⟺ product isSafeModel ⟺ label present` is enforced both ways, and 127/127 means
  *resolved*, not *behaviour implemented* (50 typed live, 51 safe models, 21 no-ops, 5 write-only).
  Evidence: `wave_c_check.py::marker_coverage_all_maps` (RED 76/127 kept in
  `evidence/baseline-meter-red.txt`, GREEN in `evidence/green-meter-run.txt`), plus the compiled product
  classifier itself reporting `unmatched: {}` over 125/125 loaded maps, and
  `evidence/bypass-closure-proof.txt` for the relabelling bypass.
- [x] **AC-002** Given the three formerly-ignored families, when any of the 51 markers is loaded, then
  each carries a committed disposition naming its kind, footprint, label and the evidence behind it.
  Evidence: `wave_c_check.py::ignored_types_disposition` against
  `evidence/marker-disposition-v1.json`, rendered into `evidence/marker-coverage.md`.
- [x] **AC-003** Given the audited canonicalization, when the 125 maps are hashed, then exactly 101 are
  unique, the 23 `L02Sxx≡L05Sxx` pairs plus `L03S09≡L04S11` hash equal, no other pair collides, and the
  four backdrop-identical pairs are flagged.
  Evidence: `wave_c_check.py::level_pair_manifest_pinned` against
  `engineering/contracts/level-content-v1.json`.
- [x] **AC-004** Given a synthetic map that diverges from a declared pair, then the pin test fails; given
  a tampered manifest entry, then the self-check rejects it — and a control that cannot flip is itself a
  failure. Evidence: `wave_c_check.py::manifest_selfcheck` (10 tamper controls — each one re-seals the
  contract before being judged, so they test content and not checksum drift — while the honest body is
  accepted), including `declare_nonidentical_pair_rejected` (the divergent-pair case, moved into the
  probe AC-004 names) and `unkeyed_reseal_rejected`; plus the 5 pin-probe controls. Independent
  external reproduction of the reviewer's shipping cases: `evidence/f1-tamper-proof.txt`.
- [x] **AC-005** Given the 76 markers the matcher already covered, when this change is applied, then
  their factory **branch** output is digest-identical — a source-level fingerprint per arm (the 76 marker
  records plus mutations, nodes, textures, **balanced-paren-captured** `CGRect` geometry and numeric
  literals), read against the immutable base blob via `git show <base>:TMXLevelRuntime.swift`, so the
  probe cannot be satisfied by editing a golden. Scope of the claim, stated: it is *branch source text
  for this file*, **not** transitive collaborator behaviour (R2b / reviewer case C06).
  Evidence: `wave_c_check.py::unchanged_marker_output`; golden digest `545e281f470c0900…` in
  `evidence/baseline-prechange-digest.json`; the mutation controls in
  `evidence/bypass-closure-proof.txt`.
- [x] **FORBID-001** No tile or object content was authored to dissolve the **24 duplicate groups**
  (24 pairs, 48 maps): `wave_c_check.py::no_invented_content` proves all 282 `Exolon/Resources` files are
  blob-identical to route base `295690b`, uniqueness is still 101, the group set is still the audited 24,
  and no new image/texture literal exists. Intentionality is **ruled**, not asserted, and the manifest
  discloses that the premise does not reach `L03S09/L04S11` (`ruling.premise_citations`,
  `pair_notes`).
- [x] **FORBID-002** Every safe model is labeled in the product source (`safeModelLabel`), in the record
  (`TMXSafeModelMarker.label`), in debug rendering (labeled node name in the hitbox overlay) and in the
  meter output, and a safe model declared as `typed` (or a typed one carrying a label) now reddens two
  probes: `wave_c_check.py::safe_models_are_labeled`.
- [x] **INV-001** `zone_index == (stage-1)*25 + (scene-1)` is derived and validated for all 125 maps,
  while the raw `zoneNumber` property exists on **117 of 125** (`L01S01…L01S08` honestly record null) and
  every present property equals the derived index. The canonicalization version is declared once at
  document level and bound to every hash through `self_check.body_sha256` — which since the test-review
  fix is a **keyed** seal plus **live re-derivation of every data claim**, not a recomputable checksum;
  see `evidence/level-content-v1-binding-note.md` for what the seal does and does not protect.
  Evidence: `wave_c_check.py::zone_index_formula`, `manifest_selfcheck`.
- [x] **OBJ-001 / SIG-001** 0 silently ignored markers, manifest pinned, controls flip, and both tables
  regenerate with one stdlib-only command in **~2.4 s** against a 120 s budget.

## Failure and edge cases

- **8 of 125 maps carry no `zoneNumber` at all** — `L01S01…L01S08` (zones 000-007), which hold ad-hoc
  provenance keys instead. The 0-based formula is therefore verified on the 117 maps that have the
  property and on the manifest's derived `zone_index` for all 125; those 8 are honestly null for the raw
  property, not silently skipped. (The independent audit raised this wording distinction; the typed AC
  text is being amended by the controller — `change-spec.yaml` is not edited here.)
- **A `sourceBlock` matching nothing** must reach `unmatchedSourceMarkers`, and the meter fails on it.
  Controls: a synthetic `blk_zz_control` value is reported as unclaimed, and renaming the recorder call
  flips the probe (`missing_recorder_flips_probe`) — so "covered" cannot be claimed by the meter alone.
- **A marker matching two substrings** resolves by source order, not by accident: the classifier keeps
  the seven original tests in their historical order, and "no value currently double-matches" is recorded
  in the characterization as a property of today's data rather than trusted as an invariant.
- **Empty `sourceBlock`** returns `nil` from the classifier and is recorded, never dropped.
- **A declared pair that later diverges** (someone regenerates one half) fails
  `level_pair_manifest_pinned`; **a newly pasted duplicate** fails it too through the
  undeclared-collision arm. Both directions are demonstrated by controls.
- **Manifest tampering without regeneration** fails `self_check.body_sha256`.
- **Layer encodings**: non-empty `compression` is a hard error in the product loader, so the
  canonicalizer cannot silently mis-decode a layer; the shipped corpus is 138/138 uncompressed.
- **A new `TMXSourceMarkerKind` case added without a runtime arm is a compile error**, because the
  runtime `switch` is exhaustive and deliberately has no `default:`. That is the structural guard
  replacing the deleted silent-drop path.
- **"Resolved" is not "implemented"**: the 51 safe models stop the loss but add no behaviour. Stated in
  `marker-coverage.md` so the 127/127 figure cannot be misread as full original fidelity.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example,
debt, or digest named here is non-authoritative context until the verifier rederives current governance
evidence.

- Applicable rule IDs: none — this repository has no `governance/` or `architecture/` directory and the
  gate reports both as "not configured". The binding authorities here are [`brief.md`](brief.md) rulings
  1-3, [`change-spec.yaml`](change-spec.yaml), the route (`route.json`: risk low/green, no human gates,
  write owner `general_implementer`), and the merged P1-7/P1-12 measurements, which were reused and
  re-proved rather than freshly re-derived.
- Canonical-example deviations and evidence: the `blk_gunMachine_BOTTOM` row deviates from "add a factory
  type" deliberately — the in-tree evidence cannot identify what that action does (56 type-11 actions
  exist in the original, only 18 are exported with a BOTTOM marker, and the other 38 sit in 18 maps that
  have no BOTTOM marker at all), so a labeled safe model is used instead of invented behaviour. Recorded in
  `evidence/marker-disposition-v1.json` and in Deviations D2 of [`tasks.md`](tasks.md).
- Intentional debt created, repaid, or accepted: **repaid** — 51 silently dropped markers, and the
  untracked level-duplication question. **Accepted and named** — the four hand-copied mirrors of the
  matcher literals in other packages' committed measurers (`v3_measurements.py:89`,
  `linux_static_audit.py:47-55`) remain mirrors and still cannot detect this fix; collapsing them belongs
  to that route (Deviations D4, residual risk R1).

## Non-functional requirements

- Security: no auth, secret, PII, tenant or payment surface is touched; no external system is written to.
  The meter shells out to `git` and `swiftc` with fixed arguments and never interprets repository content
  as a command; no `.env`, key or credential store is read.
- Reliability: backward compatible by construction — the 76 already-covered markers are digest-checked
  unchanged (AC-005), no physics/damage/score/spawn path reads the new arrays, and no shipped data file is
  modified. Rollback is a forward fix (`rollback.strategy: forward_fix`, 1 step): revert the three Swift
  files; the contract, spec and meter are additive and may stay.
- Performance: full-tree meters run in ~2.4 s against the 120 s budget, stdlib only, with the corpus
  parsed once and memoized across probes. Runtime cost is 51 struct appends per level load and no
  per-frame work, since safe models create nodes only inside the debug overlay.
- Observability: coverage and per-map dispositions are regenerable by one command and committed as
  `evidence/marker-coverage.md`; the manifest records `canonicalization_version` alongside every digest so
  a later change cannot compare against an undocumented method; an unmatched marker is now a failing
  signal instead of an absent one.
