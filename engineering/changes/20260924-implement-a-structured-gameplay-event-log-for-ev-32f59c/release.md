# Release plan — wave A

## Deployment
PR-only delivery (`codex/wave-a-gameplay-log-tick-fixes-20260924` → `main`); first in merge series
A → B → C (D-1 rebases onto this). Merge only after the external App-owned Trust CI check on the
exact head SHA plus code/test review receipts. No deployable artifact; waves B/C/D and the release
train consume main.

## Feature flags / staged rollout
- `EXOLON_EVENT_LOG`: unset → Debug level 1 / Release off; `<0|1|2>` level; `off`; `<path>` prefix.
  Default Release posture = zero user-visible change; developer builds get the log.
- Everything un-injected runs through `NullGameplayEventSink` — byte-identical legacy path.

## Metrics and alerts
- `python3 evidence/gameplay_log_check.py` 23/23 on the head (self-builds Linux harness; verification
  receipt already bound at tree bf509f48…).
- From the log in the field (Debug users): `log.events_dropped` absent; `tick.heartbeat` gap ≤10.5 s;
  ≤15 `player.motion`/frame; ≤1 `bonus.stage_points` per completed_zone.
- macOS `xcodebuild` of the shared scheme (the only true build gate for SpriteKit-bound files) —
  record output in PR before un-drafting review findings resolution.

## Go/no-go criteria
- AC-001..007 / INV / FORBID / SIG green with revert controls for AC-002/AC-003 observed flipping
  (evidence transcripts in package); both review receipts bound to final fingerprint; the 20
  recorded Deviations reviewed — the load-bearing ones for reviewers: UInt32 tick/frame lanes,
  drop-marker-as-event, discarded_us form per AC-002, playthrough boundary = state re-init,
  scene-side jump mask removed.
- Residual accepted: no Linux typecheck of SpriteKit files (parse + arity cross-check + macOS build).
