# Release plan — wave B

## Deployment
PR-only delivery (`codex/wave-b-mapdata-physics-20260924` → `main`); merge position SECOND in
series A → B → C — DONE: rebased clean onto post-A main `17a742a` (zero conflicts; artifacts
byte-identical), head `e520884`. External App-owned Trust CI on the exact head SHA plus both
review receipts remain the only merge gates.

## Feature flags / staged rollout
No flags: pure physics/data corrections. Player-visible deltas to disclose in the PR body:
- beam pair award 1000 (was 2000 per pair) — one destruction, one payout;
- spawn placement corrected within ±16 px on 119 maps; 6 enumerated unmoved;
- 48 spawns remain body-in-solid on thick-floor maps (≤ base 61, no-worse bound; true repair needs
  factory `vitorc` regeneration — recorded follow-up, not this wave);
- grenade cull moves 536 → derived 564-class bound.

## Metrics and alerts
- `python3 evidence/wave_b_check.py` 9/9 ≤3 s on head (live harness byte-equal to committed
  artifact; write_if_changed idempotence keeps source-stability green).
- 14-ablation mutation battery (A1–A8, B1–B4, M12, M13 in `evidence/wave_b_ablations.txt`):
  each named mutation reddens a named check (audit-grade controls).
- `git status Exolon/Resources` empty at every step (blob manifest 125/125).

## Go/no-go criteria
- macOS manual checks — STRUCTURALLY UNRUNNABLE; owner constraint 2026-09-25 (no macOS
  hardware/Developer ID exists; wave A's merged precedent shipped the same class of visual
  checks meter-proven with accepted residuals): piston retracted-sprite z-order eyeball
  (code review R1-2), one beam-map destruction visual, one stage-start spawn feel check.
  None gates the merge; wherever physics is involved the meter carries the proof
  (lethality 46/46, shared pool 25, spawn surface delta 0 on 119 + enumerated kept 6).
- AC-001..005/INV/FORBID green on final fingerprint (post-rebase onto 17a742a: 9/9, artifact
  byte-identical; controller re-records gate/receipts);
- code/test review receipts bound to the same fingerprint;
- Deviations incl. historical guards (`p1-1_piston_probe.py`, v3 expectations now red by design as
  defect-existence guards) acknowledged in PR body — their rewrite belongs to the reports' owner
  route, not to wave B.
