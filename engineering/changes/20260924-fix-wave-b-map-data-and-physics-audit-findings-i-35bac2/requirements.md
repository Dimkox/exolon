# Requirements — wave B (map-data physics)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- [ ] AC-001 Given the shared surface query, when spawn feet are resolved, then for maps having a
      Collision top within ±16 px of the `vitorc` marker the feet equal that surface (body-clear
      PREFERRED, tie → lower Y), maps without one stay UNMOVED and enumerated; no spawn moves
      >16 px; the 37/59/29 marker-vs-surface control reproduces under the old rule.
- [ ] AC-002 Given the 46 pistons on 27 maps, when anchors resolve at-or-below the raised tread,
      then all 46 are lethal (6/46 under the old anchor — control).
- [ ] AC-003 Given beam_up/beam_down pairs, when fields are built, then one shared 25-HP pool per
      x-overlapping group, destruction removes both segments together, sum == 25×pairs per map.
- [ ] AC-004 Given derived projectile bounds, then blaster cull ≥ reachable clamp + bullet width,
      no shot is born dead at any reachable x, grenades share the named-bound policy, x>510
      transition unchanged.
- [ ] AC-005 Then the full meter is deterministic stdlib ≤60 s and EVERY named control flips.

## Failure and edge cases

- Column with no cell at/below tread → GLOBAL fallback plane (3 shaft maps; L01S15, L02S23,
  L05S23) — documented, meter-proven lethal.
- Equal-minX beam halves → index tie-break (grouping total order; precondition asserted in meter).
- No swiftc → `TOOL_ABSENT` rc=3, never silent green.
- merge-base attribution: added-lines scan widens, never narrows, when bases degenerate.

## Governance context

No `governance/` in tree — n/a. Normative sources: issues #5/#6/#7/#9, audit v3 rows, merged
P1-1/P1-2 probes; the ±16 window and preference-not-filter spawn rule are this change's rulings
after audits (amendments 1–2 recorded in `change-spec.yaml`).

## Non-functional requirements

- Security: n/a (no I/O surface added).
- Reliability: no new state; physics math only; rollback = git revert.
- Performance: one surface query built per level load (was 2–3 implicit scans); renderer merge
  now shared — equal rect-for-rect, proven 125/125.
- Observability: per-map delta tables (`wave_b_deltas.md`), green/ablation transcripts pinned in
  evidence; wave-A event log now covers transitions where these rules apply.
