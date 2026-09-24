# Rollback plan — wave A

## Trigger conditions
- Field: drops > 0, heartbeat gaps > 10.5 s, or any crash attributed to Diagnostics (design goal:
  structurally impossible — treat as blocking).
- Build: macOS xcodebuild breakage from pbxproj registration or emit-arity drift.
- Gameplay: any behavior change beyond the four audited defects + rulings (compare stream
  predicates on a recorded session).

## Application rollback
One step, no rebuild: `EXOLON_EVENT_LOG=off` — sink short-circuits, no file created (proven by
SIG-002/kill_switch_no_file). For code-level revert: `git revert <merge>` is self-contained —
Diagnostics files + contract + harness are additive; call sites default to
`NullGameplayEventSink.shared`, so after revert the tree behaves as base by construction.

## Data recovery / forward-fix
- No game state touched: checkpoints/saves format unchanged; logs live in `$TMPDIR/exolon/` —
  deleting the directory is complete cleanup (never inside the clone; FORBID-003).
- Farm-inflated scores from pre-fix checkpoints are NOT retro-corrected (documented deviation;
  forward-fix only).
- Ledger/latch/launcher changes are pure-state; no persisted field added.

## Verification after rollback
- Reverted run produces NO log file and empty stderr echo line (assert kill_switch_no_file form);
- harness `run.sh` re-derives base behaviors: reverted driver → predicate A red (14 steps),
  reverted ledger → predicate B red (750 awards) — expected reds prove the control pair intact;
- `git diff 295690b` limited to reverted scope; grok_verify recorded on the reverted tree.
