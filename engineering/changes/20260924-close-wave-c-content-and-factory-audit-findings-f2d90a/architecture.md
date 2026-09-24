# Architecture — wave C (content factory + manifest)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Current behavior
Factory matcher covers 76 of 127 source_marker values; unmatched markers (incl. blk_waggon,
blk_gunMachine_BOTTOM, blk_mushroom) are dropped without a signal on 32 maps. Map duplication
(101 unique / 125) is untracked: nothing pins which pairs are *supposed* to be identical.

## Proposed behavior
Every marker resolves to a typed factory object or an explicitly labeled safe model; silent drop
ceases to exist as a path. A committed canonical digest manifest pins per-map hashes, the
declared-identical pairs (23 L02/L05 + L03S09/L04S11) and background-equality flags; a test makes
divergence or undeclared collision fail.

## Components and boundaries
- Level factory/compiler (Python tooling located via LEVEL_COMPILER_AUDIT.md; implementer records
  exact paths in analysis before editing) — matcher table + coverage meter.
- Runtime Swift registration for any new object type (minimal, parse-gated; pbxproj rules of wave
  A apply if new files land).
- `engineering/contracts/level-content-v1.json` — data contract (canonicalization: tiles+objects,
  background recorded separately, 0-based zone formula honored).

## API and event contracts
No runtime wire events. The manifest is a repository contract: schema {map→sha256,
identical_pairs[], background_identical[], unique_count, canonicalization_version}.

## Governance context / Bitrix
n/a (no governance dir; not a Bitrix repo).

## Decisions
Brief rulings 1–3 binding (intentional reskin pinned, not fabricated; typed>safe>error; audit
canonicalization reused so 101/24 reproduces merged measurement).

## Risks and mitigations
- Invented semantics for the 3 lost types → keep visuals minimal (safe model allowed), document
  per-marker disposition table for review;
- canonicalization drift → manifest self-check recomputes with pinned method id;
- regression on existing 76 → byte-identical digest check AC;
- runtime type creep → new Swift types only when the marker is interactive, else sprite-only path.
