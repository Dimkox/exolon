# Wave C: content factory markers + duplicate-map ruling (P1-7, P1-12)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260924-close-wave-c-content-and-factory-audit-findings-f2d90a`
Route base `295690b` · branch `codex/wave-c-content-factory-20260924`
Risk: low(green) · Write owner: `general_implementer`

## Problem

- **P1-7** (issue #11): of 127 `source_marker` object instances in `Exolon/Resources/*.tmx`
  (11 distinct `sourceBlock` values per the merged census), the
  level factory matcher covers only 76; `blk_waggon`, `blk_gunMachine_BOTTOM`, `blk_mushroom`
  are silently ignored on 32 maps — content lost between original data and shipped levels.
  Measurement: merged `engineering/changes/20260921-...2e7698/evidence/analysis-p1-7-markers.md`.
- **P1-12** (issue #16): canonical hashes show only 101 unique maps of 125 — 23 `L02Sxx≡L05Sxx`
  pairs (xx=03..25) plus `L03S09≡L04S11` are tile-and-object identical (some background-identical
  too). Finding text: "Подтвердить намеренность или восстановить уникальные данные."

## Outcome

Marker coverage is 127/127 with zero silent drops (missing visuals become an explicit, labeled
safe model), and the duplication question is RESOLVED BY RULING, pending PR merge and the owner's
acceptance: the pairs are ruled to be the original game's design (stage 5 is a recolored stage 2; the
reskin is in the source data, not a factory bug), so no content is invented — the identity is instead
pinned by a committed digest manifest and a test that fails if a declared-identical pair ever diverges or
a new collision appears. Intentionality is this change's decision, not a sourced fact: no primary states
it. Issues #11 and #16 stay OPEN upstream (`blocked-on-owner`) until the owner accepts the ruling.

## Scope

### In scope

- Factory matcher: add real handling for the three ignored marker families (visual objects with
  the documented blockset semantics) or, where no visual resource exists, the explicit safe model
  (rendered as a bounded placeholder in debug view, flagged in the coverage meter, never dropped).
- Coverage meter over all 125 maps: every marker maps to {typed object | safe model}, table of the
  51 previously-lost markers → disposition, committed.
- Content spec doc (level data): uniqueness model 101/24, per-pair table, background-file rules
  (only `zone_NNN_original.png` differs; 4 pairs fully identical), the 0-based zoneNumber formula.
- Digest manifest `engineering/contracts/level-content-v1.json`: canonical hash per map + declared
  identical pairs; pin test (pair equality must hold; non-declared pairs must differ).

### Out of scope

- Inventing new tile content to "fix" duplicates (prohibited), physics fixes (wave B), runtime
  marker interpretation in Swift unless the factory output itself must carry the new objects
  (then the minimal runtime type registration is in scope, flagged in tasks).

## Design rulings

1. **P1-12 = intentional content** (matches original Exolon's 125-zone numbering inherited from
   the ASM data; the reskin exists in the source, not in the factory). Close by pinning, not by
   fabricating. If the owner later decides otherwise, the manifest makes exactly which 24 files
   to regenerate a one-command query.
2. **P1-7 order of preference** per marker: real factory type > documented safe model > error.
   "Silently ignored" is removed as a code path: an unmatched marker must fail the meter.
3. Manifest hashes use the same canonicalization as the audit (tiles + objects, background
   excluded from identity, but per-pair background equality recorded) so the numbers (101/24/23+1)
   reproduce the merged measurement, not a new one.

## Constraints

- Backward compatibility: existing 76 covered markers must produce byte-identical output
  (digest check); only the 51 lost markers change behavior.
- Data/privacy: n/a. Performance: full-tree meters ≤ 120 s. Operational: revert = forward-fix.

## Analysis

Implementer records factory location discovery (compiler/tooling lives where LEVEL_COMPILER_AUDIT.md
points) in `evidence/analysis-repo_explorer.md` before edits; cross-check numbers against the
merged P1-7/P1-12 evidence rather than recomputing fresh.
