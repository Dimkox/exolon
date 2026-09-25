# Rollback plan — wave B

## Trigger conditions
- playability regression attributable to the four corrected rules (piston now lethal where
  players memorized free lanes; beam now one-shot-pool; spawn shifted ≤16 px on stage starts);
- `wave_b_check.py` red on a later tree without a recorded re-baseline;
- macOS build breakage from the shared-constants refactor.

## Application rollback
One step: `git revert <merge>` of wave B. Self-contained: all changes are code-side physics;
`Exolon/Resources` untouched (blob-proven), no persistence changes, no flags to unwind. Revert
restores the audited defects exactly (37/59/29 spawn skew, 6/46 pistons lethal, 50-HP beam pairs,
528 cull corridor) — the meter then re-REDs its own baseline controls, which is the proof the
revert landed intact.

## Data recovery / forward-fix
- No saved state affected (checkpoints carry no spawn/anchor data).
- Accepted debt preserved from the fix side: 48 body-in-solid spawns (≤61 base) are forward-fixed
  only by regenerating `vitorc` markers in the level factory — tracked as follow-up, out of scope.
- Beam route-opening (destroyed field still solid in Collision layer) remains the pre-existing
  behavior either way.

## Verification after rollback
- `wave_b_check.py` after revert: `spawn_ground_all_maps`/`piston_anchor_all_pistons`/
  `beam_shared_hp_all_maps`/`bullet_cull_bounds` must FAIL with old-rule numbers
  ({0:37,+16:59,−16:29}, 6/46, 500 HP, 528) — expected reds;
- `pinned_geometry_unchanged` and `single_surface_query` are EXPECTED RED after revert too — they
  key off the post-change constants/query existence (corrected per code review; the earlier
  "stay green" claim was wrong by design);
- recorded gate re-run on the reverted tree binds a fresh receipt.
