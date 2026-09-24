# Requirements — wave A (gameplay event log + state-machine fixes)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- [ ] AC-001 Given the Linux harness drives the real Foundation-only product types at emission
      level 2, when the run completes, then the JSONL has ≥ 1 `player.motion` per simulated tick,
      every line parses with `json.loads`, and `log.events_dropped` is absent or zero.
- [ ] AC-002 Given a scripted frame-gap crossing zone exit, when the fix is present, then
      predicate A holds (no `player.motion` with the transition's `frame` after
      `state.zone_transition`, a `tick.accumulator_reset{reason:"zone_transition"}` exists,
      `discarded_steps` consistent); when the fix is reverted, predicate A fails.
- [ ] AC-003 Given a playthrough parked at x>510 on stage-end zones, when fixed, then ≤ 1
      `bonus.stage_points` per `completed_zone` and every repeated trigger is witnessed by
      `bonus.stage_boundary_suppressed` (never silence); when reverted, predicate B fails
      (probe baseline: 750 awards in 600 s).
- [ ] AC-004 Given UP held across a teleport, when fixed, then no `player.jump` occurs until a
      release edge (`input.action_edge{action:"jump",pressed:false}`) precedes it; the predicates
      are decidable because `player.teleport.jump_latch_held` and `player.jump.after_teleport`
      exist.
- [ ] AC-005 Given a `bonus.double_launcher` collect, then `launcher_active_after` is reported and
      the launcher's subsequent firing (or absence) is observable via `entity.launcher_fire`;
      predicate D passes on the fixed build.
- [ ] AC-006 Level-2 emission costs ≤ 5 % of a 16.67 ms tick on this host (design target 0.025 %).
- [ ] AC-007 Every new Swift file is registered in `project.pbxproj` (all 4 marker kinds per file),
      verified by grep in the gate, and the shared Archive scheme still builds against the same
      single native target.

## Failure and edge cases

- Writer lags producer → ring laps: `log.events_dropped{count,first_seq,last_seq}` +
  `# dropped N` marker; a test with starved writer asserts counted drops, not silence.
- Truncated log → `seq` continuity check FAILS loudly (evidence loss is never a pass).
- Emission disabled (`EXOLON_EVENT_LOG=off`) → no file is created at all (not an empty one).
- Unknown enum raw value formats as `unknown<N>`, never aliases a real name.
- `beginTick` first tick is exactly 1 (off-by-one was a live prototype bug).
- Rotation boundary: a state-changing event never spans two files without `log.rotate` linking them.
- Death/respawn/pause/title do not reset `tick`/`frame` counters.

## Governance context

No `governance/` directory exists in this tree (`analysis-architect.md` §10.4); governance sections
are not applicable. Canonical normative sources for this change are `ORIGINAL_MECHANICS.md`,
`engineering/reports/exolon-full-audit-20260920-v3.md` and the GitHub issues #8/#10/#12/#13; spec
gaps are closed by explicit rulings recorded in `architecture.md` → Decisions.

- Applicable rule IDs: none available.
- Canonical-example deviations and evidence: n/a.
- Intentional debt created, repaid, or accepted: bullet/entity/pickup/hud event families reserved
  but unused in wave A (documented in schema, no payload definitions yet).

## Non-functional requirements

- Security: zero PII/secrets by construction (integer + enum-label payloads only; no free text;
  PID only in filename; no env dumps).
- Reliability: no crash path on logging failure (drop-count and continue); bounded disk
  (8 MiB × 8); kill switch one-step, no rebuild.
- Performance: hot-path append ≤ ~70 ns/event; level-2 full emission ≤ 5 % of a tick; producer
  never touches I/O, String, or collection allocation.
- Observability: the log itself is the observability deliverable; stderr echoes the active path;
  `tick.heartbeat` bounds any silence to 10 s.
