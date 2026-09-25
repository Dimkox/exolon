# Rollback plan — wave C

## Trigger conditions
- `wave_c_check.py` red on a later tree without a recorded re-baseline protocol run;
- F1 overlay regression from `addDebugRect(...label:)` found on the macOS build (R2);
- a shipped-map visual regression attributable to newly-rendered safe models (32 maps).

## Application rollback
One step: `git revert <merge>` of wave C. Changes are self-contained:
- `TMXMapLoader.swift` additions delete cleanly (pure append);
- `TMXLevelRuntime.swift`: the exhaustive switch reverts to the silent-fallthrough chain
  (restoring the known defect — acceptable for rollback; issue #11 stays open as the tracker);
- `GameScene.swift` label param reverts to base signature use;
- contracts/manifest files are additive; deleting them reverts no runtime behavior.

## Data recovery / forward-fix
- `Exolon/Resources` is proven byte-identical to base at every recorded gate (282/282 blob
  recompute); no data state can exist that needs cleanup.
- The manifest is a committed artifact: forward-fix = regenerate with a new
  `canonicalization_version` tag; old digests remain auditable in history.

## Verification after rollback
- `wave_c_check.py` after revert: coverage probes must go RED (baseline 76/127 reproduced) —
  that red proves the rollback landed intact;
- harness `run.sh` REAL MAPS 125/125 still green (loader semantics unchanged);
- F1 overlay shows no safe-model outlines on the 32 maps.
