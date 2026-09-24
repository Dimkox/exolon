# Exolon — Step 9 Rebase (test archive)

This is the first runnable archive from the new level-rebase branch.

Key changes in this archive:
- keeps the existing 125-zone project and original-visual pipeline;
- Zone 009 object placement is rebuilt from the reference TMX coordinates rather than the old source-marker approximation;
- Zone 009 pistons now use x=64/192, y=320 (not y=384);
- changing room is a real 32x80 rectangle at x=368, y=176 in Tiled coordinates;
- rectangle-object coordinate conversion is explicit, so tile objects and rectangles are no longer conflated;
- pistons are lethal when exposed (unless test Invulnerability is ON);
- pressing UP inside the changing room toggles Exoskeleton mode;
- Exoskeleton fires a double blaster and protects against mines/pistons;
- Restart/new session resets Exoskeleton;
- every application launch still starts from Zone 000; High Score persists.

Important: this archive is a runnable checkpoint of the rebase work, not the claim that every late-zone action is already audited.

## Rebase cabin fix

- Changing-room artwork is now pass-through scenery: its action trigger no longer remains hidden behind compiled static collision.
- The collision exclusion is applied by object type, so it affects every changing-room screen, not only Zone 009.
- UP inside a changing room/teleport is consumed as a contextual action and cannot become an accidental jump on the following fixed step.

## Structured gameplay event log (wave A, 2026-09-24)

Every player action and game state change is now observable as one versioned JSON-lines record, and
the four wave-A state-machine findings are fixed with stream-only regression predicates
(`engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/`).

- Contract: `engineering/contracts/schemas/gameplay-event-v1.schema.json` (envelope
  `schema_version,seq,tick,frame,rot,ts_us,name` + per-event payload; `ts_us` is derived from the
  tick counter, never wall clock).
- Core: `Exolon/GameCore/Diagnostics/` - Foundation-only, no SpriteKit and no `CGVector`, so the
  fixed-step driver, the stage-boundary ledger, the launcher bonus state and `Player` compile and
  run on Linux (`evidence/harness/run.sh`, judged by `evidence/gameplay_log_check.py`).
- Where the file goes: `$TMPDIR/exolon/gameplay-<run_id>-<rot>.jsonl`, 8 MiB x 8 files, path echoed
  once to stderr. Never inside this repository - an untracked log here would stale every
  fingerprint-bound receipt.
- Switches: `EXOLON_EVENT_LOG=off|0|1|2|<directory>`; default is level 1 in Debug and off in
  Release. `off` creates no file at all. It is **file**-inert, not path-inert: level-0 records still
  append to the in-memory ring (nanoseconds each, and the ring laps quietly-counted when nothing
  drains it), and `GameplayEventLog` remains the injected sink. A build that must touch nothing is a
  build that does not construct the log; every non-injected object still uses `NullGameplayEventSink`.
- In-game: the F1 hitbox window also shows the last 8 log lines in one reused label.
- Fixed behavior: no catch-up step runs in a new zone inside the frame that transitioned (P1-9); a
  held UP cannot jump after a teleport/changing-room consume (P1-4); the stage bonus awards once per
  completed zone per playthrough with a visible suppression record (P1-8); the double-launcher bonus
  pays once and the launcher keeps firing (P1-6).
